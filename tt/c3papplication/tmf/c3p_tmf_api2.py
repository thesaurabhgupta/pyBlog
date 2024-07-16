from requests.auth import HTTPBasicAuth
import requests
import random
import string
from flask import request, jsonify
from flask_httpauth import HTTPBasicAuth
import datetime
import time
import json
import logging
from flask_api import status
from c3papplication.common import Connections
from werkzeug.security import generate_password_hash, check_password_hash
from builtins import str
from c3papplication.discovery import c3p_snmp_disc_rec_new as CSDRN
from jproperties import Properties
from c3papplication.ipmanagement import c3p_ip_ping as CIP
from c3papplication.conf.springConfig import springConfig

auth = HTTPBasicAuth()
# app = Flask(__name__) #creating the Flask class object
users = {
    "root": generate_password_hash("hello"),
    "c3p": generate_password_hash("c3p")
}
# mydb = Connections.create_connection()
# mycursor = mydb.cursor(buffered=True)
filename = ""
configs = springConfig().fetch_config()
logger = logging.getLogger(__name__)
""" Authentification using Username and Password """


def create_backup_json(v_so_num, device_specs, row_id, param_feat, conn_flag, reso_id):
    data = {}
    result = []
    wflow = False
    mydb = Connections.create_connection()
    try:
        mycursor = mydb.cursor(buffered=True)
        for t in device_specs:
            for x in t:
                result.append(x)

        data["hostname"] = result[8]
        data["managementIp"] = result[6]
        data["userName"] = "admin"
        data["userRole"] = "admin"
        mycursor.execute(
            "SELECT rfo_apibody FROM c3p_rf_orders where rfo_id=%s", (v_so_num,))
        myresult = mycursor.fetchone()
        rfo_apibody = ''.join(myresult)
        body = json.loads(rfo_apibody)
        data["startup"] = body.get('startup')
        data['running'] = body.get('running')
        data['backupType'] = body.get('backupType')
        data['scheduleDate'] = body.get('scheduleDate')
        data['bkpBaselineFlag'] = ""
        data['hourlyDate'] = ""
        data['hourlyHrs'] = ""
        data["apiCallType"] = body.get('apiCallType')
        data["sourcesystemcode"] = body.get('sourcesystemcode')
        json_data = json.dumps(data)
        logger.debug('create_backup_json - json_data - %s', json_data)
        mycursor.execute("update c3p_rfo_decomposed set od_request_json = %s where od_rowid=%s", (json_data, row_id,))
        logger.debug("create_backup_json - record updated. %s", mycursor.rowcount)
        mydb.commit()
        logger.debug('create_backup_json - json_data :: %s', json_data)
        newHeaders = {"Content-type": "application/json",
                      "Accept": "application/json"}
        url = configs.get("C3P_Application") + \
              '/C3P/BackUpConfigurationAndTest/createConfigurationDcmBackUpAndRestore'

        req = requests.post(url, data=json_data, headers=newHeaders)
        # print ('req ::', req)
        resp = req.json()
        resp_json = resp
        if len(resp) == 0:
            wflow = True
        logger.debug('create_backup_json - req JSON :: %s', resp)
        mycursor.execute("update c3p_rfo_decomposed set od_requeststatus =%s,od_request_id=%s where od_rowid=%s", (resp_json['output'], resp_json['requestId'], row_id,))
        mydb.commit()
    except Exception as err:
        logger.error("Exception in create_backup_json: %s", err)
    finally:
        mydb.close
    return wflow

