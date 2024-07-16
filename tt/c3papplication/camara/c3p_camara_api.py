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
from c3papplication.conf.springConfig import springConfig
from builtins import str
from jproperties import Properties
import ipaddress
import uuid
import re

filename = ""

configs = springConfig().fetch_config()

logger = logging.getLogger(__name__)


def compute_id(id, method):
    if (id != None):
        sID = "SR"
    else:
        sID = "SO"
    rfo_id = sID + \
             str(method[0:2]) + \
             (datetime.datetime.today().strftime('%Y%m%d%H%M%S%f')[0:16])
    logger.debug("c3p_camara_api:compute_id :: rfo_id: %s", rfo_id)
    return rfo_id


def camaradatatodb(id):
    rhref = ''
    try:

        mydb = Connections.create_connection()
        mycursor = mydb.cursor(buffered=True)

        cao_id = compute_id(id, request.environ['REQUEST_METHOD'])
        cao_nel_id = compute_nel_id(cao_id)
        logger.info('c3p_camara_api:camaradatatodb :: cao_id: %s', cao_id)
        logger.debug('c3p_camara_api:camaradatatodb :: cao_nel_id: %s', cao_nel_id)
        logger.debug('c3p_camara_api:camaradatatodb :: headers: %s', request.headers)

        cao_apioperation = request.environ['REQUEST_METHOD']
        logger.debug('c3p_camara_api:camaradatatodb :: cao_apioperation: %s', request.environ['REQUEST_METHOD'])

        cao_apiurl = request.environ['PATH_INFO']
        logger.debug('c3p_camara_api:camaradatatodb :: cao_apiurl: %s', request.environ['PATH_INFO'])

        global cao_url_param_id
        if (id != None):
            cao_url_param_id = id
        else:
            cao_url_param_id = request.args.get('id')
        logger.debug('c3p_camara_api:camaradatatodb :: cao_url_param_id: %s', cao_url_param_id)

        if 'username' in request.headers:
            cao_sourcesystem = str(request.headers['username'])
        else:
            cao_sourcesystem = str(request.environ['SERVER_NAME'])
        logger.debug('c3p_camara_api:camaradatatodb :: cao_sourcesystem: %s', cao_sourcesystem)

        cao_apiauth_status = status.HTTP_201_CREATED
        cao_apibody = {
            'cao_apioperation': cao_apioperation
        }

        cao_url_param_filters = ''
        if (cao_apioperation == 'DELETE'):
            cao_status = 'Accepted'
            try:
                mycursor = mydb.cursor(buffered=True)
                apibody_sql = "SELECT rfo_apibody FROM c3p_rf_orders where rfo_nel_id= %s"
                mycursor.execute(apibody_sql, (id,))
                apibody_result = mycursor.fetchone()
                cao_apibody = json.loads(apibody_result[0])
                logger.info("c3p_camara_api:camaradatatodb :: delete_apibody: %s", cao_apibody)
                # cao_apibody.update({'qos': "QoS_S"})
                # logger.info("datatodb:delete::apibody: %s", cao_apibody)

            except Exception as err:
                logger.error("c3p_camara_api:camaradatatodb :: Exception: %s", err)
        else:
            cao_url_param_filters = request.args.get('filter')
            cao_apibody = request.json
            # cao_apibody = json.dumps(request.json)

            if (len(cao_apibody) != 0):
                cao_status = 'Accepted'
            else:
                cao_status = 'Bad Request'

        # cao_url_param_filters = prfl_par_flag
        cao_created_date = datetime.datetime.now()
        cao_updated_by = 'system'
        cao_updated_date = datetime.datetime.now()

        cao_apibody["id"] = cao_nel_id
        if (cao_apioperation == 'DELETE'):
            cao_apibody["id"] = id

        try:

            # sql = "INSERT INTO c3p_t_camara_orders(cao_id,cao_apibody,cao_apioperation,cao_apiurl,cao_url_param_id,cao_url_param_filters,cao_sourcesystem,cao_apiauth_status,cao_status,cao_created_date,cao_updated_by,cao_updated_date) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
            sql = "INSERT INTO c3p_rf_orders(rfo_nel_id,rfo_id,rfo_apibody,rfo_apioperation,rfo_apiurl,rfo_url_param_id,rfo_url_param_filters,rfo_sourcesystem,rfo_apiauth_status,rfo_status,rfo_created_date,rfo_updated_by,rfo_updated_date) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
            val = (
                cao_nel_id, cao_id, json.dumps(cao_apibody), cao_apioperation, cao_apiurl, cao_url_param_id,
                cao_url_param_filters,
                cao_sourcesystem, cao_apiauth_status, cao_status, cao_created_date, cao_updated_by, cao_updated_date)
            logger.debug("c3p_camara_api:camaradatatodb :: apibody: %s", cao_apibody)
            mycursor.execute(sql, val)
            mydb.commit()

            #cao_apibody["id"] = cao_nel_id
            logger.info(" c3p_camara_api:camaradatatodb :: Execution Done")
        except Exception as err:
            logger.error("c3p_camara_api:camaradatatodb :: Exception: %s", err)

        url = configs.get("Camunda_Engine") + configs.get("Camara_Decompose_Workflow")
        logger.debug("c3p_camara_api:camaradatatodb :: url: %s", url)

        inp = {}
        inp['businessKey'] = cao_id
        inp['variables'] = {"version": {"value": "1.0"}}
        data_json = json.dumps(inp)

        newHeaders = {"Content-type": "application/json", "Accept": "application/json"}

        f = requests.post(url, data=data_json, headers=newHeaders)
        logger.debug('c3p_camara_api:camaradatatodb :: Response: %s', f.json())

        rhref = configs.get("C3P_Environment") + '/c3p-p-core/naas/api/camara/monitor/?id=' + cao_id

        if (cao_apioperation == 'DELETE' or "latitude" in cao_apibody):
            status_query = "SELECT od_requeststatus FROM c3p_rfo_decomposed where od_rfo_id =%s"
            logger.debug("c3p_camara_api:camaradatatodb :: status_sql: %s", status_query)
            mycursor.execute(status_query, (cao_id,))
            test_status = mycursor.fetchone()
            count = 0

            while count <= 36:
                mydb = Connections.create_connection()
                mycursor = mydb.cursor(buffered=True)

                if test_status[0] == "Success" or test_status[0] == "Failure":
                    if "latitude" in cao_apibody:
                        req_id_sql = "SELECT od_request_id FROM c3p_rfo_decomposed where od_rfo_id = %s"
                        mycursor.execute(req_id_sql, (cao_id,))
                        req_id = (mycursor.fetchone())[0]
                        logger.debug("req_id: %s", req_id)

                        col_val_sql = "Select test_collected_values from c3p_t_tststrategy_m_config_results where request_id = %s"
                        mycursor.execute(col_val_sql, (req_id,))
                        col_val1 = mycursor.fetchone()
                        logger.debug("After fetching %s", col_val1)
                        if col_val1:
                            col_val = json.loads(col_val1[0])
                            content = []
                            del col_val["Collected_values"]
                            logger.debug("Col_val: %s",col_val)
                            content.append(col_val)
                            logger.debug("After format %s", content)
                            response = {"content": content, "code": "Response", "status": 201, "message": "Success"}
                            # response = jsonify({"content": col_val},{"code": "Response", "status": 201,"message": "Success"})
                            logger.debug('c3p_camara_api:camaradatatodb :: Response: %s', response)
                            break
                        else:
                            logger.debug('c3p_camara_api:camaradatatodb :: Response:No collected values')
                            response = {"code": "Response", "status": 201, "message": "Failure"}

                    elif cao_apioperation == 'DELETE':
                        if test_status[0] == "Success":
                            response = {"Code": "Session Deleted", "Status": test_status[0]}
                            logger.debug('c3p_camara_api:camaradatatodb inside while success :: Response: %s', response)
                            break
                        else:
                            response = {"Code": "Session Failed", "Status": test_status[0]}
                            logger.debug('c3p_camara_api:camaradatatodb :: Response: %s', response)
                            break

                status_query = "SELECT od_requeststatus FROM c3p_rfo_decomposed where od_rfo_id =%s"
                logger.debug("c3p_camara_api:camaradatatodb :: status_sql_while: %s", status_query)
                mycursor.execute(status_query, (cao_id,))
                test_status = mycursor.fetchone()
                logger.debug("c3p_camara_api:camaradatatodb :: test_status_while: %s", test_status[0])
                time.sleep(5)
                mydb.close()
                count += 1

                # response = {"Code": "Session Failed"}
                # logger.debug('c3p_camara_api:camaradatatodb :: Response: %s', response)

        elif (cao_apioperation != 'DELETE'):
            response = jsonify({"content": cao_apibody, "href": rhref},
                               {"code": "Response", "status": 201, "message": "Success"}), status.HTTP_201_CREATED
            logger.debug('c3p_camara_api:camaradatatodb :: Response: %s', response)

    # cao_apibody["id"] = cao_nel_id
    except Exception as err:
        logger.error("c3p_camara_api:camaradatatodb :: Exception in main block of datatodb: %s", err)

    finally:
        if not response:
            response = {"Code": "Session Failed"}
            logger.error('c3p_camara_api:camaradatatodb :: Response: %s', response)
        mydb.close

    logger.info("Response at end %s", response)
    return response


