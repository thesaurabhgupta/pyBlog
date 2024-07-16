import json
from flask import jsonify
import logging
from c3papplication.common import Connections
from c3papplication.conf.springConfig import springConfig
from jproperties import Properties
import geopy.distance
import re

# filename = ""
configs = springConfig().fetch_config()
logger = logging.getLogger(__name__)


def dvc_locatn_test(req_json):
    mydb = Connections.create_connection()
    mycursor = mydb.cursor(buffered=True)
    try:
        so_num = req_json["so_number"]
        lat = req_json["latitude"]
        long = req_json["longitude"]
        json_sql = "SELECT rfo_apibody FROM c3p_rf_orders where rfo_id =%s"
        logger.info("test_dvclctn:dvc_locatn_test :: json_sql: %s", json_sql)
        mycursor.execute(json_sql, (so_num,))
        json_body = mycursor.fetchone()
        logger.info("test_dvclctn:dvc_locatn_test :: json_body: %s", json_body)
        json_body = json.loads(json_body[0])

        msisdn = json_body['ueId']['msisdn']
        latitude = json_body['latitude']
        longitude = json_body['longitude']
        # lat = str(latitude).split(".")
        # lat = lat[0]
        # logger.debug("test_dvclctn:dvc_locatn_test :: lat: %s", lat)
        # long = (str(longitude).split("."))[0]

        accuracy = json_body['accuracy']
        coords_1 = (latitude, longitude)
        acc_per = (accuracy + accuracy * 30 / 100)

        # lat_long_sql = f"Select ue_latitude,ue_longitude from c3p_naas_m_ue_register where ue_msisdn ='{msisdn}'"
        # logger.info("test_dvclctn:dvc_locatn_test :: lat_long_sql: %s", lat_long_sql)
        # mycursor.execute(lat_long_sql)
        # lat_long_val = (mycursor.fetchone())
        # logger.info("test_dvclctn:dvc_locatn_test :: lat_long_val: %s", lat_long_val)

        # k = {}
        lst_diff = []  # shr
        # for i in lat_long_val:
        coords_2 = (lat,long)
        diff = geopy.distance.geodesic(coords_1, coords_2).m

        output_json = {}
        logger.info("test_dvclctn:dvc_locatn_test :: diff: %s", diff)
        output_json["Expected_Distance"] = accuracy
        output_json["Actual_Distance"] = round(diff,2)
        output_json["Collected_values"] = "Latitude:{} Longitude:{}".format(coords_2[0], coords_2[1])

        #site_name_sql = f"Select ue_control_amf from c3p_naas_m_ue_register where ue_latitude ='{coords_2[0]}' and ue_longitude ='{coords_2[1]}'"
        #logger.info("test_dvclctn:dvc_locatn_test :: site_name_sql: %s", site_name_sql)
        #mycursor.execute(site_name_sql)
        #site_name = mycursor.fetchone()
        #output_json["site_name"] = site_name[0]

        if diff < accuracy:
            output_json["value"] = "Matched"
            lst_diff.append(output_json)  # shr
        elif (accuracy < diff < acc_per):
            output_json["value"] = "Partially Matched"
            lst_diff.append(output_json)  # shr
        else:
            output_json["value"] = "Not Matched"
            lst_diff.append(output_json)  # shr
        response = lst_diff  # shr
        # response = output_json
        logger.debug("test_dvclctn:dvc_locatn_test :: response : %s", response)
        return response
    except Exception as e:
        logger.error("test_dvclctn:dvc_locatn_test :: error: %s", e)


def verify_dvc_input(req_json):
    try:
        mydb = Connections.create_connection()
        mycursor = mydb.cursor(buffered=True)

        logger.info("Inside Verify Dvc")
        # so_num = req_json["so_number"]
        # json_sql = "SELECT rfo_apibody FROM c3p_rf_orders where rfo_id ='{}'".format(so_num)
        # mycursor.execute(json_sql)
        # logger.info("c3p_dvclctn: verify_dvc_input :: json_sql: %s",json_sql)
        # json_body = mycursor.fetchone()
        # json_body= json.loads(json_body[0])
        json_body = req_json

        accuracy = json_body['accuracy']
        msisdn = json_body['ueId']['msisdn']
        latitude = json_body['latitude']
        longitude = json_body['longitude']
        logger.debug("c3p_dvclctn: verify_dvc_input :: msisdn: %s", msisdn)

        # if accuracy < 100:
        #     return {"undetermined input": "too small accuracy"}

        valid_pattern = re.compile("[0-9]{11}")
        if not valid_pattern.match(msisdn):
            logger.debug("Inside Not Matched")
            return jsonify({"code": "INVALID_ARGUMENT", "status": 400, "message": "Expected Valid 11 digit msisdn"})

        verify_msisdn_sql = "SELECT * FROM c3p_naas_m_ue_register where ue_msisdn = %s"
        logger.debug("verify_msisdn_sql %s", verify_msisdn_sql)
        mycursor.execute(verify_msisdn_sql, (msisdn,))
        verify_msisdn = mycursor.fetchone()
        logger.debug("verify_msisdn %s", verify_msisdn)
        if not verify_msisdn:
            return jsonify({"code": "INVALID_ARGUMENT", "status": 400, "message": "Expected Valid msisdn"})

        if not latitude:
            return jsonify({"code": "INVALID_ARGUMENT", "status": 400,"message": "Expected Valid latitude"})

        if not longitude:
            return jsonify({"code": "INVALID_ARGUMENT", "status": 400, "message": "Expected Valid longitude"})

        if (latitude > 90 or latitude < -90) or (longitude > 180 or longitude < -180):
            return jsonify({"code": "INVALID_ARGUMENT", "status": 400, "message": "Expected Valid latitude or longitude"})

        return False

    # except Exception as e:
    #     logger.debug("e value %s", e)
    #     if str(e) in ("'ueId'", "'latitude'", "'longitude'", "'accuracy'", "'msisdn'"):
    #         return jsonify(
    #             {"code": "INVALID_ARGUMENT", "status": 400, "message": "Expected {} in json body ".format(e)})
    #     else:
    #         return jsonify({"code": "INVALID_ARGUMENT", "status": 400, "message": "Invalid json body"})
    except Exception as e:
        logger.error("Error in verify_dvc_inputq: %s", e)
        return {"code": "INVALID_ARGUMENT", "status":400, "message":"Invalid json body"}


def lat_long_ext(req_json):
    msisdn = req_json['msisdn']
    mydb = Connections.create_connection()
    mycursor = mydb.cursor(buffered=True)

    lat_long_sql = "Select ue_latitude,ue_longitude from c3p_naas_m_ue_register where ue_msisdn =%s"
    logger.info("test_dvclctn:dvc_locatn_test :: lat_long_sql: %s", lat_long_sql)
    mycursor.execute(lat_long_sql, (msisdn, ))
    lat_long_val = (mycursor.fetchone())
    logger.info("test_dvclctn:dvc_locatn_test :: lat_long_val: %s", lat_long_val)
    if lat_long_val:
        return {"Status":"Success","latitude":lat_long_val[0],"longitude":lat_long_val[1]}
    else:
        return {"Status":"Expected a Valid Msisdn"}

# #test Purpose
# req_jsn = {
# "ueId": {"msisdn" :"41793834315"},
# "latitude" :19.246,
# "longitude" :72.956,
# "accuracy" :11}
#

# req_jsn= {
#     "so_number": "SOPO202307101381613"
# }
# print("output",(dvc_locatn_test(req_jsn)))
# #print("output",(verify_dvc_input(req_jsn)))