def create_delete_instance_json(v_so_num, device_specs, row_id, param_feat, conn_flag, reso_id):
    data = {}
    wflow = False
    mydb = Connections.create_connection()
    try:
        mycursor = mydb.cursor(buffered=True)
        result = []
        for t in device_specs:
            for x in t:
                result.append(x)
        data["apiCallType"] = "c3p-ui"
        data["customer"] = result[9]
        data["region"] = result[10]
        data["siteName"] = result[11]
        data["hostname"] = result[8]
        data["model"] = result[7]
        data["os"] = result[0]
        data["osVersion"] = result[1]
        data["deviceType"] = result[4]
        data["deviceFamily"] = result[2]
        data["vendor"] = result[3]
        data["networkType"] = "VNF"
        data["requestType"] = "SNAD"
        data["vnfConfig"] = ""
        data["managementIp"] = result[6]
        data["configGenerationMethod"] = ['DeleteInstance']
        data["templateId"] = ""
        data["selectedFeatures"] = []
        data["dynamicAttribs"] = []
        data["replication"] = []
        data["userName"] = "admin"
        data["userRole"] = "admin"
        json_data = json.dumps(data)
        mycursor.execute("update c3p_rfo_decomposed set od_request_json = %s where od_rowid=%s", (json_data, row_id,))
        logger.debug("create_delete_gcp - record updated. %s", mycursor.rowcount)
        mydb.commit()
        mycursor.execute(
            "SELECT d_id FROM c3p_deviceinfo WHERE d_decomm =0 AND d_hostname = %s AND d_mgmtip = %s", (result[8], result[6],))
        device_id = mycursor.fetchone()
        dummy_sr = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10)) + str(datetime.datetime.now())
        if (device_id[0] != None):
            mycursor.execute(
                "SELECT distinct rc_feature_id FROM c3p_resourcecharacteristicshistory WHERE device_id = %s AND rc_device_hostname = %s", (device_id[0], result[8],))
            myResult = mycursor.fetchall()
            for feature_id in myResult:
                mycursor.execute(
                    "SELECT c_id, c_name FROM c3p_m_characteristics WHERE c_f_id = %s", (feature_id[0],))
                myresult = mycursor.fetchall()
                for rc in myresult:
                    sql = "INSERT INTO c3p_resourcecharacteristicshistory(device_id,rc_device_hostname,so_request_id,rc_request_status,rfo_id,rc_action_performed,rc_feature_id,rc_characteristic_id,rc_name,rc_value,rc_valuetype) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
                    val = (
                    str(device_id[0]), result[8], dummy_sr, "", v_so_num, "DELETE", feature_id[0], rc[0], rc[1], "", "")
                    mycursor.execute(sql, val)
                    mydb.commit()

            newHeaders = {"Content-type": "application/json", "Accept": "application/json"}
            url = configs.get("C3P_Application") + \
                  configs.get("Config_Create")

            # Call to Camunda
            req = requests.post(url, data=json_data, headers=newHeaders)
            resp = req.json()
            resp_json = resp
            if len(resp) == 0:
                wflow = True
            # resp_json={"output": "Submitted","requestId": "SLGC-71D62FF","version": "1.0"}
            mycursor.execute(
                "update c3p_rfo_decomposed set od_requeststatus =%s,od_request_id=%s, od_updated_date = %s where od_rowid=%s", (resp_json['output'], resp_json['requestId'], datetime.datetime.now(), row_id,))
            mydb.commit()

            mycursor.execute("update c3p_resourcecharacteristicshistory set so_request_id=%s where rfo_id = %s", (resp_json[
                'requestId'], v_so_num,))
            mydb.commit()
            logger.debug('create_json_delete -json_data ::%s', json_data)
    except Exception as err:
        logger.error("Exception in create_delete_json: %s", err)
    finally:
        mydb.close
    return wflow