def camaradecompose():
    global rfo_url_param_id, rfo_id, resource_key
    depth = 0
    badflow = 0
    so_num = request.json['SO_number']
    mydb = Connections.create_connection()
    try:
        mycursor = mydb.cursor(buffered=True)
        rfo_id = so_num

        mycursor.execute(
            "SELECT rfo_apioperation,rfo_apibody,rfo_apiurl FROM c3p_rf_orders where rfo_id=%s", (so_num,))
        logger.debug("c3p_camara_api:camaradecompose :: SQL: %s",
                     "SELECT rfo_apioperation,rfo_apibody,rfo_apiurl FROM c3p_rf_orders where rfo_id='" + so_num + "'")
        myresult = mycursor.fetchall()

        result = []
        for x in myresult:
            for t in x:
                result.append(t)
        logger.debug("c3p_camara_api:camaradecompose :: Result is: %s", result)

        rfo_apimethod = result[0]
        logger.debug("c3p_camara_api:camaradecompose :: API-METHOD here is: %s", rfo_apimethod)
        rfo_apibody = result[1]
        rfo_apiurl = result[2]
        if rfo_apimethod == "DELETE":
            rfo_apiurl = rfo_apiurl.split("/")[-2]
            logger.debug("c3p_camara_api:camaradecompose :: rfo_apiurl here is: %s", rfo_apimethod)
        else:
            rfo_apiurl = rfo_apiurl.split("/")[-1]

        # logic for GCP compute begins
        if rfo_apimethod == 'POST' or rfo_apimethod == 'DELETE' or rfo_apimethod == 'PUT':
            # camara_requestType= fetch apiurl operation from url---(e.g.: qod)
            camara_requestType = rfo_apiurl
            logger.debug("c3p_camara_api:camaradecompose :: camara_requestType: %s", camara_requestType)

            rfo_apibody2 = json.loads(rfo_apibody)
            logger.debug("c3p_camara_api:camaradecompose :: rfo_apibody2: %s", rfo_apibody2)

            if camara_requestType != None:
                dummy_sr = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10)) + str(
                    datetime.datetime.now())

                if (camara_requestType == 'qod'):

                    sql = "INSERT INTO c3p_rfo_decomposed(od_rfo_id,od_param_id,od_seq,od_rf_taskname,od_req_resource_id,od_request_id,od_requeststatus,od_created_by,od_created_date,od_updated_by,od_updated_date) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
                    val = (
                        so_num, "NULL", '1', 'activationFeature', dummy_sr, "", 'queued', 'system',
                        datetime.datetime.now(), 'system', datetime.datetime.now())

                    mycursor.execute(sql, val)
                    mydb.commit()
                    badflow = 2
                    logger.debug("cc3p_camara_api:camaradecompose :: od_request_id: %s", dummy_sr)

                elif (camara_requestType == "devicelocation"):
                    sql = "INSERT INTO c3p_rfo_decomposed(od_rfo_id,od_param_id,od_seq,od_rf_taskname,od_req_resource_id,od_request_id,od_requeststatus,od_created_by,od_created_date,od_updated_by,od_updated_date) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
                    val = (
                        so_num, "NULL", '1', 'LocationTest', dummy_sr, "", 'queued', 'system',
                        datetime.datetime.now(), 'system', datetime.datetime.now())

                    mycursor.execute(sql, val)
                    mydb.commit()
                    badflow = 2
                    logger.debug("cc3p_camara_api:camaradecompose :: od_request_id: %s", dummy_sr)

                else:
                    pass

    except Exception as err:
        logger.error("c3p_camara_api:camaradecompose :: Exception in decompose: %s", err)
    finally:
        mydb.close

    if badflow == 1:
        return jsonify({"message": "Resource Characteristics is missing some value(s)"}), status.HTTP_400_BAD_REQUEST
    elif (badflow == 2 or badflow == 3 or badflow == 4 or badflow == 5 or badflow == 6 or badflow == 7):
        return jsonify({"SO_number": so_num, "workflow_status": True}), status.HTTP_200_OK
    else:
        return jsonify({"SO_number": so_num, "workflow_status": True}), status.HTTP_200_OK


