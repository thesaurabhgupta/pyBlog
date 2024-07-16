import json
from c3papplication.common import Connections
import json, logging
from flask import jsonify
from c3papplication.camara import c3p_camara_api

logger = logging.getLogger(__name__)

#check
def camara_qod_details(nel_id):
    mydb = Connections.create_connection()
    try:
        mycursor = mydb.cursor(buffered=True)
        camara_nel_id = str(nel_id)
        camara_nel_id = camara_nel_id.replace('\r\n','').replace('\n','')
        logger.info('c3p_camara_get_api:camara_qod_details :: camara_nel_id: %s', camara_nel_id)

        if not c3p_camara_api.verify_del_id(nel_id):
            sql = "Select rfo_apibody from c3p_rf_orders where rfo_nel_id = %s"
        else:
            sql = "Select rfo_apibody from c3p_rf_orders where rfo_url_param_id = %s"

        mycursor.execute(sql, (camara_nel_id,))
        data_val = mycursor.fetchone()
        logger.info('c3p_camara_get_api:camara_qod_details :: data: %s', data_val)
        if not data_val:
            qod_details = {"code": "INVALID_ARGUMENT", "status": 400, "message": "Invalid Id"}
        else:
            data = json.loads(data_val[0])

            if 'qos' in data:
                qod_details = data

            if 'dscp' in data:
                dscp_val = data["dscp"]
                logger.info("dscp_val- %s", dscp_val)

                sql = "Select pp_paramter, pp_p_value FROM c3p_naas_m_profile_parameter where pr_id in (SELECT pr_id FROM c3p_naas_m_profile where pr_name = %s)"
                mycursor.execute(sql, (dscp_val,))
                para_data = mycursor.fetchall()

                for para_val in para_data:
                    data[para_val[0].capitalize()] = para_val[1].capitalize()

                logger.info("data- %s", data)
                qod_details = data

    except Exception as err:
        logger.error("c3p_camara_get_api:camara_qod_details :: Exception : %s", err)

    finally:
        return qod_details

#
# def camara_qod_homedvc_details(nel_id):
#     mydb = Connections.create_connection()
#     try:
#         mycursor = mydb.cursor(buffered=True)
#         camara_nel_id = str(nel_id)
#         logger.info('c3p_camara_get_api:camara_qod_details :: camara_nel_id: %s', camara_nel_id)
#
#         if not c3p_camara_api.verify_del_id(nel_id):
#             sql = "Select rfo_apibody from c3p_rf_orders where rfo_nel_id ='{}'".format(camara_nel_id)
#         else:
#             sql = "Select rfo_apibody from c3p_rf_orders where rfo_url_param_id ='{}'".format(camara_nel_id)
#
#             mycursor.execute(sql)
#             data = mycursor.fetchone()
#             logger.info('c3p_camara_get_api:camara_qod_details :: data: %s', data)
#
#         if not data:
#             qod_details = {"code": "INVALID_ARGUMENT", "status": 400, "message": "Invalid Id"}
#         else:
#             data = json.loads(data[0])
#             logger.info("data- %s", data)
#             dscp_val = data["dscp"]
#             logger.info("dscp_val- %s", dscp_val)
#
#             sql = "Select pp_paramter, pp_p_value FROM c3p_naas_m_profile_parameter where pr_id in (SELECT pr_id FROM c3p_naas_m_profile where pr_name = '{}')".format(
#                 dscp_val)
#             mycursor.execute(sql)
#             para_data = mycursor.fetchall()
#             for para_val in para_data:
#                 data[para_val[0].capitalize()] = para_val[1].capitalize()
#
#             logger.info("data- %s", data)
#             qod_details = data
#
#     except Exception as err:
#         logger.error("c3p_camara_get_api:camara_qod_details :: Exception : %s", err)
#
#     finally:
#         return qod_details