def create_json_gcp(v_so_num, rfo_apibody, res_chars, row_id):
    data = {}
    wflow = False
    mydb = Connections.create_connection()
    logger.debug("create_json_gcp - rfo_apibody:: %s", rfo_apibody)
    uId = datetime.datetime.now().strftime('%m%d%H%M%S')
    try:
        mycursor = mydb.cursor(buffered=True)
        data["apiCallType"] = "external"
        for rp in rfo_apibody['relatedParty']:
            if rp['role'] == 'customer':
                data["customer"] = rp['name']
            else:
                data["customer"] = ""
        if v_so_num[0:2] == "SR":
            res = rfo_apibody
        else:
            res = res_chars['resource']
        sql = "select c_site_region,c_site_name from c3p_cust_siteinfo where id = %s"
        logger.debug("create_json_gcp - DINFO:: %s", sql)

        mycursor.execute(sql, (res['place']['id'],))
        sites = []
        for x in mycursor.fetchone():
            sites.append(x)
        data["region"] = sites[0]
        data["siteName"] = sites[1]
        rand_str = ''.join(random.choices(string.ascii_lowercase +
                                          string.digits, k=5)) + str(int(round(time.time() * 1000)))
        data["hostname"] = res['name'] + ":::" + rand_str
        vnf_hostname = res['name']
        image = ""
        logger.debug("create_json_gcp - RES KEYS:: %s",
                     res.keys())
        for rc in res.keys():
            if rc == "resourceCharacteristic":
                for rc2 in res[rc]:
                    logger.debug("create_json_gcp - RC2::%s", rc2)
                    if rc2['name'] == "sourceImage":
                        image = rc2['value']
                        break
        sql = "SELECT v_model,v_os,v_osversion,v_devicetype,v_family,v_vendor FROM c3p_vnfimage_info where v_imagename=%s"
        logger.debug("create_json_gcp - SQL IS ::%s", sql)
        mycursor.execute(sql, (image,))
        myresult = mycursor.fetchall()
        result = []
        for x in myresult:
            for t in x:
                result.append(t)
        data["model"] = result[0]
        data["os"] = result[1]
        data["osVersion"] = result[2]
        data["deviceType"] = result[3]
        data["deviceFamily"] = result[4]
        data["vendor"] = result[5]
        data["networkType"] = "VNF"
        data["requestType"] = "SNAI"
        data["vnfConfig"] = ""
        data["managementIp"] = ""
        data["configGenerationMethod"] = ['Instantiation']
        data["templateId"] = ""
        data["selectedFeatures"] = []
        data["dynamicAttribs"] = []
        data["replication"] = []
        data["userName"] = "admin"
        data["userRole"] = "admin"
        json_data = json.dumps(data)
        mycursor.execute("update c3p_rfo_decomposed set od_request_json = %s where od_rowid=%s", (json_data, row_id,))
        logger.debug("create_json_gcp - record updated. %s", mycursor.rowcount)
        mydb.commit()
        if res['id'][0:10] == "INV-NETOPS":
            logger.debug("create_json_gcp - INV-NETOPS update.")
            for res_c in res['resourceCharacteristic']:
                sql = "INSERT INTO c3p_resourcecharacteristicshistory(device_id,rc_device_hostname,so_request_id,rc_request_status,rfo_id,rc_action_performed,rc_feature_id,rc_characteristic_id,rc_name,rc_value,rc_valuetype) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
                val = (
                uId, vnf_hostname, rand_str, "", v_so_num, "ADD", uId, res_c['id'], res_c['name'], res_c['value'], "")
                mycursor.execute(sql, val)
                mydb.commit()
        else:
            for res_c in res['resourceCharacteristic']:
                sql = "INSERT INTO c3p_resourcecharacteristicshistory(device_id,rc_device_hostname,so_request_id,rc_request_status,rfo_id,rc_action_performed,rc_feature_id,rc_characteristic_id,rc_name,rc_value,rc_valuetype) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
                val = (res['id'], vnf_hostname, rand_str, "", v_so_num, "ADD",
                       res['id'], res_c['id'], res_c['name'], res_c['value'], "")
                mycursor.execute(sql, val)
                mydb.commit()

        newHeaders = {"Content-type": "application/json",
                      "Accept": "application/json"}
        url = configs.get("C3P_Application") + \
              configs.get("Config_Create")

        # Call to Camunda
        req = requests.post(url, data=json_data, headers=newHeaders)
        resp = req.json()
        resp_json = resp
        logger.debug('create_json_gcp -resp_json ::%s', resp_json)
        if len(resp) == 0:
            wflow = True

        # resp_json={"output": "Submitted","requestId": "SLGC-71D62FF","version": "1.0"}
        mycursor.execute("update c3p_rfo_decomposed set od_requeststatus =%s,od_request_id=%s where od_rowid=%s", (resp_json['output'], resp_json['requestId'], row_id,))
        mydb.commit()
        logger.debug('create_json_gcp -json_data ::%s', json_data)
    except Exception as err:
        logger.error("Exception in create_json_gcp: %s", err)
    finally:
        mydb.close
    return wflow