def camarafindNextPriorityReq():
    wflow_status = True
    rfo_apibody = json.dumps(request.json)
    logger.debug("c3p_camara_api:camarafindNextPriorityReq :: rfo_apibody: %s", rfo_apibody)
    conn_flag = 0
    seq_res = 0

    v_so_num = request.json['SO_number']
    mydb = Connections.create_connection()
    try:

        mycursor = mydb.cursor(buffered=True)
        logger.debug("c3p_camara_api:camarafindNextPriorityReq :: v_so_num: %s", v_so_num)

        mycursor.execute("SELECT rfo_apioperation FROM c3p_rf_orders where rfo_id=%s", (v_so_num,))
        req_method = mycursor.fetchone()

        v_minseq = "SELECT min(od_seq) FROM c3p_rfo_decomposed WHERE od_rfo_id = %s AND lower(od_requeststatus) = 'queued'"
        logger.debug("c3p_camara_api:camarafindNextPriorityReq :: v_minseq: %s", v_minseq)

        mycursor.execute(v_minseq, (v_so_num,))
        min_seq = mycursor.fetchone()

        mycursor.execute("SELECT rfo_apibody FROM c3p_rf_orders where rfo_id=%s", (v_so_num,))
        myresult = mycursor.fetchone()
        rfo_apibody = json.loads(''.join(myresult))

        prfl_name = ""

        if 'qos' in rfo_apibody:
            prfl_name = rfo_apibody["qos"]
        elif 'dscp' in rfo_apibody:
            prfl_name = rfo_apibody["dscp"]
        logger.info("c3p_camara_api:camarafindNextPriorityReq :: Prfl_name: %s ", prfl_name)

        if prfl_name:
            mycursor.execute("Select pr_function from c3p_naas_m_profile where pr_name =%s", (prfl_name,))
            funcs = mycursor.fetchall()
            nel_id = rfo_apibody["id"]
            if min_seq[0] is not None:

                v_row = \
                    "SELECT od_rowid, od_req_resource_id,od_rf_taskname FROM c3p_rfo_decomposed WHERE od_rfo_id = %s AND lower(od_requeststatus) = 'queued' AND od_seq = %s"
                logger.debug("c3p_camara_api:camarafindNextPriorityReq :: v_row: %s", v_row)

                mycursor.execute(v_row, (v_so_num, min_seq[0],))
                rowid = mycursor.fetchall()  # fetch the data

                for row in rowid:
                    # un-tuple the data to list
                    logger.debug("c3p_camara_api:camarafindNextPriorityReq :: ROW FOR JSON PREPRARER: %s", row)

                    for func in funcs:
                        # device_specs = getDeviceSpecs(row[1])
                        logger.info("c3p_camara_api:camarafindNextPriorityReq :: func: %s", func)
                        device_specs = getProfileSpecs(v_so_num, func)
                        logger.debug("c3p_camara_api:camarafindNextPriorityReq :: device_specs: %s", device_specs)
                        wflow_status = create_json(v_so_num, device_specs, row[0], row[2], conn_flag, row[1])

                    v_rowstatus = "UPDATE c3p_rf_orders SET rfo_status = 'In Progress',rfo_updated_date = %s,rfo_updated_by='System'  WHERE rfo_id = %s"  # update the rfo status
                    logger.debug("c3p_camara_api:camarafindNextPriorityReq :: v_rowstatus: %s", v_rowstatus)

                    mycursor.execute(v_rowstatus, (datetime.datetime.now(), v_so_num,))
                    mydb.commit()
                    conn_flag = conn_flag + 1

        elif "latitude" in rfo_apibody:
            if min_seq[0] is not None:

                v_row = \
                    "SELECT od_rowid, od_req_resource_id,od_rf_taskname FROM c3p_rfo_decomposed WHERE od_rfo_id = %s AND lower(od_requeststatus) = 'queued' AND od_seq = %s"
                logger.debug("c3p_camara_api:camarafindNextPriorityReq :: v_row: %s", v_row)

                mycursor.execute(v_row, (v_so_num, min_seq[0],))
                rowid = mycursor.fetchall()  # fetch the data

                for row in rowid:
                    # un-tuple the data to list
                    msisdn = rfo_apibody['ueId']['msisdn']
                    lat = str(rfo_apibody['latitude'])
                    long = str(rfo_apibody['longitude'])
                    logger.debug("c3p_camara_api:camarafindNextPriorityReq :: ROW FOR JSON PREPRARER: %s", row)
                    wflow_status = create_device_json(lat, long, msisdn, row[0])

                    v_rowstatus = "UPDATE c3p_rf_orders SET rfo_status = 'In Progress',rfo_updated_date = %s,rfo_updated_by='System'  WHERE rfo_id = %s"  # update the rfo status
                    logger.debug("c3p_camara_api:camarafindNextPriorityReq :: v_rowstatus: %s", v_rowstatus)

                    mycursor.execute(v_rowstatus, (datetime.datetime.now(), v_so_num,))
                    mydb.commit()
                    conn_flag = conn_flag + 1

        else:
            logger.debug("c3p_camara_api:camarafindNextPriorityReq :: I am in else")
            wflow_status = True
            v_rowstatus = "UPDATE c3p_rf_orders SET rfo_status = 'Completed',rfo_updated_date = %s,rfo_updated_by='System'  WHERE rfo_id = %s"  # update the rfo status
            mycursor.execute(v_rowstatus, (datetime.datetime.now(), v_so_num,))
            mydb.commit()

        if (req_method[0] == 'DELETE'):
            del_status = "UPDATE c3p_rf_orders SET rfo_status = 'Deleted',rfo_updated_date = %s,rfo_updated_by='System'  WHERE rfo_nel_id = %s"  # update the rfo status
            mycursor.execute(del_status, (datetime.datetime.now(), nel_id,))
            mydb.commit()

    except Exception as err:
        logger.error("c3p_camara_api:camarafindNextPriorityReq :: Exception in findNextPriorityReq: %s", err)
    finally:
        mydb.close
    return jsonify(SO_number=v_so_num, workflow_status=wflow_status), status.HTTP_200_OK


