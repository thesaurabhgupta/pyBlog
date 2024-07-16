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



def incidentworkflow(req_json):
    category = req_json.get("category")
    config_item = req_json.get("Configuration_item")
    description = req_json.get("description")
    source_System = req_json.get("source_System")
    mydb = Connections.create_connection()

    try:
        mycursor = mydb.cursor(buffered=True)
        dvc_sql = "SELECT c_site_id, d_hostname, d_model, d_os, d_os_version, d_device_family, d_vendor, d_vnf_support, d_type, d_mgmtip FROM c3p_deviceinfo WHERE d_mgmtip =%s or d_hostname = %s"
        logger.debug("incidentworkflow:: dvc_sql: %s", dvc_sql)
        mycursor.execute(dvc_sql, (config_item,config_item,))
        dvc_detail = mycursor.fetchone()
        logger.debug("incidentworkflow:: dvc_detail: %s", dvc_detail)

        cust_sql = "SELECT c_cust_name, c_site_region, c_cloudplat_zone, c_site_name FROM c3p_cust_siteinfo where id = %s"
        mycursor.execute(cust_sql, (dvc_detail[0],))
        cust_detail = mycursor.fetchone()
        logger.debug("incidentworkflow:: cust_detail: %s", cust_detail)

        resource_json = {
    "configGenerationMethod": [
        "Test"
    ],
    "apiCallType": "external",
    "customer": "Tech Mahindra Ltd",
    "region": "us",
    "siteName": "Middletown",
    "zone": "na",
    "hostname": "ATT-LAB-AP",
    "model": "AIR-CAP2702I-D-K9",
    "os": "IOS",
    "osVersion": "15.3",
    "deviceType": "Router",
    "deviceFamily": "ATT-LAB-AP",
    "vendor": "Cisco",
    "templateId": "",
    "networkType": "PNF",
    "requestType": "Test",
    "vnfConfig": "",
    "managementIp": "10.10.227.129",
    "selectedFeatures": [],
    "dynamicAttribs": [],
    "certificationTests": {
        "dynamic": [
            {
                "bundleName": [],
                "selected": 1,
                "testCategory": "Health Check",
                "testName": "CISC2700USPN$$_CheckRadioInterfaceAP_1.4"
            }
        ],
        "default": [
            {
                "testCategory": "Standard Tests",
                "selected": 0,
                "testName": "Frameloss",
                "bundleName": []
            },
            {
                "testCategory": "Standard Tests",
                "selected": 0,
                "testName": "Latency",
                "bundleName": []
            },
            {
                "testCategory": "Standard Tests",
                "selected": 0,
                "testName": "Throughput",
                "bundleName": []
            }
        ]
    },
    "replication": [],
    "userName": "admin",
    "userRole": "admin"
}
        newHeaders = {"Content-type": "application/json", "Accept": "application/json"}
        url = configs.get("Python_Application") + "/c3p-p-core/api/testRequest"
        test_respns = requests.post(url, data=json.dumps(resource_json), headers=newHeaders, verify=False)
        logger.debug("incidentworkflow:: test_respnse: %s", test_respns.json())

        req_responc = req_status((test_respns.json()))
        logger.debug("incidentworkflow:: req_responc: %s", req_responc)
        so_id = req_responc["so_id"]
        finalReport_json = json.dumps({"soNumber": so_id})

        req_response = final_report(finalReport_json,source_System,category)

        logger.debug("incidentworkflow:: req_response_1: %s", req_response)

        if "Device" in req_response:
            logger.debug("incidentworkflow:: req_response_1: Inside Device req_response %s",req_response["Device"])
            if req_response["Device"] == "Down":
                data = {"Status":"Resolved","Status_Reason":"ATT device","Resolution":req_response["Device"]}
                notification(source_System,data,category)
                return json.dumps({"Status":"Interface Down"})

        output_json = ({
            "os": dvc_detail[3],
            "zone": cust_detail[2],
            "model": dvc_detail[2],
            "region": cust_detail[1],
            "vendor": dvc_detail[6],
            "customer": cust_detail[0],
            "hostname": dvc_detail[1],
            "siteName":  cust_detail[3],
            "userName": "admin",
            "userRole": "admin",
            "osVersion": dvc_detail[4],
            "vnfConfig": "",
            "deviceType": dvc_detail[8],
            "templateId": "",
            "apiCallType": "external",
            "networkType": dvc_detail[7],
            "replication": [],
            "requestType": "Test",
            "deviceFamily": dvc_detail[5],
            "managementIp": dvc_detail[9],
            "dynamicAttribs": [],
            "selectedFeatures": [],
            "certificationTests": {
                "default": [
                    {
                        "selected": 0,
                        "testName": "Frameloss",
                        "bundleName": [],
                        "testCategory": "Standard Tests"
                    },
                    {
                        "selected": 0,
                        "testName": "Latency",
                        "bundleName": [],
                        "testCategory": "Standard Tests"
                    },
                    {
                        "selected": 0,
                        "testName": "Throughput",
                        "bundleName": [],
                        "testCategory": "Standard Tests"
                    }
                ],
                "dynamic": [
                    {
                        "selected": 1,
                        "testName": "CISCSR1000VUSPN$$_CheckInterfaceGi2_1.4",
                        "bundleName": [],
                        "testCategory": "Network Test"
                    }
                ]
            },
            "configGenerationMethod": [
                "Test"
            ]
        })
        logger.debug("incidentworkflow:: output_json: %s",json.dumps(output_json))
        output_json = json.dumps(output_json)

        newHeaders = {"Content-type": "application/json", "Accept": "application/json"}
        url = configs.get("Python_Application")+ "/c3p-p-core/api/testRequest"
        test_respnse = requests.post(url, data=output_json, headers=newHeaders,verify=False)
        logger.debug("incidentworkflow:: test_respnse: %s",test_respnse.json())


        req_response = req_status((test_respnse.json()))
        so_id = req_response["so_id"]

        finalReport_json =json.dumps({"soNumber":so_id})
        
        config_respnc = final_report(finalReport_json,source_System,category)

        logger.debug("incidentworkflow:: config_respnc: %s",config_respnc)


        if "Device" in config_respnc:
                if ((config_respnc["Device"]).strip()).lower() == "up":
                    return config_respnc
                else:
                    req_response = req_status(config_respnc)
                    logger.debug("incidentworkflow:: req_response: %s",req_response)

                    newHeaders = {"Content-type": "application/json", "Accept": "application/json"}
                    url = configs.get("Python_Application") + "/c3p-p-core/api/testRequest"
                    test_respnse = requests.post(url, data=output_json, headers=newHeaders,verify=False)
                    logger.debug("incidentworkflow:: test_respnse: %s", test_respnse.json())

                    req_response = req_status(test_respnse.json())
                    so_id = req_response["so_id"]

                    finalReport_json = json.dumps({"soNumber": so_id})
                    finalreport = final_report(finalReport_json,source_System,category)
                    logger.debug("incidentworkflow:: finalreport:%s",finalreport)


    except Exception as err:
        logger.debug("incidentworkflow:: Exception: %s", err)

    finally:
        mydb.close()

    return finalreport