def compute_id(id, method):
    if (id != None):
        sID = "SR"
    else:
        sID = "SO"
    rfo_id = sID + \
             str(method[0:2]) + \
             (datetime.datetime.today().strftime('%Y%m%d%H%M%S%f')[0:16])
    logger.debug("compute_id - rfo_id %s", rfo_id)
    return rfo_id

""" TMF Notification date : 19th Nov 2020 - By Sangita A """
def notify(so_num):
    json_data = {}
    mydb = Connections.create_connection()
    try:
        mycursor = mydb.cursor(buffered=True)
        v_so_num = so_num
        logger.debug("notify - v_so_num - %s", v_so_num)
        mycursor.execute(
            "SELECT rfo_url_param_id,rfo_apioperation FROM c3p_rf_orders where rfo_id=%s", (v_so_num,))
        rf_res = mycursor.fetchone()

        now = datetime.datetime.now()

        formatted_date = now.strftime('%Y-%m-%d %H:%M:%S')
        # Create the api body for API call for Notification (TMF)
        notify_apibody = {}

        if v_so_num[0:2] == 'SR':
            if rf_res[1] == 'PATCH':
                event_type = 'ResourceAttributeValueChangeEvent'
            elif rf_res[1] == 'POST':
                event_type = 'ResourceCreateEvent'
            elif rf_res[1] == 'DELETE':
                event_type = 'ResourceDeleteEvent'
        else:
            if rf_res[1] == 'PATCH':
                event_type = 'ResourceFunctionAttributeValueChangeEvent'
            elif rf_res[1] == 'POST':
                if v_so_num[0:2] == 'SD':
                    event_type = 'DiscoveryCreateEvent'
                else:
                    event_type = 'ResourceFunctionCreateEvent'
                    v_row = "SELECT od_req_resource_id FROM c3p_rfo_decomposed "\
                    "WHERE od_rfo_id = %s AND lower(od_rf_taskname) = 'instantiation'"  # this will select rowid and resourceid when min sequenceid exist
                    mycursor.execute(v_row, (v_so_num,))  # execute above mysql instruction
                    rowid = mycursor.fetchone()  # fetch the data
                    if rowid is not None:
                        logger.debug("finding resource id : %s", rowid[0])
                        mgmtipsql = "SELECT d_mgmtip FROM c3p_deviceinfo  WHERE d_id = %s"
                        mycursor.execute(mgmtipsql, (rowid[0],))  # execute above mysql instruction
                        deviceip = mycursor.fetchone()  # fetch the data
                        logger.debug("IP Address is %s", deviceip[0])
                        notify_apibody[configs.get("Notification_Ip_Address")] = deviceip[0]
                        notify_apibody[configs.get("Notification_Device_Id")] = rowid[0]
            elif rf_res[1] == 'DELETE':
                event_type = 'ResourceFunctionDeleteEvent'

        mycursor.execute('INSERT INTO c3p_event (eventTime, eventType) VALUES (%s, %s)',
                         (formatted_date, event_type,))  # Insert a row in event table
        mydb.commit()

        # Find the row_id of the record
        mycursor.execute(
            "SELECT e_rowid, eventTime, eventType FROM c3p_event WHERE e_rowid = (select last_insert_id())")
        v_event = mycursor.fetchone()
        logger.debug("notify - v_event - %s", v_event)
        x = datetime.datetime.now()
        rand_str = ''.join(random.choices(
            string.ascii_lowercase + string.digits, k=5))
        event_ID = str(v_event[0]) + x.strftime("%Y%m%d") + \
                   rand_str  # Generate an Event Id for this event
        logger.debug("notify - event_ID - %s", event_ID)
        mycursor.execute("UPDATE c3p_event SET eventID = %s WHERE e_rowid = %s", (event_ID, v_event[0],))
        mydb.commit()
        notify_apibody[configs.get("Notification_So_Id")] = v_so_num
        notify_apibody[configs.get("Notification_Event_Id")] = event_ID
        notify_apibody[configs.get("Notification_Event_Time")] = str(v_event[1])
        notify_apibody[configs.get("Notification_Event_Type")] = str(v_event[2])
        notify_apibody[configs.get("Notification_Event")] = {
            configs.get("Notification_Resource_Id"): rf_res[0],
            configs.get("Notification_Event_Status"): "successful"}

        logger.debug("notify -notify_apibody2 -%s ", notify_apibody)

        res_id = "SELECT od_req_resource_id FROM c3p_rfo_decomposed "\
                    "WHERE od_rfo_id = %s AND lower(od_rf_taskname) = 'inventory'"
        mycursor.execute(res_id, (v_so_num,))  # execute above mysql instruction
        res_id = mycursor.fetchone()  # fetch the data
        logger.debug("notify -res_id -%s ", res_id)

        if res_id is not None:
            mgmtipsql = "SELECT d_mgmtip FROM c3p_deviceinfo  WHERE d_id = %s"
            mycursor.execute(mgmtipsql, (res_id[0],))  # execute above mysql instruction
            deviceip = mycursor.fetchone()  # fetch the data
            logger.debug("IP Address is %s", deviceip[0])
            notify_apibody[configs.get("Notification_Device_Id")] = res_id[0]
            notify_apibody[configs.get("Notification_Ip_Address")] = deviceip[0]

        json_data = json.dumps(notify_apibody)
        logger.debug('notify - json_data ::%s', json_data)
    except Exception as err:
        logger.error("Exception in notify: %s", err)
    finally:
        mydb.close
    return json_data