# function to get the device info with two argument rowid and resourceid
def getProfileSpecs(soid, func):
    mydb = Connections.create_connection()
    try:
        mycursor = mydb.cursor(buffered=True)

        # checking rowid and resourceid exist or not
        if soid is not None:
            sql_apibody = "SELECT rfo_apibody,rfo_apioperation FROM c3p_rf_orders where rfo_id=%s"
            mycursor.execute(sql_apibody, (soid,))
            rfo_apibody = mycursor.fetchone()
            apibody = json.loads(rfo_apibody[0])
            operation = rfo_apibody[1]
            logger.info("c3p_camara_api:getProfileSpecs :: Apibody: %s ", apibody)

            if 'qos' in apibody:
                if operation == 'DELETE':
                    apibody.update({'qos': "QoS_S"})
                    logger.info("c3p_camara_api:getProfileSpecs :: apibody: %s", apibody)

                    sql = "UPDATE c3p_rf_orders SET rfo_apibody = '{}' where rfo_id =%s".format(json.dumps(apibody))
                    logger.info("c3p_camara_api:getProfileSpecs :: sql: %s", sql)
                    mycursor.execute(sql,(soid,))
                    mydb.commit()

                profile_name = apibody.get("qos")
                msisdn = apibody["ueId"]["msisdn"]

            if 'dscp' in apibody:

                if operation == 'DELETE':
                    pf_name = apibody['dscp']

                    # only radio and class value is required can change the values later or remove the last condition
                    sql = "Select pp_paramter, pp_p_value FROM c3p_naas_m_profile_parameter where pr_id in (SELECT pr_id FROM c3p_naas_m_profile where pr_name = %s) and pp_paramter in (%s,%s)"
                    logger.debug("c3p_camara_api:getProfileSpecs :: sql : %s", sql)
                    mycursor.execute(sql, (pf_name, 'radio', 'class',))
                    curr_prfl_val = mycursor.fetchall()
                    logger.debug("c3p_camara_api:getProfileSpecs :: current profile values(curr_prfl_val):%s",
                                 curr_prfl_val)

                    sql1 = "SELECT pr_id FROM c3p_naas_m_profile where pr_name = %s"
                    logger.debug("c3p_camara_api:getProfileSpecs :: sql1 : %s", sql1)
                    mycursor.execute(sql1, ('Default',))
                    pr_id = mycursor.fetchone()
                    logger.debug("c3p_camara_api:getProfileSpecs :: pr_id : %s", pr_id[0])

                    sql2 = "Select pp_paramter FROM c3p_naas_m_profile_parameter where pr_id in (%s)"
                    logger.debug("c3p_camara_api:getProfileSpecs :: sql2 : %s", sql2)
                    mycursor.execute(sql2, (pr_id[0],))
                    pr_para = mycursor.fetchall()
                    logger.debug("c3p_camara_api:getProfileSpecs :: pr_para : %s", pr_para)

                    for prfl in curr_prfl_val:
                        for para in pr_para:
                            if prfl[0] == para[0]:
                                update_sql = "Update c3p_naas_m_profile_parameter set pp_p_value = %s where pr_id =%s and pp_paramter = %s"
                                logger.debug("c3p_camara_api:getProfileSpecs :: update_sql : %s", update_sql)
                                mycursor.execute(update_sql, (prfl[1], pr_id[0], prfl[0],))
                                mydb.commit()

                    apibody.update({'dscp': "Default"})
                    func = ('Default',)
                    sql = "UPDATE c3p_rf_orders SET rfo_apibody = '{}' where rfo_id =%s".format(json.dumps(apibody))
                    logger.info("c3p_camara_api:getProfileSpecs :: sql: %s", sql)
                    mycursor.execute(sql, (soid,))
                    mydb.commit()
                profile_name = apibody.get("dscp")
                msisdn = apibody["ipV4address"]

            sql_profileinfo = "SELECT pr_customer, pr_region, pr_site_name, pr_hostname, pr_model, pr_os,  pr_os_ver, pr_family, pr_vendor, pr_function, pr_name, pr_internal_template, pr_id FROM c3p_naas_m_profile where pr_name =%s and  pr_function =%s"
            logger.info("c3p_camara_api:getProfileSpecs :: sql_profileinfo: %s", sql_profileinfo)
            mycursor.execute(sql_profileinfo, (profile_name, func[0],))
            profileinfo = list(mycursor.fetchone())
            logger.info("c3p_camara_api:getProfileSpecs :: profileinfo: %s", profileinfo)

            profileinfo.append(msisdn)

            if profileinfo[9] in ("gNodeB", 'Voice', 'Video_signaling', 'Video_Multimedia', 'Best_Effort', 'Default'):
                sql_mngmtip = "SELECT ue_ran_node FROM c3p_naas_m_ue_register where ue_msisdn = %s"
                logger.debug("c3p_camara_api:getProfileSpecs :: SQL is : %s", sql_mngmtip)
                mycursor.execute(sql_mngmtip, (msisdn,))
                mngmtip = mycursor.fetchone()
                profileinfo.append(mngmtip[0])

            elif profileinfo[9] == "QoS":
                sql_mngmtip = "SELECT ue_control_smf FROM c3p_naas_m_ue_register where ue_msisdn = %s"
                logger.debug("c3p_camara_api:getProfileSpecs :: SQL is : %s", sql_mngmtip)
                mycursor.execute(sql_mngmtip, (msisdn,))
                mngmtip = mycursor.fetchone()
                profileinfo.append(mngmtip[0])


    except Exception as err:
        logger.error("c3p_camara_api:getProfileSpecs :: Exception: %s", err)
    finally:
        mydb.close
    return profileinfo


