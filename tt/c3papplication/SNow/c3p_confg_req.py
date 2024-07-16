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

def configrequest(req_json):
    result={}
    device_Id = req_json.get("deviceId")
    booking_Id = req_json.get("bookingId")
    scheduled = req_json.get("scheduled")
    source_System = req_json.get("sourceSyetem")
    mydb = Connections.create_connection()
    try:

        newHeaders = {"Content-type": "application/json",
                          "Accept": "application/json"}
        url = configs.get("Python_Application") + "/c3p-p-core/api/ResourceFunction/v4/"
        config_json = {
            "resourceRelationship": [
              {
                "resource": {
                  "id": "9982081",
                  "operationalState": "operational",
                  "activationFeature": [
                    {
                      "id": "Copy:::1:::F264",
                      "name": "Day0_config",
                      "isBundle": False,
                      "featureCharacteristic": [
                        {
                          "id": "CH-2023100368F349",
                          "name": "loopbackIPaddress",
                          "value": "10.179.74.25",
                          "valueType": "string"
                        },
                        {
                          "id": "CH-202310038C7A0C",
                          "name": "loopbackSubnetMask",
                          "value": "255.255.255.0",
                          "valueType": "string"
                        },
                        {
                          "id": "CH-202310038B5072",
                          "name": "hostname",
                          "value": "GMUVMD35913-09",
                          "valueType": "string"
                        }
                      ]
                    }
                  ]
                },
                "relationshipType": "contains"
              }
            ],
            "certificationTests": {
              "dynamic": [
                {
                  "testCategory": "Network Test",
                  "selected": 1,
                  "testName": "CISCSR1000V$PNIO16.09.01_version check_1.4",
                  "bundleName": []
                },
                {
                  "testCategory": "Health Check",
                  "selected": 1,
                  "testName": "CISCSR1000V$PNIO16.09.01_Platform_diag_1.0",
                  "bundleName": []
                },
                {
                  "testCategory": "Health Check",
                  "selected": 1,
                  "testName": "CISCSR1000V$PNIO16.09.01_Port_Enablement1_1.0",
                  "bundleName": []
                }
              ],
              "default": []
            }
          }
        
        mycursor = mydb.cursor(buffered=True)
        dvc_sql = "SELECT  d_id FROM c3p_deviceinfo where d_id = %s"
        logger.debug("SNow:configrequest:: dvc_ID: %s", dvc_sql)
        mycursor.execute(dvc_sql, (device_Id,))
        dvc_Id = mycursor.fetchone()
        if dvc_Id is not None:
          if scheduled['schedule']=="immediate":
              config_json=json.dumps(config_json)
              config_respns = requests.patch(url, data=config_json, headers=newHeaders,verify=False)
              logger.debug("SNow:: config_respnse: %s", config_respns.json())
              config_respns=config_respns.json()
              if "href" in config_respns:
                  so_id = ((config_respns.get("href")).split("="))[-1]
                  logger.debug("config:: so_id: %s", so_id)
                  mycursor = mydb.cursor(buffered=True)
                  updatesql = "UPDATE c3p_rf_orders set rfo_booking_id = %s where rfo_id = %s"
                  mycursor.execute(updatesql, (booking_Id,so_id))
                  mydb.commit()
              result = config_respns
          else: 
              logger.debug("scheduler is not enabled") 
              result ={"Error": "scheduler is not enabled"}
        else:
            result ={"Error": "Device Id is not found"}
                           
    except Exception as err:
        logger.debug("SNow:: config_respnse: Exception: %s", err)
        result = {"Error": "Unkown error"}
    finally:
        mydb.close()
    return result