# function to get the device info with two argument rowid and resourceid
def getDeviceSpecs(resourceid):
    deviceinfo = {}
    mydb = Connections.create_connection()
    try:
        mycursor = mydb.cursor(buffered=True)
        if resourceid is not None:  # checking rowid and resourceid exist or not
            # dev_info = []   # List variable to store information
            v_deviceinfo = "SELECT d_os, d_os_version, d_device_family, d_vendor, d_type, d_vnf_support, d_mgmtip, "\
                "d_model, d_hostname, c_cust_name, c_site_region, c_site_name "\
                "FROM c3p_deviceinfo "\
                "JOIN c3p_cust_siteinfo "\
                "ON c3p_deviceinfo.c_site_id = c3p_cust_siteinfo.id "\
                "WHERE d_id = %s"  # this will select device info when resourceid exist
            mycursor.execute(v_deviceinfo, (resourceid,))  # execute above mysql instruction
            deviceinfo = mycursor.fetchall()  # fetch the info data
            logger.debug("getDeviceSpecs - deviceinfo - %s", deviceinfo)
    except Exception as err:
        logger.error("Exception in getDeviceSpecs: %s", err)
    finally:
        mydb.close
    return deviceinfo
# findNextPriorityReq(reqid["req_id"])   # function call

def BuildResourceRelationship(so_num):
    result = ""
    mydb = Connections.create_connection()
    try:
        mycursor = mydb.cursor(buffered=True)
        if so_num is not None:
            logger.debug("BuildResourceRelationship - so_num - %s", so_num)
            mycursor.execute(
                "SELECT rfo_apibody FROM c3p_rf_orders where rfo_id=%s", (so_num,))
            myresult = mycursor.fetchone()
            # print(type(myresult))
            # if result return tuple (None,)
            if myresult[0] == None:
                result = "Data not found in db"
            else:
                rfo_apibody = ''.join(myresult)
                body = json.loads(rfo_apibody)
                sql = "INSERT INTO c3p_resource_relationships(rr_relationshiptype,resource_id,resource_href,resource_type,resource_referredtype,resource_name,rr_basetype,rr_schemalocation,rr_type) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)"
                for bod in body['resourceRelationship']:
                    for bres in bod.keys():
                        rr_type = ""
                        base_type = ""
                        relationship_type = ""
                        schema_location = ""
                        logger.debug(
                            "BuildResourceRelationship - RREL:: %s", bod[bres])
                        if bres == "resource":
                            # if key not present then get return None and we can set defalut value also
                            # if key not present then [] returns a key error
                            resource_data = bod['resource']
                            res_id = resource_data['id']
                            # res_href = resource_data['href']
                            res_href = (lambda: "", lambda: resource_data['href'])[
                                'href' in resource_data.keys()]()
                            # res_name = resource_data['name']
                            res_name = (lambda: "", lambda: resource_data['name'])[
                                'name' in resource_data.keys()]()
                            # res_type = resource_data['@type']
                            res_type = (
                                lambda: "", lambda: resource_data['@type'])['@type' in resource_data.keys()]()
                            res_ref_type = (lambda: "", lambda: resource_data['@referredType'])[
                                '@referredType' in resource_data.keys()]()

                        relationship_type = bod['relationshipType']
                        # base_type = bod['@baseType']
                        base_type = (
                            lambda: "", lambda: bod['@baseType'])['@baseType' in bod.keys()]()
                        # schema_location = bod['@schemaLocation']
                        schema_location = (
                            lambda: "", lambda: bod['@schema_location'])['@schema_location' in bod.keys()]()
                        # rr_type = bod['@type']
                        rr_type = (
                            lambda: "", lambda: bod['@type'])['@type' in bod.keys()]()

                    val = (relationship_type, res_id, res_href, res_type,
                           res_ref_type, res_name, base_type, schema_location, rr_type)
                    mycursor.execute(sql, val)
                    mydb.commit()
                    result = "Data saved Successfully"
        else:
            result = "Empty SO_Num"
    except Exception as err:
        logger.error("Exception in create_osUpgrade_json: %s", err)
    finally:
        mydb.close
    return result