def create_json(v_so_num, device_specs, row_id, param_feat, conn_flag, reso_id):
    data = {}
    wflow = False
    mydb = Connections.create_connection()

    try:
        mycursor = mydb.cursor(buffered=True)
        config_gen = []
        isFile = False
        # result = []
        non_temp_attrs = {}
        dyn_attr = []

        logger.debug("c3p_camara_api:create_json ::  device_specs : %s", device_specs)
        data["apiCallType"] = "external"
        data["customer"] = device_specs[0]
        data["region"] = device_specs[1]
        data["siteName"] = device_specs[2]
        data["hostname"] = device_specs[3]
        global d_host, res_id
        d_host = device_specs[3]
        data["model"] = device_specs[4]
        data["os"] = device_specs[5]
        data["osVersion"] = device_specs[6]
        data["deviceType"] = device_specs[4]  # --model
        data["deviceFamily"] = device_specs[7]
        data["vendor"] = device_specs[8]
        data["networkType"] = "PNF"
        data["vnfConfig"] = ""
        data["managementIp"] = device_specs[14]
        # data["managementIp"] = result[6] #--depending on pr_function from c3p_naas_m_profile
        data["userName"] = "admin"
        data["userRole"] = "admin"

        # depending on paramfunction need to add the condition

        attrs = {}
        specialftr = []

        data["requestType"] = "Config"
        rand_str2 = ''.join(random.choices(
            string.ascii_lowercase + string.digits, k=8)) + str(datetime.datetime.now())

        f_id = device_specs[11]

        sql_chrctr = "SELECT c_name,c_id FROM c3p_m_characteristics where c_f_id = %s"
        logger.debug("c3p_camara_api:create_json :: SQL is : %s", sql_chrctr)
        mycursor.execute(sql_chrctr, (f_id,))
        chrctr_info = mycursor.fetchall()

        sql_prfl = "SELECT pp_paramter,pp_p_value FROM c3p_naas_m_profile_parameter where pr_id = %s"
        logger.debug("c3p_camara_api:create_json :: SQL is : %s", sql_prfl)
        mycursor.execute(sql_prfl, (device_specs[12],))
        profil_par = mycursor.fetchall()

        for chr in chrctr_info:
            for pf_par in profil_par:
                if chr[0] == pf_par[0]:
                    attrs = {}
                    attrs['name'] = ""
                    attrs['characteriscticsId'] = chr[1]
                    attrs['type'] = "Non-Template"
                    attrs['label'] = chr[0]
                    attrs['value'] = pf_par[1]
                    attrs['templateid'] = ""
                    dyn_attr.append(attrs)
                    break

        sql_feature = "SELECT f_name FROM c3p_m_features where f_id= %s"
        logger.debug("c3p_camara_api:create_json :: SQL is : %s", sql_feature)
        mycursor.execute(sql_feature, (f_id,))
        feature_nm = mycursor.fetchone()

        non_temp_attrs["fId"] = f_id
        non_temp_attrs["fName"] = feature_nm[0]
        non_temp_attrs["fReplicationFlag"] = "False"
        specialftr.append(non_temp_attrs)

        config_gen.append('Non-Template')
        data["dynamicAttribs"] = dyn_attr
        data["selectedFeatures"] = specialftr
        data["certificationTests"] = {}
        data["configGenerationMethod"] = config_gen

        json_data = json.dumps(data)
        logger.debug("c3p_camara_api:create_json :: json_data: %s", json_data)

        mycursor.execute("update c3p_rfo_decomposed set od_request_json = %s where od_rowid=%s", (json_data, str(row_id),))
        logger.debug("c3p_camara_api:create_json :: record updated : %s", mycursor.rowcount)
        mydb.commit()
        logger.debug('c3p_camara_api:create_json :: json_data: %s', json_data)
        newHeaders = {"Content-type": "application/json",
                      "Accept": "application/json"}
        url = configs.get("C3P_Application")+ \
              configs.get("Config_Create")

        # req = requests.post(url, data=json_data, headers=newHeaders,
        #                    auth=(configs.get("api_auth_user"), configs.get("api_auth_pass")))
        req = requests.post(url, data=json_data, headers=newHeaders)

        resp = req.json()
        resp_json = resp
        if len(resp) == 0:
            wflow = True
        logger.debug('c3p_camara_api:create_json :: req JSON : %s', resp)

        dvc_sql = "SELECT d_id FROM c3p_deviceinfo where d_hostname=%s and d_mgmtip=%s"
        mycursor.execute(dvc_sql, (device_specs[3], device_specs[14],))

        logger.debug("c3p_camara_api:create_json :: dvc_sql : %s", dvc_sql)
        device_id = mycursor.fetchone()
        logger.debug("c3p_camara_api:create_json :: device_id : %s", device_id)

        sql = "update c3p_rfo_decomposed set od_requeststatus =%s,od_request_id=%s,od_req_resource_id=%s,od_request_version=%s where od_rowid=%s"
        logger.debug("create_json - sql :: %s", sql)
        mycursor.execute(sql, (resp_json['output'], resp_json['requestId'], str(device_id[0]), str(resp_json['version']), str(row_id), ))
        mydb.commit()
    except Exception as err:
        logger.error("c3p_camara_api:create_json :: Exception : %s", err)
    finally:
        mydb.close
    return wflow