def req_status(req_json):
    try:

        mydb = Connections.create_connection()
        mycursor = mydb.cursor(buffered=True)

        if "href" in req_json:
            so_id = ((req_json.get("href")).split("="))[-1]
            logger.debug("incidentworkflow:: so_id: %s", so_id)

        status_query = "SELECT od_requeststatus FROM c3p_rfo_decomposed where od_rfo_id = %s"
        logger.debug("incidentworkflow:: status_sql: %s", status_query)
        mycursor.execute(status_query, (so_id,))
        test_status = mycursor.fetchone()

        while test_status[0] == "Submitted":
            mydb = Connections.create_connection()
            mycursor = mydb.cursor(buffered=True)
            status_query = "SELECT od_requeststatus FROM c3p_rfo_decomposed where od_rfo_id = %s"
            logger.debug("incidentworkflow:: status_while_sql: %s", status_query)
            mycursor.execute(status_query, (so_id,))
            test_status = mycursor.fetchone()
            logger.debug("incidentworkflow:: test_status_while: %s", test_status[0])
            time.sleep(5)
            mydb.close()

    except Exception as err:
        logger.debug("incidentworkflow:: Exception: %s", err)

    finally:
        mydb.close()
        return {"so_id":so_id,"status":test_status[0]}


def final_report(req_json,source_system,category):
    try:
        finalReport_json = req_json
        newHeaders = {"Content-type": "application/json", "Accept": "application/json"}
        url = configs.get("C3P_Application") +"/c3p-j-core/GetReportData/finalreport/external"
        finalReport_respns = requests.post(url, data=finalReport_json, headers=newHeaders,verify=False)
        logger.debug("incidentworkflow:: finalReport_respnse: %s", finalReport_respns.json())
        finalReport_respnse = finalReport_respns.json()

        otpt_val = finalReport_respnse["output"][0]["entity"][0]

        if otpt_val["Network"] != []:
            coll_json = otpt_val["Network"][0]

        elif otpt_val["Health_Check"] != []:
            coll_json = otpt_val["Health_Check"][0]

        logger.debug("incidentworkflow:: coll_json: %s", coll_json)
        collected_val = coll_json["CollectedValue"]
        logger.debug("incidentworkflow:: collected_val: %s", collected_val)

        if (collected_val.strip() == 'up' or collected_val.strip() == 'Not Found' ):
            logger.debug("notification Log")
            data ={"Status":"Resolved","Status_Reason":"Conducted Test on Device","Resolution":collected_val}
            notification(source_system, data,category)
            return {"Incident": "Closed","Device": collected_val}

        elif (collected_val == 'administratively down' or collected_val == 'down' or collected_val == 'admin' or collected_val == 'administratively down down'):
            data = {"Status": "Resolved", "Status_Reason": "Conducted Test on Device", "Resolution": collected_val}
            notification(source_system, data, category)

            config_json = {
                "resourceRelationship": [
                    {
                        "resource": {
                            "id": "9982081",
                            "operationalState": "operational",
                            "activationFeature": [
                                {
                                    "id": "Copy:::1:::F100132",
                                    "name": "InterfaceStatRestore",
                                    "isBundle": False,
                                    "featureCharacteristic": [
                                        {
                                            "id": "C20201012100000",
                                            "name": "yesorno",
                                            "value": "no",
                                            "valueType": "string"
                                        }
                                    ]
                                }
                            ]
                        },
                        "relationshipType": "contains"
                    }
                ]
            }

            config_json=json.dumps(config_json)
            newHeaders = {"Content-type": "application/json", "Accept": "application/json"}
            url = configs.get("Python_Application") + "/c3p-p-core/api/ResourceFunction/v4/"
            config_respns = requests.patch(url, data=config_json, headers=newHeaders,verify=False)
            logger.debug("incidentworkflow:: config_respnse: %s", config_respns.json())

            req_json1 = config_respns.json()
            if "href" in req_json1:
                href = req_json1.get("href")
                logger.debug("incidentworkflow:: href: %s", href)


            return {"Incident": "Inprogress","Device": "Down","href":href}

    except Exception as err:
        logger.debug("incidentworkflow: final_report :: Exception: %s", err)