def updateRequestIdResourceHistory(requestId, rand_str):
    mydb = Connections.create_connection()
    try:
        mycursor = mydb.cursor(buffered=True)
        updateSQL="update c3p_resourcecharacteristicshistory set so_request_id =%s where so_request_id=%s"
        mycursor.execute(updateSQL, (requestId, rand_str,));
        mydb.commit()
    except Exception as err:
        logger.error("Exception in updateRequestIdResourceHistory: %s", err)
    finally:
        mydb.close

def updateResourceCharacteristicData(apibody):
    rand_str = ''
    mydb = Connections.create_connection()
    logger.debug("updateResourceCharacteristicData - apibody: %s", apibody)
    try:
        mycursor = mydb.cursor(buffered=True)
        # Generate the dummy device id for external system
        device_id = int(str('8') + ''.join(random.choices(string.digits, k=2)
                                           ) + str(datetime.datetime.today().strftime('%H%M%S')))
        vnf_hostname = apibody["hostName"]
        rand_str = ''.join(random.choices(
            string.ascii_lowercase + string.digits, k=5)) + str(int(round(time.time() * 1000)))
        # featureId = fetchFeatureVNFInstantiation(apibody["targetVIM"])
        featureId = ''
        if apibody['networkFunction'] == 'instantiationMCC':
            logger.debug("updateResourceCharacteristicData - featureId: %s", featureId)
            for res_c in apibody['resourceCharacteristic']:
                sql = "INSERT INTO c3p_resourcecharacteristicshistory(device_id,rc_device_hostname,so_request_id,rc_request_status,rfo_id,rc_action_performed,rc_feature_id,rc_characteristic_id,rc_name,rc_value,rc_valuetype) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
                val = (device_id, vnf_hostname, rand_str, "", "", "ADD",
                       res_c['featureId'], res_c['id'], res_c['name'], res_c['value'], "string")
                mycursor.execute(sql, val)
                mydb.commit()
        else:
            logger.debug("updateResourceCharacteristicData - featureId: %s", featureId)
            for res_c in apibody['resourceCharacteristic']:
                sql = "INSERT INTO c3p_resourcecharacteristicshistory(device_id,rc_device_hostname,so_request_id,rc_request_status,rfo_id,rc_action_performed,rc_feature_id,rc_characteristic_id,rc_name,rc_value,rc_valuetype) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
                val = (device_id, vnf_hostname, rand_str, "", "", "ADD",
                       featureId, res_c['id'], res_c['name'], res_c['value'], "string")
                mycursor.execute(sql, val)
                mydb.commit()
    except Exception as err:
        logger.error("Exception in updateResourceCharacteristicData: %s", err)
    finally:
        mydb.close
    return rand_str