'''{
    "output": "Submitted",
    "requestId": "SLGC-31D62BD",
    "version": 1.0
}'''


def camaraMonitorFunction():
    status = []
    mydb = Connections.create_connection()
    try:
        mycursor = mydb.cursor(buffered=True)
        ids = request.args['id']
        v_status = "SELECT rfo_status, rfo_updated_date FROM c3p_rf_orders WHERE rfo_id = %s"
        mycursor.execute(v_status, (ids,))
        rf_status = mycursor.fetchall()
        logger.debug("c3p_camara_api:camaraMonitorFunction ::  rf_status - %s", rf_status)
        status = rf_status[0]
        print(status[0], status[1], '\n')
    except Exception as err:
        logger.error("c3p_camara_api:camaraMonitorFunction :: Exception : %s", err)
    finally:
        mydb.close
    return (status[0] + ' \t ' + str(status[1]))


def camaranotification(so_num):
    return jsonify({"SO_number": request.json['SO_number'], "workflow_status": True})


def verify_input(req_json):
    mydb = Connections.create_connection()
    mycursor = mydb.cursor(buffered=True)
    msisdn = req_json["ueId"]["msisdn"]
    ipadd = req_json["asId"]["ipv4addr"]

    if not msisdn:
        return jsonify(
            {"code": "INVALID_ARGUMENT", "status": 400, "message": "Expected property is missing: ueId.msisdn"})

    valid_pattern = re.compile("[0-9]{11}")
    if not valid_pattern.match(msisdn):
        return jsonify(
            {"code": "INVALID_ARGUMENT", "status": 400, "message": "Expected Valid 11 digit msisdn"})

    verify_msisdn_sql = "SELECT * FROM c3p_naas_m_ue_register where ue_msisdn = %s"
    mycursor.execute(verify_msisdn_sql, (msisdn,))
    verify_msisdn = mycursor.fetchone()
    if not verify_msisdn:
        return jsonify({"code": "INVALID_ARGUMENT", "status": 400, "message": "Expected Valid msisdn"})

    if not ipadd:
        return jsonify(
            {"code": "INVALID_ARGUMENT", "status": 400, "message": "Expected property is missing: asId.ipv4addr"})
    else:
        ip = ipadd
        ipadd = ip.split("/")[0]
        print(ipadd)
        try:
            ipaddress.ip_address(ipadd)
        except Exception as e:
            return jsonify({"code": "INVALID_ARGUMENT", "status": 400, "message": "Invalid Ip"})

    if not req_json["asPorts"]["ports"]:
        return jsonify(
            {"code": "INVALID_ARGUMENT", "status": 400, "message": "Expected property is missing: asPorts.ports"})

    if not req_json["qos"]:
        return jsonify({"code": "INVALID_ARGUMENT", "status": 400, "message": "Expected property is missing: qos"})

    return False


