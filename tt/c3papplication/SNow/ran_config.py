import time
from flask import request, jsonify
import requests
import json
import logging
from jproperties import Properties
from c3papplication.common import Connections
from c3papplication.conf.springConfig import springConfig

configs = springConfig().fetch_config()

logger = logging.getLogger(__name__)

def ran_conf(req_json):
    try:
        mydb = Connections.create_connection()
        mycursor = mydb.cursor(buffered=True)
        i = 0
        fc_Values = {}
        fchar = []
        result={}
        category = req_json.get("catageory")
        configuration_item = req_json.get("configuration_item")
        subcategory = req_json.get("subcategory")
        port_No = req_json.get("port_No")
        VLan = req_json.get("VLan")
        source_System = req_json.get("source_System")
        ran_config_item = req_json["ran_config"]["config_item"]
        ran_category = req_json["ran_config"]["category"]
        ran_subcategory = req_json["ran_config"]["subcategory"]

        if subcategory == "L2vpn":
            fc_Values["port_No"] = port_No
            fc_Values["VLan"] = VLan
            logger.debug("incidentmgmt:: fc_Value: %s", fc_Values)
            #fc_Values.append(fc_Value)

        deviceinf = deviceinfo(configuration_item)
        incidentinfo = incidentmgntinfo(deviceinf, category, subcategory)
        chainfo = charactersticinfo(incidentinfo[1])
        logger.debug("ran_config:ran_conf :: deviceinf[10]: %s%s", deviceinf[9], deviceinf[10])
        logger.debug("ran_config:ran_conf :: incidentinfo: %s%s", incidentinfo[0], incidentinfo[1])
        logger.debug("ran_config:ran_conf :: chainfo: %s", chainfo)

        for fcchar in chainfo:
            for i in (req_json.keys()):
                if fcchar[1] == i:
                    value = fc_Values[i]

                    fc = {
                        "id": fcchar[0],
                        "name": fcchar[1],
                        "value": value,
                        "valueType": "string"
                        }
                    #i += 1
                    fchar.append(fc)
        config_json = {
            "resourceRelationship": [
                {
                    "resource": {
                        "id": deviceinf[10],
                        "operationalState": "operational",
                        "activationFeature": [
                            {
                                "id": "Copy:::1:::" + incidentinfo[1],
                                "name": incidentinfo[0],
                                "isBundle": False,
                                "featureCharacteristic": fchar
                            }
                        ]
                    },
                    "relationshipType": "contains"
                }
            ]
        }
        config_json = json.dumps(config_json)
        logger.debug("ran_config:ran_conf ::  config_json: %s", config_json)
        newHeaders = {"Content-type": "application/json", "Accept": "application/json"}
        url = configs.get("Python_Application") + "/c3p-p-core/api/ResourceFunction/v4/"

        config_respns = requests.patch(url, data=config_json, headers=newHeaders, verify=False)
        config_respns = config_respns.json()
        logger.debug("ran_config:ran_conf :: config_respnse: %s", config_respns)
        response = config_respns
        if "href" in config_respns:
            #href = config_respns["href"]
            so_id = ((config_respns["href"]).split("="))[-1]

        status_query = "SELECT od_requeststatus FROM c3p_rfo_decomposed where od_rfo_id = %s"
        logger.debug("ran_config:ran_conf :: status_sql: %s", status_query)
        mycursor.execute(status_query, (so_id,))
        test_status = mycursor.fetchone()
        count = 0

        while count <= 55:
            mydb = Connections.create_connection()
            mycursor = mydb.cursor(buffered=True)

            if test_status[0] == "Success" or test_status[0] == "Failure":
                if test_status[0] == "Success":
                    logger.debug('ran_config:ran_conf :: Response: %s', "Success")

                    deviceinf = deviceinfo(ran_config_item)
                    logger.debug("ran_config:ran_conf :: deviceinf : %s", deviceinf)
                    dvc_id = deviceinf[10]
                    logger.debug("ran_config:ran_conf :: dvc_id : %s", dvc_id)
                    where_clause = "where device_id = {} and pd_status = 'planned'".format(dvc_id)
                    fetch_json_sql = "SELECT pd_tmf_json FROM c3p_t_planning_data {}".format(where_clause)
                    logger.debug("ran_config:ran_conf :: fetch_json_sql : %s", fetch_json_sql)
                    mycursor.execute(fetch_json_sql)
                    pd_tmf_json = (mycursor.fetchone())[0]
                    logger.debug("ran_config:ran_conf :: pd_tmf_json : %s", pd_tmf_json)

                    newHeaders = {"Content-type": "application/json", "Accept": "application/json"}
                    url = configs.get("Python_Application") + "/c3p-p-core/api/ResourceFunction/v4/?id=RF10001"
                    logger.debug("ran_config:ran_conf :: url : %s", url)
                    ran_respns = requests.patch(url, data=pd_tmf_json, headers=newHeaders, verify=False)
                    logger.debug("ran_config:ran_conf :: ran_respns: %s", ran_respns)
                    #response = config_respns.json()
                    #logger.debug("ran_config:ran_conf :: config_respnse: %s", response)
                    break

                else:
                    logger.debug('ran_config:ran_conf :: Response: %s', "Failure")
                    response ={"Status":"Config Request is failed for Device {}".format(configuration_item)}
                    break

            status_query = "SELECT od_requeststatus FROM c3p_rfo_decomposed where od_rfo_id = %s"
            logger.debug("ran_config:ran_conf :: status_sql_while: %s", status_query)
            mycursor.execute(status_query, (so_id,))
            test_status = mycursor.fetchone()
            logger.debug("ran_config:ran_conf :: test_status_while: %s", test_status[0])
            time.sleep(5)
            mydb.close()
            count += 1
            #response = "Failed"

    except Exception as err:
        logger.error("ran_config:ran_conf :: error: %s", err)
        response = {"error": "Ran config error"}
    return response