def buildCreateVNFRequest(apibody):
    data = {}
    mydb = Connections.create_connection()
    try:
        mycursor = mydb.cursor(buffered=True)
        data["customer"] = apibody['customer']
        data["apiCallType"] = "c3p-ui"
        data["region"] = apibody["region"]
        data["siteName"] = apibody["siteName"]
        rand_str = ''.join(random.choices(
            string.ascii_lowercase + string.digits, k=5)) + str(int(round(time.time() * 1000)))
        data["hostname"] = apibody["hostName"] + ":::" + rand_str

        image = ""
        for rc in apibody['resourceCharacteristic']:
            if rc['name'] == "sourceImage":
                image = rc['value']
                break

        if apibody["targetVIM"] == "OpenStack":
            sql = "SELECT v_model,v_os,v_osversion,v_devicetype,v_family,v_vendor FROM c3p_vnfimage_info where v_image_ref = %s"
        else:
            sql = "SELECT v_model,v_os,v_osversion,v_devicetype,v_family,v_vendor FROM c3p_vnfimage_info where v_imagename = %s"

        logger.debug("buildCreateVNFRequest - ICVR SQL IS ::%s", sql)
        mycursor.execute(sql, (image,))
        myresult = mycursor.fetchall()
        result = []
        for x in myresult:
            for t in x:
                result.append(t)
        if len(result) > 5:
            data["model"] = result[0]
            data["os"] = result[1]
            data["osVersion"] = result[2]
            data["deviceType"] = result[3]
            data["deviceFamily"] = result[4]
            data["vendor"] = result[5]
        else:
            data["model"] = ""
            data["os"] = ""
            data["osVersion"] = ""
            data["deviceType"] = ""
            data["deviceFamily"] = ""
            data["vendor"] = "Affirmed"
        data["networkType"] = "VNF"
        data["requestType"] = "SNAI"
        data["vnfConfig"] = ""
        data["managementIp"] = ""
        if apibody["networkFunction"] != None:
            data["configGenerationMethod"] = apibody["networkFunction"]
        else:
            data["configGenerationMethod"] = ['Instantiation']
        if "templateId" in apibody:
            data["templateId"] = apibody["templateId"]
        else:
            data["templateId"] = ""
        data["selectedFeatures"] = []
        data["dynamicAttribs"] = []
        data["replication"] = []

        if (apibody['userName'] != None):
            data["userName"] = apibody['userName']
        else:
            data["userName"] = "admin"

        if (apibody['userRole'] != None):
            data["userRole"] = apibody['userRole']
        else:
            data["userRole"] = "admin"
    except Exception as err:
        logger.error("Exception in buildCreateVNFRequest:%s", err)
    finally:
        mydb.close
    return data

def fetchFeatureVNFInstantiation(targetVIM):
    mydb = Connections.create_connection()
    try:
        mycursor = mydb.cursor(buffered=True)
        if targetVIM == 'GCP':
            featureName = 'VNF Instantiation GCP'
        elif targetVIM == 'OpenStack':
            featureName = 'VNF Instantiation OS'
        else:
            featureName = 'VNF Instantiation'
        # sql = f"SELECT f_id FROM c3p_m_features where f_category='Instantiation' and f_name='{featureName}'"
        mycursor.execute("SELECT f_id FROM c3p_m_features where f_category='Instantiation' and f_name=%s'",
                         (featureName,));
        myresult = mycursor.fetchone()
        return myresult[0]
    except Exception as err:
        logger.error("Exception in fetchFeatureVNFInstantiation:%s", err)
    finally:
        mydb.close