def compute_nel_id(qualified_str):
    nel_id = uuid.uuid5(uuid.NAMESPACE_DNS, qualified_str)
    return str(nel_id)


def verify_del_id(id):
    mydb = Connections.create_connection()
    mycursor = mydb.cursor(buffered=True)

    logger.info("c3p_camara_api : verify_del_id :: id : %s", id)
    verify_id_sql = "SELECT rfo_status FROM c3p_rf_orders where rfo_nel_id =%s"
    logger.info("c3p_camara_api : verify_del_id:: verify_id_sql : %s", verify_id_sql)
    mycursor.execute(verify_id_sql, (id,))
    verify_status = mycursor.fetchone()
    logger.info("c3p_camara_api : verify_del_id:: verify_status : %s", verify_status)

    if not verify_status:
        return jsonify({"code": "INVALID_ARGUMENT", "status": 400, "message": "Invalid Id"})
    if verify_status[0] == 'Deleted':
        return jsonify({"Code": "Session deleted", "Message": "Id Already Deleted", "status": 200})
    else:
        return None


def verify_hmdvc_input(req_json):
    mydb = Connections.create_connection()
    mycursor = mydb.cursor(buffered=True)
    dscp_val = req_json["dscp"]
    ipadd = req_json["ipV4address"]

    verify_dscp_sql = "SELECT * FROM c3p_naas_m_profile where pr_name = %s"
    logger.debug("c3p_camara_api : verify_hmdvc_input:: verify_dscp_sql : %s", verify_dscp_sql)
    mycursor.execute(verify_dscp_sql, (dscp_val,))
    dscp_lst = mycursor.fetchone()
    logger.debug("c3p_camara_api : verify_hmdvc_input:: dscp_lst : %s", dscp_lst)

    if not dscp_val:
        return jsonify({"code": "INVALID_ARGUMENT", "status": 400, "message": "Expected property is missing: dscp"})

    # elif dscp_val not in dscp_lst:
    if not dscp_lst:
        return jsonify({"code": "INVALID_ARGUMENT", "status": 400, "message": "Invalid Id dscp"})

    if not ipadd:
        return jsonify(
            {"code": "INVALID_ARGUMENT", "status": 400, "message": "Expected property is missing: ipV4address"})
    else:
        try:
            ipaddress.ip_address(ipadd)
        except:
            return jsonify({"code": "INVALID_ARGUMENT", "status": 400, "message": "Invalid Ip"})