def notification(source_system,data,category):
    mydb = Connections.create_connection()
    try:
        mycursor = mydb.cursor(buffered=True)

        if source_system == "CEBMCIN1":
            mycursor.execute("SELECT ss_name FROM c3p_m_source_system where ss_code= %s", (source_system,))
            verify_source = mycursor.fetchone()
            logger.debug("incidentworkflow::notification - verify_source - %s", verify_source)

            if verify_source[0] == "BMC":
                jsondt = data
                mycursor.execute("SELECT srm_response_url,srm_auth_u_param,srm_auth_p_param "
                                 "FROM c3p_m_ss_response_mapping "
                                 "where srm_ss_code=%s and srm_module_code='CMNOTITK'", (source_system,))
                url_tokn = mycursor.fetchone()
                logger.debug("incidentworkflow::notification:BMC - URL_tokn - %s", url_tokn)

                headers = {"Authorization": "AR-JWT{{jwt}}", "Content-Type": "application/x-www-form-urlencoded","Connection": "keep-alive"}

                login_data = {}
                login_data["username"] = url_tokn[1]
                login_data["password"] = url_tokn[2]
                logger.debug("incidentworkflow::notification:BMC - login_data - %s", login_data)

                token = requests.request("POST", url_tokn[0], headers=headers, data=login_data)
                logger.debug("incidentworkflow::notification:BMC - token - %s", token.text)

                mycursor.execute("SELECT srm_response_url "
                                 "FROM c3p_m_ss_response_mapping "
                                 "where srm_ss_code='" + source_system + "' and srm_module_code='CMNOTIIN'")
                url_actual = mycursor.fetchone()
                logger.debug("incidentworkflow::notification:BMC - URL_Actual - %s", url_actual)

                url_2 = str((url_actual[0]) +'"'+category+'"')
                headers2 = {  'Content-Type': 'application/json','Authorization': 'AR-JWT{{jwt}}','Cookie': 'AR-JWT='+token.text+''}
                response = requests.request("GET",url_2, headers=headers2)
                respnse = response.json()
                logger.debug("incidentworkflow::notification:BMC - json_resp - %s", respnse)
                incident_number = respnse["entries"][0]["values"]["Request ID"]

                mycursor.execute("SELECT srm_response_url "
                                 "FROM c3p_m_ss_response_mapping "
                                 "where srm_ss_code='" + source_system + "' and srm_module_code='CMNOTIAC'")
                url_actual = mycursor.fetchone()
                logger.debug("incidentworkflow::notification:BMC - URL_Actual - %s", url_actual)

                url_3 = str((url_actual[0]) + incident_number)
                data = json.dumps({"values":{"Status":"Resolved","Status_Reason":"Request","Resolution":"InProcess_Shr-Test done"}})
                response = requests.request("PUT",url_3, headers=headers2,data=data)
                logger.debug("incidentworkflow::notification:BMC - json_resp - %s", response)

                logger.debug('notification - Response JSON :: %s', response)
                logger.debug('notification - Status Code :: %s', response.status_code)
                if response.status_code == 204:
                    data = {"workflow_status": True}
                else:
                    data = {"workflow_status": False}

    except Exception as err:
        logger.error("incidentworkflow::notification:Exception in notification: %s", err)
    finally:
        mydb.close
    return data