'''Added Dhanshri Mane :23/02/2021.
create osUpgrade json as per c3p and call c3p osUpgrade request'''
def create_osUpgrade_json(v_so_num, device_specs, row_id, param_feat, conn_flag, reso_id):
    wflow = False
    mydb = Connections.create_connection()
    try:
        mycursor = mydb.cursor(buffered=True)
        data = {}
        result = []
        for t in device_specs:
            for x in t:
                result.append(x)
        listData = []
        valueData = {}
        valueData["hostname"] = result[8]
        valueData["managementIp"] = result[6]
        valueData["requestType"] = "IOSUPGRADE"
        valueData["templateId"] = ""
        listData.append(valueData)

        data["requests"] = listData
        data["userName"] = "admin"
        data["userRole"] = "admin"
        data["apiCallType"] = "external"
        data["sourcesystemcode"] = ""
        json_data = json.dumps(data)
        logger.debug("create_osUpgrade_json - json_data - %s", json_data)
        mycursor.execute("update c3p_rfo_decomposed set od_request_json = %s where od_req_resource_id=%s", (json_data, row_id,))
        logger.debug("create_osUpgrade_json - record updated. %s",
                     mycursor.rowcount)
        mydb.commit()
        logger.debug('create_osUpgrade_json -json_data :: %s', json_data)
        newHeaders = {"Content-type": "application/json",
                      "Accept": "application/json"}
        url = configs.get("C3P_Application") + \
              '/C3P/BackUpConfigurationAndTest/batchOsUpgrade'
        # wflow = False

        req = requests.post(url, data=json_data, headers=newHeaders)
        # print ('req ::', req)
        resp = req.json()
        resp_json = resp
        if len(resp) == 0:
            wflow = True
        logger.debug('create_osUpgrade_json -req JSON :: %s', resp)
        mycursor.execute("update c3p_rfo_decomposed set od_requeststatus =%s,od_request_id=%s where od_req_resource_id=%s", (resp_json['output'], resp_json['requestId'], row_id,))
        mydb.commit()
    except Exception as err:
        logger.error("Exception in create_osUpgrade_json:%s", err)
    finally:
        mydb.close
    return wflow

def bMC_Authentication(srcsystem, jsondt):
    mydb = Connections.create_connection()
    try:
        rf_srcsystm = srcsystem
        jsondata = json.dumps(jsondt)
        print(jsondata)
        mycursor = mydb.cursor(buffered=True)
        if rf_srcsystm == "CEBMCIN1":
            mycursor.execute("SELECT srm_response_url,srm_auth_u_param,srm_auth_p_param "
                             "FROM c3p_m_ss_response_mapping "
                             "where srm_ss_code=%s and srm_module_code='CMNOTITK'", (rf_srcsystm,))
            url_tokn = mycursor.fetchone()
            logger.debug("tmf:c3p_tmf_get_api::bMC_Authentication:BMC - URL_tokn - %s", url_tokn)
            #           url = "https://techmgosi-restapi.onbmc.com/api/jwt/login"
            headers = {"Authorization": "AR-JWT{{jwt}}", "Content-Type": "application/x-www-form-urlencoded",
                       "Connection": "keep-alive"}

            login_data = {}
            login_data["username"] = url_tokn[1]
            login_data["password"] = url_tokn[2]
            logger.debug("tmf:c3p_tmf_get_api::bMC_Authentication:BMC - login_data - %s", login_data)

            token = requests.request("POST", url_tokn[0], headers=headers, data=login_data)

            #            url2 = "https://techmgosi-restapi.onbmc.com/api/arsys/v1/entry/C3P Interface update"
            mycursor.execute("SELECT srm_response_url "
                             "FROM c3p_m_ss_response_mapping "
                             "where srm_ss_code=%s and srm_module_code='CMNOTIAC'", (rf_srcsystm,))
            url_actual = mycursor.fetchone()
            logger.debug("tmf:c3p_tmf_get_api::bMC_Authentication:BMC - URL_Actual - %s", url_actual)

            headers2 = {"Content-Type": "application/json", "Authorization": "AR-JWT{{jwt}}",
                        "Cookie": "AR-JWT=" + token.text}
            respnse = requests.post(url_actual[0], headers=headers2, data=jsondata)
            print(respnse)
            logger.debug("tmf:c3p_tmf_get_api::bMC_Authentication:BMC - json_resp - %s", respnse)
            logger.debug('bMC_Authentication - Response JSON :: %s', respnse)
            logger.debug('bMC_Authentication - Status Code :: %s', respnse.content)

    except Exception as err:

        logger.error("Exception in bMC_Authentication: %s", err)

    finally:
        return respnse
        mydb.close