def create_device_json(lat, long, msisdn, row_id):
    data = {}
    crtfctn_test = {}
    wflow = False

    try:
        mydb = Connections.create_connection()
        mycursor = mydb.cursor(buffered=True)

        data["msisdn"] = msisdn
        data["os"] = "IOS"
        data["zone"] = "na"
        data["model"] = "AIR-CAP2702I-D-K9"
        data["region"] = "US"
        data["vendor"] = "Cisco"
        data["customer"] = "Bank Of America"
        data["hostname"] = "ATT-LAB-AP"
        data["siteName"] = "Century Printing"
        data["userName"] = "admin"
        data["userRole"] = "admin"
        data["osVersion"] = "15.3"
        data["vnfConfig"] = ""
        data["deviceType"] = ""
        data["templateId"] = "Latitude:{} Longitude:{}".format(lat, long)
        data["apiCallType"] = "external"
        data["networkType"] = "PNF"
        data["replication"] = []
        data["requestType"] = "Location Test"
        data["deviceFamily"] = "C2700"
        data["managementIp"] = "10.10.227.129"
        data["dynamicAttribs"] = []
        data["selectedFeatures"] = ""
        crtfctn_test["default"] = []
        test_details=  {
                "testCategory": "Others",
                "selected": 1,
                "testName": "CISCSR1000VUSPNIO16.09.01_DeviceLocationTest_1.0",
                "bundleName": []
            }
        crtfctn_test["dynamic"] = []
        crtfctn_test["dynamic"].append(test_details)
        data["certificationTests"] = crtfctn_test
        data["configGenerationMethod"] = ["Test"]

        json_data = json.dumps(data)
        logger.debug("c3p_camara_api:create_device_json :: json_data: %s", json_data)

        mycursor.execute(
            "update c3p_rfo_decomposed set od_request_json = %s where od_rowid=%s", (json_data, str(row_id),))
        logger.debug("c3p_camara_api:create_device_json :: record updated : %s", mycursor.rowcount)
        mydb.commit()
        logger.debug('c3p_camara_api:create_device_json :: json_data: %s', json_data)

        newHeaders = {"Content-type": "application/json", "Accept": "application/json"}
        url = configs.get("C3P_Application") + \
              configs.get("Config_Create")
        # req = requests.post(url, data=json_data, headers=newHeaders,auth=(configs.get("api_auth_user").data, configs.get("api_auth_pass").data))
        req = requests.post(url, data=json_data, headers=newHeaders)

        resp = req.json()
        resp_json = resp
        if len(resp) == 0:
            wflow = True
        logger.debug('c3p_camara_api:create_device_json :: req JSON : %s', resp)

        sql = "update c3p_rfo_decomposed set od_requeststatus =%s,od_request_id=%s,od_request_version=%s where od_rowid=%s" 
        logger.debug("create_device_json - sql :: %s", sql)
        mycursor.execute(sql, (resp_json['output'], resp_json['requestId'], str(resp_json['version']), str(row_id), ))
        mydb.commit()


    except Exception as err:
        logger.error("c3p_camara_api:create_device_json :: Exception : %s", err)
    finally:
        mydb.close
    return wflow