def deviceinfo(mgmtip):
    mydb = Connections.create_connection()
    try:
        mycursor = mydb.cursor(buffered=True)
        dvc_sql = "SELECT c_site_id, d_hostname, d_model, d_os, d_os_version, d_device_family, d_vendor, d_vnf_support, d_type, d_mgmtip,d_id FROM c3p_deviceinfo WHERE d_mgmtip = %s or d_hostname = %s"
        logger.debug("ran_config:deviceinfo :: dvc_sql: %s", dvc_sql)
        mycursor.execute(dvc_sql, (mgmtip, mgmtip,))
        dvc_detail = mycursor.fetchone()
        logger.debug("ran_config:deviceinfo :: dvc_detail: %s", dvc_detail)
    except Exception as err:
        logger.error("ran_config:deviceinfo:: Error: %s", err)
    finally:
        mydb.close()
    return dvc_detail


def charactersticinfo(f_id):
    mydb = Connections.create_connection()
    try:
        mycursor = mydb.cursor(buffered=True)
        cha_sql = "SELECT c_id,c_name FROM c3p_m_characteristics where c_f_id = %s"
        logger.debug("ran_config:charactersticinfo :: dvc_sql: %s", cha_sql)
        mycursor.execute(cha_sql, (f_id,))
        cha_detail = mycursor.fetchall()
        logger.debug("ran_config:charactersticinfo :: cha_detail: %s", cha_detail)
    except Exception as err:
        logger.error("ran_config:charactersticinfo :: Error: %s", err)
    finally:
        mydb.close()
    return cha_detail


def incidentmgntinfo(dvc_detail,category,subcategory):
    mydb = Connections.create_connection()
    try:
        mycursor = mydb.cursor(buffered=True)
        im_sql = "SELECT im_feature_name,im_feature_id,im_template_name,im_template_id FROM c3p_m_incidentmgmt where im_vendor = %s and im_family= %s and im_model = %s and im_os = %s and im_osversion = %s and im_networkfun = %s and im_category = %s and im_sub_catagory = %s"
        logger.debug("ran_config:: im_sql: %s", im_sql)
        mycursor.execute(im_sql, (dvc_detail[6],dvc_detail[5],dvc_detail[2],dvc_detail[3],dvc_detail[4],dvc_detail[7],category,subcategory,))
        im_detail = mycursor.fetchone()
        logger.debug("ran_config:incidentmgntinfo :: im_detail: %s", im_detail)
    except Exception as err:
        logger.error("ran_config:incidentmgntinfo :: Error: %s", err)
    finally:
        mydb.close()
    return im_detail