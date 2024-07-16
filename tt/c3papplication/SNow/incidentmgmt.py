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


def deviceinfo(mgmtip):
    mydb = Connections.create_connection()    
    try:
        mycursor = mydb.cursor(buffered=True)
        dvc_sql = "SELECT c_site_id, d_hostname, d_model, d_os, d_os_version, d_device_family, d_vendor, d_vnf_support, d_type, d_mgmtip,d_id FROM c3p_deviceinfo WHERE d_mgmtip = %s or d_hostname = %s"
        logger.debug("incidentmgmt:: dvc_sql: %s", dvc_sql)
        mycursor.execute(dvc_sql, (mgmtip,mgmtip,))
        dvc_detail = mycursor.fetchone()
        logger.debug("incidentmgmt:: dvc_detail: %s", dvc_detail)
    except Exception as err:
        logger.error("incidentmgmt:: deviceinfo: %s", err)
    finally:
        mydb.close()
    return dvc_detail

def custinfo(site_id):
    mydb = Connections.create_connection()    
    try:
        mycursor = mydb.cursor(buffered=True)
        cust_sql = "SELECT c_cust_name, c_site_region, c_cloudplat_zone, c_site_name FROM c3p_cust_siteinfo where id = %s"
        mycursor.execute(cust_sql, (site_id,))
        cust_detail = mycursor.fetchone()
        logger.debug("incidentmgmt:: cust_detail: %s", cust_detail)
    except Exception as err:
        logger.error("incidentmgmt:: custinfo: %s", err)
    finally:
        mydb.close()
    return cust_detail

def incidentmgntinfo(dvc_detail,category,subcategory):
    mydb = Connections.create_connection()    
    try:
        mycursor = mydb.cursor(buffered=True)
        im_sql = "SELECT im_feature_name,im_feature_id,im_template_name,im_template_id FROM c3p_m_incidentmgmt WHERE im_vendor = %s and im_family= %s and im_model = %s and im_os = %s and im_osversion = %s and im_networkfun = %s and im_category = %s and im_sub_catagory = %s"
        logger.debug("incidentmgmt:: im_sql: %s", im_sql)
        mycursor.execute(im_sql, (dvc_detail[6],dvc_detail[5],dvc_detail[2],dvc_detail[3],dvc_detail[4],dvc_detail[7],category,subcategory,))
        im_detail = mycursor.fetchone()
        logger.debug("incidentmgmt:: im_detail: %s", im_detail)
    except Exception as err:
        logger.error("incidentmgmtinfo:: %s", err)
    finally:
        mydb.close()
    return im_detail

def charactersticinfo(f_id):
    mydb = Connections.create_connection()    
    try:
        mycursor = mydb.cursor(buffered=True)
        cha_sql = "SELECT c_id,c_name FROM c3p_m_characteristics where c_f_id = %s"
        logger.debug("charactersticinfo:: dvc_sql: %s", cha_sql)
        mycursor.execute(cha_sql, (f_id,))
        cha_detail = mycursor.fetchall()
        logger.debug("incidentmgmt:: cha_detail: %s", cha_detail)
    except Exception as err:
        logger.error("incidentmgmt:: cha_detail: %s", err)
    finally:
        mydb.close()
    return cha_detail


def incidentmgmtconf(req_json):
    config_respns={}
    i=0
    fc_Values=[]
    fchar=[]
    logger.debug("incidentmgmt:: req_json: %s", req_json)
    incident = req_json["incident"][0]["incident"]
    category = req_json["incident"][0]["catageory"]
    config_item = req_json["incident"][0]["configuration_item"]
    subcategory= req_json["incident"][0]["subcategory"]
    description = req_json["incident"][0]["description"]
    source_System = req_json["source_System"]
    short_description=req_json["incident"][0]["short_description"]
    logger.debug("incidentmgmt:: short_description: %s %s %s %s", short_description,category,subcategory,config_item)
    fc_Values.append(short_description)

    try:
        deviceinf=deviceinfo(config_item)
        custinf=custinfo(deviceinf[0])
        incidentinfo=incidentmgntinfo(deviceinf,category,subcategory)
        chainfo=charactersticinfo(incidentinfo[1])
        logger.debug("incidentmgmt:: deviceinf[10]: %s%s", deviceinf[9],deviceinf[10])
        logger.debug("incidentmgmt:: incidentinfo: %s%s", incidentinfo[0],incidentinfo[1])
        logger.debug("incidentmgmt:: chainfo: %s", chainfo)
        for fcchar in chainfo:
            fc= {
                    "id": fcchar[0],
                    "name": fcchar[1],
                    "value": fc_Values[i],
                    "valueType": "string"
                }
            i+=1
            fchar.append(fc)
        config_json =  {
                            "resourceRelationship": [
                                {
                                    "resource": {
                                        "id": deviceinf[10],
                                        "operationalState": "operational",
                                        "activationFeature": [
                                            {
                                                "id":"Copy:::1:::" + incidentinfo[1],
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
        config_json=json.dumps(config_json)
        logger.debug("incidentmgmt::  config_json: %s",  config_json)
        newHeaders = {"Content-type": "application/json", "Accept": "application/json"}
        url = configs.get("Python_Application") + "/c3p-p-core/api/ResourceFunction/v4/"
        config_respns = requests.patch(url, data=config_json, headers=newHeaders,verify=False)
        config_respns=json.dumps( config_respns.json())
        logger.debug("incidentmgmt:: config_respnse: %s", config_respns)

    except Exception as err:
        logger.error("incidentmgmt:: error: %s", err)
        config_respns={"error":"Incident management config error"}
    return config_respns