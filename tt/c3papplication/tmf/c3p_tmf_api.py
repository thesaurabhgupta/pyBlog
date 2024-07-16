from requests.auth import HTTPBasicAuth
import requests
import random
import string
from flask import request, jsonify
from flask_httpauth import HTTPBasicAuth
import datetime
from markupsafe import escape
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
from c3papplication.tmf import c3p_tmf_api2 as tmf2
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


@auth.verify_password
def verify_password(username, password):
    if username in users and \
            check_password_hash(users.get(username), password):
        return username, status.HTTP_202_ACCEPTED
    else:
        return "NOT", status.HTTP_401_UNAUTHORIZED


def datatodb(id):
    logger.debug('datatodb - id :: %s', id)
    global depth
    depth = 0
    # Value Computations begin
    # print(request.environ)
    global rfo_id, resource_key, resource_id
    resource_id = ''
    resource_key = ""
    rhref = ''
    try:
        logger.debug('datatodb - request :: %s', request)
        rfo_id = tmf2.compute_id(id, request.environ['REQUEST_METHOD'])
        logger.debug('datatodb - headers :: %s', request.headers)

        # logger.debug('datatodb - SERVER_NAME :: %s', request.headers['username'])

        rfo_apioperation = request.environ['REQUEST_METHOD']
        rfo_apiurl = request.environ['PATH_INFO']
        logger.debug('datatodb - rfo_apioperation :: %s', request.environ['REQUEST_METHOD'])
        logger.debug('datatodb - rfo_apiurl :: %s', request.environ['PATH_INFO'])
        global rfo_url_param_id
        if (id != None):
            rfo_url_param_id = id
        else:
            rfo_url_param_id = request.args.get('id')
        logger.debug('datatodb - rfo_url_param_id :: %s', rfo_url_param_id)
        if 'username' in request.headers:
            rfo_sourcesystem = str(request.headers['username'])
        else:
            rfo_sourcesystem = str(request.environ['SERVER_NAME'])
        logger.debug('datatodb - rfo_sourcesystem :: %s', rfo_sourcesystem)
        rfo_apiauth_status = status.HTTP_201_CREATED
        rfo_apibody = {
            'rfo_apioperation': rfo_apioperation
        }
        rfo_status = ''
        rfo_url_param_filters = ''
        if (rfo_apioperation == 'DELETE'):
            rfo_status = 'Accepted'
        else:
            rfo_url_param_filters = request.args.get('filter')
            rfo_apibody = request.json
            if (len(rfo_apibody) != 0):
                rfo_status = 'Accepted'
            else:
                rfo_status = 'Bad Request'
        rfo_created_date = datetime.datetime.now()
        rfo_updated_by = 'system'
        rfo_updated_date = datetime.datetime.now()
        mydb = Connections.create_connection()
        try:
            mycursor = mydb.cursor(buffered=True)
            sql = "INSERT INTO c3p_rf_orders(rfo_id,rfo_apibody,rfo_apioperation,rfo_apiurl,rfo_url_param_id,rfo_url_param_filters,rfo_sourcesystem,rfo_apiauth_status,rfo_status,rfo_created_date,rfo_updated_by,rfo_updated_date) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
            val = (
            rfo_id, json.dumps(rfo_apibody), rfo_apioperation, rfo_apiurl, rfo_url_param_id, rfo_url_param_filters,
            rfo_sourcesystem, rfo_apiauth_status, rfo_status, rfo_created_date, rfo_updated_by, rfo_updated_date)
            mycursor.execute(sql, val)
            mydb.commit()
        except Exception as err:
            logger.error("Exception in datatodb: %s", err)
        finally:
            mydb.close
        # Body parsing logic starts from here
        # print(json.loads(rfo_apibody).keys())
        # call http://localhost:8080/engine-rest/process-definition/key/decompWorkflow/start
        url = configs.get("Camunda_Engine") + configs.get("Decompose_Workflow")
        inp = {}
        inp['businessKey'] = rfo_id
        inp['variables'] = {"version": {"value": "1.0"}}
        data_json = json.dumps(inp)
        newHeaders = {"Content-type": "application/json",
                      "Accept": "application/json"}

        f = requests.post(url, data=data_json, headers=newHeaders)
        #logger.debug('datatodb - Response :: %s', f.json())

        rhref = configs.get("Python_Application") + \
                '/c3p-p-core/api/ResourceFunction/v4/monitor/?id=' + rfo_id

    except Exception as err:
        global description
        description = str(err)
        logger.error("Exception in main block of datatodb: %s", err)
    return jsonify({"content": rfo_apibody, "href": rhref}), status.HTTP_202_ACCEPTED

def decompose():
    global depth, rfo_url_param_id, rfo_id, resource_key, resource_id
    depth = 0
    badflow = 0  # initializing
    so_num = request.json['SO_number']
    print("so_num ", so_num)

    mydb = Connections.create_connection()
    try:
        mycursor = mydb.cursor(buffered=True)

        rfo_id = so_num

        if rfo_id[0:2] == "SD":
            logger.debug('decompose - rfo id starts with SD :: %s', rfo_id)
            mycursor.execute(
                "SELECT dis_row_id FROM c3p_t_discovery_dashboard  where dis_dash_id=%s", (so_num,))
            myresult = mycursor.fetchone()
            dis_row_id = myresult[0]
            logger.debug('decompose - dis_row_id :: %s', dis_row_id)
            sql = "INSERT INTO c3p_rfo_decomposed(od_rfo_id,od_param_id,od_seq,od_rf_taskname,od_req_resource_id,od_request_id,od_requeststatus,od_created_by,od_created_date,od_updated_by,od_updated_date) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
            val = (so_num, '', '7', 'discovery', '', dis_row_id, 'queued',
                   'system', datetime.datetime.now(), 'system', datetime.datetime.now())
            mycursor.execute(sql, val)
            mydb.commit()
            badflow = 6
        elif rfo_id[0:2] == "SP":
            logger.debug('decompose - rfo id starts with SP :: %s', rfo_id)
            mycursor.execute(
                "SELECT qt_row_id FROM c3p_t_qt_dashboard  where qt_id=%s", (so_num,))
            myresult = mycursor.fetchone()
            qt_row_id = myresult[0]
            logger.debug('decompose - qt_row_id :: %s', qt_row_id)
            sql = "INSERT INTO c3p_rfo_decomposed(od_rfo_id,od_param_id,od_seq,od_rf_taskname,od_req_resource_id,od_request_id,od_requeststatus,od_created_by,od_created_date,od_updated_by,od_updated_date) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
            val = (so_num, '', '4', 'ping', '', qt_row_id, 'queued',
                   'system', datetime.datetime.now(), 'system', datetime.datetime.now())
            mycursor.execute(sql, val)
            mydb.commit()
            badflow = 6
        else:
            mycursor.execute(
                "SELECT rfo_apioperation,rfo_apibody FROM c3p_rf_orders where rfo_id=%s", (so_num,))
            logger.debug("decompose - SQQ:: %s",
                         "SELECT rfo_apioperation,rfo_apibody FROM c3p_rf_orders where rfo_id='" + so_num + "'")
            myresult = mycursor.fetchall()
            result = []
            for x in myresult:
                for t in x:
                    result.append(t)
            logger.debug("decompose - Result is :: %s", result)
            rfo_apibody = result[1]
            rfo_apimethod = result[0]
            logger.debug("decompose - API-METHOD here is :: %s", rfo_apimethod)
            # Commented for issue resolution, need to veryfy what it is failing 07-Mar-2021 @ Sangita
            # rel = BuildResourceRelationship(so_num) #Resource Rel entry
            #
            # print("RES-REL_ENTRY:::",rel)
            mycursor.execute("SELECT rfo_url_param_id FROM c3p_rf_orders where rfo_id=%s", (so_num,))
            myresult = mycursor.fetchone()
            if (myresult[0] != None):
                rfo_url_param_id = ''.join(myresult)
            badflow = 0
            # logic for GCP compute begins
            if rfo_apimethod == 'POST':
                rfo_apibody2 = json.loads(rfo_apibody)
                logger.debug("decompose - rfo_apibody2 :: %s", rfo_apibody2)
                # Code for backup . test & diagnostics
                if rfo_apibody2.get('requestType') != None:
                    if ('Test' == rfo_apibody2.get('requestType') or 'Audit' == rfo_apibody2.get('requestType')):
                        mycursorValue = mydb.cursor(buffered=True)
                        mycursorValue.execute("SELECT d_id FROM c3p_deviceinfo where d_hostname=%s and d_mgmtip=%s", (rfo_apibody2.get('hostname'),rfo_apibody2.get('managementIp')))
                        deviceResult = mycursorValue.fetchone()
                        # need to check this line
                        logger.debug(
                            "decompose - if - deviceResult[0] :: %s", deviceResult[0])
                        dummy_sr = ''.join(random.choices(
                            string.ascii_uppercase + string.digits, k=10)) + str(datetime.datetime.now())
                        sql = "INSERT INTO c3p_rfo_decomposed(od_rfo_id,od_seq,od_rf_taskname,od_req_resource_id,od_request_id,od_requeststatus,od_created_by,od_created_date,od_updated_by,od_updated_date) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
                        val = (
                        so_num, 100, 'test', deviceResult[0], dummy_sr, 'queued', 'system', datetime.datetime.now(
                        ), 'system', datetime.datetime.now())
                        mycursor.execute(sql, val)
                        mydb.commit()
                        badflow = 3
                    elif 'backup' == rfo_apibody2.get('requestType'):
                        mycursorValue = mydb.cursor(buffered=True)
                        mycursorValue.execute("SELECT d_id FROM c3p_deviceinfo where d_hostname=%s and d_mgmtip=%s", (rfo_apibody2.get('hostname'),rfo_apibody2.get('managementIp')))
                        deviceResult = mycursorValue.fetchone()
                        logger.debug(
                            "decompose - else - deviceResult[0] :: %s", deviceResult[0])
                        dummy_sr = ''.join(random.choices(
                            string.ascii_uppercase + string.digits, k=10)) + str(datetime.datetime.now())
                        sql = "INSERT INTO c3p_rfo_decomposed(od_rfo_id,od_seq,od_rf_taskname,od_req_resource_id,od_request_id,od_requeststatus,od_created_by,od_created_date,od_updated_by,od_updated_date) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
                        val = (
                        so_num, 100, 'backup', deviceResult[0], dummy_sr, 'queued', 'system', datetime.datetime.now(
                        ), 'system', datetime.datetime.now())
                        mycursor.execute(sql, val)
                        mydb.commit()
                        badflow = 4
                elif so_num[0:2] == "SR":
                    if rfo_apibody2['id'][0:10] == "INV-NETOPS":
                        logger.debug("decompose - enter values in rfo_decomposed inv :: ")
                        sql = "INSERT INTO c3p_rfo_decomposed(od_rfo_id,od_param_id,od_seq,od_rf_taskname,od_req_resource_id,od_request_id,od_requeststatus,od_created_by,od_created_date,od_updated_by,od_updated_date) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
                        val = (so_num, rfo_url_param_id, '2', 'inventory', rfo_apibody2['id'], "", 'queued', 'system',
                               datetime.datetime.now(), 'system', datetime.datetime.now())
                        mycursor.execute(sql, val)
                        mydb.commit()
                        logger.debug("decompose - sql INSERT INTO c3p_rfo_decomposed table :: %s", sql)
                        logger.debug("decompose - od_request_id :: %s", rfo_apibody2['id'])
                        badflow = 2
                    else:
                        sql = "select count(*) from c3p_deviceinfo where d_id = %s"
                        logger.debug("decompose - sql SR here :: %s", sql)
                        mycursor.execute(sql, (rfo_apibody2['id'],))
                        countres = mycursor.fetchone()
                        count_of_rows = countres[0]
                        logger.debug("decompose -  count_of_rows :: %s", count_of_rows)
                        if count_of_rows == 0:
                            logger.debug("RES-CHARS length is::", len(rfo_apibody2['resourceCharacteristic']))
                            if len(rfo_apibody2['resourceCharacteristic']) < 5:
                                badflow = 1
                            else:  # enter values in rfo_decomposed
                                logger.debug("decompose - enter values in rfo_decomposed else :: ")
                                sql = "INSERT INTO c3p_rfo_decomposed(od_rfo_id,od_param_id,od_seq,od_rf_taskname,od_req_resource_id,od_request_id,od_requeststatus,od_created_by,od_created_date,od_updated_by,od_updated_date) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
                                val = (so_num, rfo_url_param_id, '2', 'instantiation', rfo_apibody2['id'], "", 'queued',
                                       'system', datetime.datetime.now(), 'system', datetime.datetime.now())
                                mycursor.execute(sql, val)
                                mydb.commit()
                                logger.debug("decompose - sql INSERT INTO c3p_rfo_decomposed table :: %s", sql)
                                logger.debug("decompose - od_request_id :: %s", rfo_apibody2['id'])
                                badflow = 2
                    badflow = 5
                else:
                    logger.debug("decompose - resourceRelationship else :: ")

                    for res_out in rfo_apibody2['resourceRelationship']:
                        for res in res_out.keys():
                            logger.debug("decompose - resource :: %s", res)

                            if res == 'resource':
                                mycursor.execute(
                                    "SELECT rfo_sourcesystem FROM c3p_rf_orders where rfo_id=%s", (so_num,))
                                rf_srcsystm = mycursor.fetchone()
                                logger.debug("tmf:c3p_tmf_get_api::decompose - rf_srcsystm - %s", rf_srcsystm)

                                if rf_srcsystm[0] == 'CEBMCIN1':
                                    sql = "select count(*) from c3p_deviceinfo where d_ref_device_id = %s"
                                    logger.debug("decompose - sql here :: %s", sql)
                                    mycursor.execute(sql, (res_out[res]['id'],))
                                    countres = mycursor.fetchone()
                                    count_of_rows = countres[0]
                                    # print(mycursor.fetchall())
                                    logger.debug("tmf:c3p_tmf_get_api::decompose - no. of records - %s", count_of_rows)

                                    if count_of_rows == 0:
                                        # print(mycursor.fetchall())
                                        # if not mycursor.fetchall()  :
                                        # check 5 tags and supply 400 when something is missing with the detail
                                        logger.debug(
                                            "decompose - RES-CHARS length is:: %s",
                                            len(res_out[res]['resourceCharacteristic']))
                                        if len(res_out[res]['resourceCharacteristic']) < 5:
                                            badflow = 1
                                        else:  # enter values in rfo_decomposed
                                            sql = "INSERT INTO c3p_rfo_decomposed(od_rfo_id,od_param_id,od_seq,od_rf_taskname,od_req_resource_id,od_request_id,od_requeststatus,od_created_by,od_created_date,od_updated_by,od_updated_date) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
                                            val = (
                                                so_num, rfo_url_param_id, '2', 'instantiation', res_out[res]['id'], "",
                                                'queued', 'system', datetime.datetime.now(
                                                ), 'system', datetime.datetime.now())
                                            mycursor.execute(sql, val)
                                            mydb.commit()
                                            badflow = 2
                                            logger.debug("decompose - od_request_id :: %s", res_out[res]['id'])

                                    else:
                                        raise Exception("This resource ID already exists")

                                else:
                                    sql = "select count(*) from c3p_deviceinfo where d_id = %s"
                                    logger.debug("decompose - sql here :: %s", sql)
                                    mycursor.execute(sql, (res_out[res]['id'],))
                                    countres = mycursor.fetchone()
                                    count_of_rows = countres[0]
                                    # print(mycursor.fetchall())
                                    if count_of_rows == 0:
                                        # print(mycursor.fetchall())
                                        # if not mycursor.fetchall()  :
                                        # check 5 tags and supply 400 when something is missing with the detail
                                        logger.debug(
                                            "decompose - RES-CHARS length is:: %s",
                                            len(res_out[res]['resourceCharacteristic']))
                                        if len(res_out[res]['resourceCharacteristic']) < 5:
                                            badflow = 1
                                        else:  # enter values in rfo_decomposed
                                            sql = "INSERT INTO c3p_rfo_decomposed(od_rfo_id,od_param_id,od_seq,od_rf_taskname,od_req_resource_id,od_request_id,od_requeststatus,od_created_by,od_created_date,od_updated_by,od_updated_date) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
                                            val = (
                                            so_num, rfo_url_param_id, '2', 'instantiation', res_out[res]['id'], "",
                                            'queued', 'system', datetime.datetime.now(
                                            ), 'system', datetime.datetime.now())
                                            mycursor.execute(sql, val)
                                            mydb.commit()
                                            badflow = 2
                                            logger.debug("decompose - od_request_id :: %s", res_out[res]['id'])

                    # sql = "INSERT INTO c3p_rfo_decomposed(od_rfo_id,od_param_id,od_seq,od_rf_taskname,od_req_resource_id,od_request_id,od_requeststatus,od_created_by,od_created_date,od_updated_by,od_updated_date) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
                    # val =(so_num,'','7','discovery','',dis_row_id,'queued','system',datetime.datetime.now(),'system',datetime.datetime.now())
                    # mycursor.execute(sql, val)
                    # mydb.commit()
                    # --------remove start ------------
                    # rel = BuildResourceRelationship(so_num) #Resource Rel entry
                    # print("RES-REL_ENTRY:::",rel)
                    # mycursor.execute("SELECT rfo_url_param_id FROM c3p_rf_orders where rfo_id='"+so_num+"'")
                    # myresult = mycursor.fetchone()
                    # rfo_url_param_id=''.join(myresult)
                    # --------remove end ------------
                    # #body= json.loads(rfo_apibody)
                    body_dict = json.loads(rfo_apibody).keys()
                    for bd in body_dict:
                        if bd == "connectivity":
                            for cy in json.loads(rfo_apibody)[bd]:
                                logger.debug("decompose - Cy is :: %s", cy)
                                sql = "INSERT INTO c3p_connectivity(rf_id,cy_connectivity_id,cy_name,cy_description,cy_type,cy_basetype,cy_schemalocation) VALUES (%s,%s,%s,%s,%s,%s,%s)"
                                val = (rfo_url_param_id, cy['id'], cy['name'], cy['description'],
                                       cy['@type'], cy['@baseType'], cy['@schemaLocation'])
                                mycursor.execute(sql, val)
                                mydb.commit()
                                mycursor.execute(
                                    "SELECT cy_rowid FROM c3p_connectivity WHERE cy_rowid = (select last_insert_id())")
                                myresult = mycursor.fetchone()
                                cy_row_id = myresult[0]
                                logger.debug(
                                    "decompose - CY row id: %s", cy_row_id)
                                for cn in cy['connection']:
                                    sql = "INSERT INTO c3p_connections(cy_rowid,cy_connectivity_id,co_connection_name,co_association_type,co_status) VALUES (%s,%s,%s,%s,%s)"
                                    val = (
                                        str(cy_row_id), cn['id'], cn['name'], cn['associationType'], "")
                                    mycursor.execute(sql, val)
                                    mydb.commit()
                                    mycursor.execute(
                                        "SELECT co_rowid FROM c3p_connections WHERE co_rowid = (select last_insert_id())")
                                    myresult = mycursor.fetchone()
                                    co_row_id = myresult[0]
                                    for ce in cn['endpoint']:
                                        sql = "INSERT INTO c3p_endpoints(ep_name,device_id,port_id,ep_is_root,type,referredtype,ep_schemalocation,basetype,href,rfo_id,request_id,cp_schemalocation) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
                                        logger.debug(
                                            "decompose - IS-ROOT:: %s", ce['isRoot'])
                                        # val = (ce['name'],ce['id'],ce['connectionPoint']['id'],str(ce['isRoot']),ce['@type'],ce['@referredType'],ce['@schemaLocation'],ce['@baseType'],ce['href'],rfo_id,'',ce['connectionPoint']['@schemaLocation'])
                                        ce_sl = (
                                            lambda: "", lambda: ce['@schemaLocation'])['@schemaLocation' in ce.keys()]()
                                        ce_ir = (lambda: "", lambda: ce['isRoot'])[
                                            'isRoot' in ce.keys()]()
                                        ce_tp = (
                                            lambda: "", lambda: ce['@type'])['@type' in ce.keys()]()
                                        ce_rt = (
                                            lambda: "", lambda: ce['@referredType'])['@referredType' in ce.keys()]()
                                        ce_bt = (
                                            lambda: "", lambda: ce['@baseType'])['@baseType' in ce.keys()]()
                                        ce_href = (lambda: "", lambda: ce['href'])[
                                            'href' in ce.keys()]()
                                        val = (ce['name'], ce['id'], ce['connectionPoint']['id'], str(
                                            ce_ir), ce_tp, ce_rt, ce_sl, ce_bt, ce_href, rfo_id, '',
                                               ce['connectionPoint']['@schemaLocation'])
                                        # val = (ce['name'],ce['id'],ce['connectionPoint']['id'],str(ce['isRoot']),ce['@type'],ce['@referredType'],ce['@schemaLocation'],ce['@baseType'],ce['href'],rfo_id,'',ce['connectionPoint']['@schemaLocation'])                            mycursor.execute(sql, val)

                                        mycursor.execute(sql, val)
                                        mydb.commit()
                                    mycursor.execute(
                                        "SELECT ep_rowid FROM c3p_endpoints WHERE ep_rowid = (select last_insert_id())")
                                    myresult = mycursor.fetchone()
                                    ep_id_a = myresult[0]
                                    ep_id_z = ep_id_a - 1
                                    logger.debug(
                                        "decompose - RESULT:: %s", ep_id_a)
                                    logger.debug("decompose - update c3p_connections set co_endpoint_a = '" + str(
                                        ep_id_a) + "' and co_endpoint_z = '" + str(
                                        ep_id_z) + "' where cy_rowid='" + str(cy_row_id) + "'")
                                    mycursor.execute("update c3p_connections set co_endpoint_a = '" + str(
                                        ep_id_a) + "', co_endpoint_z = '" + str(
                                        ep_id_z) + "' where cy_rowid='" + str(cy_row_id) + "' and co_rowid='" + str(
                                        co_row_id) + "'")
                                    mydb.commit()

                    mycursor.execute("SELECT distinct(device_id) FROM c3p_endpoints where rfo_id=%s", (so_num,))
                    myresult = mycursor.fetchall()
                    result = []
                    for t in myresult:
                        for x in t:
                            result.append(x)
                    for rx in result:
                        dummy_sr = ''.join(random.choices(
                            string.ascii_uppercase + string.digits, k=10)) + str(datetime.datetime.now())
                        sql = "INSERT INTO c3p_rfo_decomposed(od_rfo_id,od_param_id,od_seq,od_rf_taskname,od_req_resource_id,od_request_id,od_requeststatus,od_created_by,od_created_date,od_updated_by,od_updated_date) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
                        val = (so_num, rfo_url_param_id, '4', 'connection', rx, dummy_sr, 'queued',
                               'system', datetime.datetime.now(), 'system', datetime.datetime.now())
                        logger.debug("decompose - od_request_id :: %s", dummy_sr)
                        mycursor.execute(sql, val)
                        mydb.commit()
                    badflow = 5
            elif rfo_apimethod == 'DELETE':
                mycursorValue = mydb.cursor(buffered=True)
                if rfo_id[0:2] == "SR":
                    mycursorValue.execute(
                        "SELECT d_id, d_hostname FROM c3p_deviceinfo WHERE d_id = %s", (rfo_url_param_id,))
                else:
                    mycursorValue.execute(
                        "SELECT resource_id, resource_name FROM c3p_resource_relationships WHERE rr_rf_id = %s", (rfo_url_param_id,))
                result = mycursorValue.fetchall()
                logger.debug("decompose - elif - DELETE resource_id and resource_name  :: %s", result)
                dummy_sr = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10)) + str(
                    datetime.datetime.now())
                hostnames = configs.get("Imp_hostname")
                for resource in result:
                    if resource[1] not in hostnames:
                        reqStatus = 'queued'
                    else:
                        reqStatus = 'Failure'
                    sql = "INSERT INTO c3p_rfo_decomposed(od_rfo_id,od_seq,od_rf_taskname,od_req_resource_id,od_request_id,od_requeststatus,od_created_by,od_created_date,od_updated_by,od_updated_date) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
                    val = (
                    so_num, 70, 'DeleteInstance', resource[0], dummy_sr, reqStatus, 'system', datetime.datetime.now(),
                    'system', datetime.datetime.now())
                    mycursor.execute(sql, val)
                    mydb.commit()
                    logger.debug("decompose - od_request_id :: %s", dummy_sr)
                badflow = 7
            # Call Java camunda api from here

            # badflow 0,1,2 -> activation(patch),1- gcp but bad ,2-gcp good, 3-backup 4- t&d/audit, 5-connectivity, 6-discovery
        if badflow == 0:
            if rfo_id[0:2] == "SR":
                depth = 1
                resource_key = "resource"
                mycursor.execute("SELECT distinct(to_tag_name), to_tag_id, to_key_level FROM c3p_task_orch WHERE to_key_level='R'")
            elif rfo_id[0:2] == "SO":
                mycursor.execute("SELECT distinct(to_tag_name), to_tag_id, to_key_level FROM c3p_task_orch WHERE to_key_level='RF'")
            myresult = mycursor.fetchall()

            # commented the below code for tmf_639 to work, as we are sending all the 3 values to checktag function, we don't need to iterate the result.
            '''
            for t in myresult:
                for x in t:
                    result.append(x)
            '''
            body_dict = json.loads(rfo_apibody).keys()
            for key in body_dict:
                # Tag Parsing Function here
                # print(json.loads(rfo_apibody)[key])
                # print(key)
                checkTag(myresult, key, json.loads(rfo_apibody)
                [key], rfo_url_param_id)

    except Exception as err:
        global description
        description = str(err)
        logger.error("Description in decompose: %s", description)
        logger.error("Exception in decompose: %s", err)
    finally:
        mydb.close

    if badflow == 1:
        return jsonify({"message": "Resource Characteristics is missing some value(s)"}), status.HTTP_400_BAD_REQUEST
    elif (badflow == 2 or badflow == 3 or badflow == 4 or badflow == 5 or badflow == 6 or badflow == 7):
        return jsonify({"SO_number": so_num, "workflow_status": True}), status.HTTP_200_OK
    else:
        return jsonify({"SO_number": so_num, "workflow_status": True}), status.HTTP_200_OK

def create_test_json(v_so_num, device_specs, row_id, param_feat, conn_flag, reso_id):
    data = {}
    result = []
    wflow = False
    mydb = Connections.create_connection()
    try:
        mycursor = mydb.cursor(buffered=True)
        for t in device_specs:
            for x in t:
                result.append(x)
        data["configGenerationMethod"] = "Test"
        data["apiCallType"] = "external"
        data["customer"] = result[9]
        data["region"] = result[10]
        data["siteName"] = result[11]
        data["hostname"] = result[8]
        global d_host, res_id
        d_host = result[8]
        data["model"] = result[7]
        data["os"] = result[0]
        data["osVersion"] = result[1]
        data["deviceType"] = result[4]
        data["deviceFamily"] = result[2]
        data["vendor"] = result[3]
        data["networkType"] = "PNF"
        data["vnfConfig"] = ""
        data["managementIp"] = result[6]
        data["userName"] = "admin"
        data["userRole"] = "admin"
        # data["requestType"]="Test"
        mycursor.execute("SELECT rfo_apibody FROM c3p_rf_orders where rfo_id=%s", (v_so_num,))
        myresult = mycursor.fetchone()
        rfo_apibody = ''.join(myresult)
        body = json.loads(rfo_apibody)
        data["requestType"] = body.get('requestType')
        data['certificationTests'] = body.get('certificationTests')
        json_data = json.dumps(data)
        mycursor.execute("UPDATE c3p_rfo_decomposed set od_request_json = %s where od_rowid = %s", (json_data, row_id,))
        logger.debug("create_test_json - record updated. %s", mycursor.rowcount)
        mydb.commit()
        logger.debug('create_test_json - json_data :: %s', json_data)
        newHeaders = {"Content-type": "application/json",
                      "Accept": "application/json"}
        url = configs.get("C3P_Application") + \
              configs.get("Config_Create")

        req = requests.post(url, data=json_data, headers=newHeaders)
        # print ('req ::', req)
        resp = req.json()
        resp_json = resp
        if len(resp) == 0:
            wflow = True
        logger.debug('create_test_json - req JSON :: %s', resp)
        mycursor.execute("UPDATE c3p_rfo_decomposed set od_requeststatus = %s,od_request_id = %s where od_rowid = %s", (resp_json['output'], resp_json['requestId'], row_id,))
        mydb.commit()
    except Exception as err:
        global description
        description = str(err)
        logger.error("Exception in create_test_json: %s", err)
    finally:
        mydb.close
    return wflow

def create_json(v_so_num, device_specs, row_id, param_feat, conn_flag, reso_id):
    data = {}
    wflow = False
    mydb = Connections.create_connection()
    mycursor = mydb.cursor(buffered=True)
    mycursor.execute("SELECT d_role FROM c3p_deviceinfo WHERE d_id = %s", (reso_id,))
    deviceRole = mycursor.fetchone()
    try:
        mycursor = mydb.cursor(buffered=True)
        result = []
        feat_reps = []
        non_temp_attrs = {}
        rep_attrs = {}
        dyn_attr = []
        for t in device_specs:
            for x in t:
                result.append(x)
        logger.debug("create_json -result  device_specs :: %s", result)
        data["apiCallType"] = "external"
        data["customer"] = result[9]
        data["region"] = result[10]
        data["siteName"] = result[11]
        data["hostname"] = result[8]
        global d_host, res_id
        d_host = result[8]
        data["model"] = result[7]
        data["os"] = result[0]
        data["osVersion"] = result[1]
        data["deviceType"] = result[4]
        data["deviceFamily"] = result[2]
        data["vendor"] = result[3]
        data["networkType"] = "PNF"
        data["vnfConfig"] = ""
        data["managementIp"] = result[6]
        data["userName"] = "admin"
        data["userRole"] = "admin"
        isFile = False
        isTemplate = False
        attrs = {}
        sf = ""
        sff = []
        config_gen = []
        rep_array = []
        if param_feat == 'connection':
            data["requestType"] = "Config MACD"
            isFile = True
            rr = ""
            rand_str2 = ''.join(random.choices(
                string.ascii_lowercase + string.digits, k=8)) + str(datetime.datetime.now())
            # sff ="WAN Interface"
            dyn_attr = []
            # run 4 queries to find the best match of feat_id
            vals = [result[3], result[2], result[0], result[1]]
            i = 3
            stop = 0
            # flag = 0
            while stop == 0:
                sql = "SELECT * FROM c3p_m_features where f_category = 'WAN' and f_vendor = %s and f_family = %s and f_os = %s and f_osversion = %s"
                logger.debug("create_json - sql :: %s", sql)
                # c3p_template_master_command_list
                mycursor.execute(sql, (vals[0],vals[1],vals[2],vals[3],))
                myresult = mycursor.fetchall()
                logger.debug("create_json - Result is:: %s", myresult)
                if len(myresult) > 0:
                    stop = 1
                else:
                    vals[i] = 'ALL'
                    i = i - 1
            result = []
            for t in myresult:
                for x in t:
                    result.append(x)
            # sql = f"select command_value from c3p_template_master_command_list where master_f_id='{result[1]}'"
            # logger.debug("create_json - THE SQL:: %s", sql)
            f_id = result[1]

            # x = datetime.datetime.now()
            # rand_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=5))

            # search endpoint table for device_id and rfo_id and run service now api that many times you find entries in that table
            sql = "select ep_rowid, cp_schemalocation from c3p_endpoints where rfo_id=%s and device_id=%s"
            logger.debug("create_json - THE SQL:: %s", sql)
            # f_id=result[1]
            mycursor.execute(sql, (v_so_num, reso_id,))
            myresult = mycursor.fetchall()
            cpresult = []
            for t in myresult:
                for x in t:
                    cpresult.append(x)
            logger.debug("create_json - THE OTIPUTTT:: %s", mycursor.rowcount)
            logger.debug("create_json - schemaLocation is :: %s", cpresult[1])
            # call service now api here for dyn-attribs in JSON

            newHeaders = {"Content-type": "application/json",
                          "Accept": "application/json"}
            loop = mycursor.rowcount
            # feat = ""
            while loop > 0:
                # url ='https://techmahindramspsvsdemo3.service-now.com/api/now/table/u_connection_point?u_connection_id=32kl'
                url = cpresult[1]
                req = requests.get(url, headers=newHeaders,
                                   auth=('webUser', 'Admin*123'))
                resp = req.json()
                logger.debug('create_json - req JSON :: %s', resp)
                conn_attr = json.loads(
                    resp['result'][0]['u_connection_attributes'])
                logger.debug("create_json - Connection Attr:: %s", conn_attr)
                for co in conn_attr.keys():
                    # sql = "INSERT INTO c3p_resourcecharacteristicshistory(device_id,rc_device_hostname,so_request_id,rc_request_status,rfo_id,rc_action_performed,rc_feature_id,rc_characteristic_id,rc_name,rc_value,rc_valuetype) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
                    # val = (reso_id,d_host,rand_str2,"",v_so_num,"ADD",f_id,reso_id,co,conn_attr[co],"")
                    # mycursor.execute(sql, val)
                    # mydb.commit()
                    # dynamic attributess logic as per new JSON
                    sql = "SELECT c_id FROM c3p_m_characteristics where c_name = %s and c_f_id = %s"
                    logger.debug("create_json - SQL is :: %s", sql)
                    mycursor.execute(sql, (co,f_id,))
                    result = mycursor.fetchone()
                    logger.debug("create_json - Fetch One result :: %s", result[0])
                    attrs['name'] = result[0]
                    attrs['type'] = "Non-Template"
                    attrs['label'] = co
                    attrs['value'] = conn_attr[co]
                    attrs['templateid'] = ""
                    # attrs[co] = conn_attr[co]
                    feat_reps.append(attrs)
                    if loop > 1:
                        # replication logic
                        sql = "SELECT distinct c3p_m_features.f_id,c3p_m_features.f_name " \
                                "FROM c3p_m_characteristics INNER JOIN c3p_m_features " \
                                "ON c3p_m_features.f_id  in (select distinct(c_f_id) from c3p_m_characteristics where c_id = %s)"
                        mycursor.execute(sql, (attrs['name'],))
                        myresult = mycursor.fetchall()
                        result = []
                        logger.debug("create_json - Feat_reps is :: %s", feat_reps)
                        for t in myresult:
                            for x in t:
                                result.append(x)
                        rep_flag = 0
                        feat = result[0]
                        for rep_a in rep_array:
                            if result[0] == rep_a['featureId']:
                                logger.debug("Item at connection json")
                                rep_a['featureAttribDetails'].append(attrs)
                                rep_attrs = {}
                                rep_flag = 1
                        if rep_flag == 0:
                            rep_attrs["featureId"] = result[0]
                            rep_attrs["featureName"] = result[1]
                            rep_attrs["templateid"] = ""
                            rep_attrs["featureAttribDetails"] = feat_reps
                            rep_array.append(rep_attrs)
                            rep_attrs = {}
                        feat_reps = []
                        logger.debug("create_json - rep_array is :: %s", rep_array)
                    else:
                        dyn_attr.append(attrs)
                    attrs = {}
                loop = loop - 1

            sql = "SELECT f_name,f_replicationind FROM c3p_m_features where f_id= %s"
            logger.debug("create_json - SQL is :: %s", sql)
            mycursor.execute(sql, (f_id,))
            myres = mycursor.fetchall()
            result = []
            for x in myres:
                for t in x:
                    result.append(t)
            non_temp_attrs = {}
            non_temp_attrs["fId"] = f_id
            non_temp_attrs["fName"] = result[0]
            non_temp_attrs["fReplicationFlag"] = (
                (lambda: False, lambda: True)[int(result[1]) == 1]())
            sff.append(non_temp_attrs)
        else:
            logger.debug("create_json: deviceRole:: %s", deviceRole)
            if deviceRole[0] == "eNB" or deviceRole[0] == "gNB" or deviceRole[0] == "CT":
                data["requestType"] = "Config"
            else:
                data["requestType"] = "Config MACD"
            mycursor.execute(
                "SELECT rfo_apibody FROM c3p_rf_orders where rfo_id=%s", (v_so_num,))
            myresult = mycursor.fetchone()
            rfo_apibody = ''.join(myresult)
            body = json.loads(rfo_apibody)
            data['certificationTests'] = body.get('certificationTests')  #ADD for Demo perpose if removed tests is not added
            i = 0
            count = 0
            # flag = 0
            # filename = ""
            rr = []
            sf = []
            config_gen = []
            sff = []
            rand_str2 = ''.join(random.choices(
                string.ascii_lowercase + string.digits, k=8)) + str(datetime.datetime.now())
            # fpath = "jboss/C3Pconfig/ConfigurationFiles/"

            sf_temp = "("
            if v_so_num[0:2] == "SR":
                for bres2 in body:
                    if bres2 == 'activationFeature':
                        for bres3 in body[bres2]:  # for bres3 in bod[bres][bres2] :
                            if not bres3['isBundle']:
                                act_feat_id = bres3['id'].split(":::")
                                mycursor.execute(
                                    "SELECT f_name,f_replicationind FROM c3p_m_features where f_id = %s", (act_feat_id[2],))
                                logger.debug("create_json - Feature ID:: %s", act_feat_id[2])
                                myresult = mycursor.fetchone()
                                result = []
                                for t in myresult:
                                    result.append(t)
                                count = count + 1
                                isFile = True
                                data["templateId"] = ""
                                fc = 0
                                # Replication Logic
                                for bres4 in bres3['featureCharacteristic']:
                                    fc = fc + 1
                                    sf_temp = sf_temp + "'" + bres4['id'] + "',"
                                    attrs["label"] = bres4['name']
                                    attrs["name"] = bres4['id']
                                    attrs["value"] = bres4['value']
                                    attrs["type"] = "Non-Template"
                                    attrs["templateid"] = ""
                                    if int(act_feat_id[1]) == 1:
                                        dyn_attr.append(attrs)
                                        if fc == 1:
                                            non_temp_attrs["fId"] = act_feat_id[2]
                                            non_temp_attrs["fName"] = result[0]
                                            non_temp_attrs["fReplicationFlag"] = (
                                                (lambda: False, lambda: True)[int(result[1]) == 1]())
                                            sff.append(non_temp_attrs)
                                            non_temp_attrs = {}
                                        else:
                                            feat_reps.append(attrs)
                                        attrs = {}
                                if int(act_feat_id[1]) > 1:
                                    rep_attrs["featureId"] = act_feat_id[2]
                                    rep_attrs["featureName"] = bres3['name']
                                    rep_attrs["templateid"] = ""
                                    rep_attrs["featureAttribDetails"] = feat_reps
                                    rep_array.append(rep_attrs)
                                    rep_attrs = {}
                                    feat_reps = []
                                logger.debug("create_json - FEAT_REPS:: %s", feat_reps)
                                rep_attrs = {}
                                # Generate config file logic starts here
                            else:
                                isTemplate = True
                                rr.append(bres3['id'])
                                for bres4 in bres3['featureCharacteristic']:
                                    feat_char_id = bres4['id'].split(":::")
                                    mycursor.execute( "Select m_characteristic_id from t_attrib_m_attribute where id = %s", (feat_char_id[2],))
                                    logger.debug("create_json - SQL:: %s",
                                                 "Select m_characteristic_id from t_attrib_m_attribute where id = '" +
                                                 feat_char_id[2] + "'")
                                    myresult = mycursor.fetchone()
                                    logger.debug("create_json - and result:: %s", myresult)
                                    feat_char_id[2] = ''.join(myresult)
                                    if int(feat_char_id[1]) == 1:
                                        sf_temp = sf_temp + "'" + feat_char_id[2] + "',"
                                        attrs["label"] = bres4['name']
                                        attrs["name"] = feat_char_id[2]
                                        attrs["value"] = bres4['value']
                                        attrs["type"] = "Template"
                                        attrs["templateid"] = bres3['id']
                                        dyn_attr.append(attrs)
                                        attrs = {}
                                    else:
                                        attrs["label"] = bres4['name']
                                        attrs["name"] = feat_char_id[2]
                                        attrs["value"] = bres4['value']
                                        attrs["type"] = "Template"
                                        attrs["templateid"] = bres3['id']
                                        feat_reps.append(attrs)
                                        attrs = {}
                                        # queries for fetching feature id and feature name will be here
                                        sql = "SELECT distinct c3p_m_features.f_id,c3p_m_features.f_name " \
                                                "FROM c3p_m_characteristics INNER JOIN c3p_m_features " \
                                                "ON c3p_m_features.f_id  in (select distinct(c_f_id) from c3p_m_characteristics where c_id = %s)"
                                        mycursor.execute(sql, (feat_char_id[2], ))
                                        myresult = mycursor.fetchall()
                                        result = []
                                        for t in myresult:
                                            for x in t:
                                                result.append(x)
                                if int(feat_char_id[1]) > 1:
                                    rep_attrs["featureId"] = result[0]
                                    rep_attrs["featureName"] = result[1]
                                    rep_attrs["templateid"] = bres3['id']
                                    rep_attrs["featureAttribDetails"] = feat_reps
                                    rep_array.append(rep_attrs)
                                    feat_reps = []
                                    rep_attrs = {}
                                sf_temp2 = list(sf_temp)
                                sf_temp2[len(sf_temp2) - 1] = ')'
                                sf_temp3 = "".join(sf_temp2)
                                mycursor.execute("Select distinct(feature_id) from t_attrib_m_attribute where m_characteristic_id in " + sf_temp3 + " and lower(template_id) = '" +
                                             bres3['id'].lower() + "'")
                                logger.debug("create_json - SQL:: %s",
                                             "Select distinct(feature_id) from t_attrib_m_attribute where m_characteristic_id in " + sf_temp3 + " and lower(template_id) = '" +
                                             bres3['id'].lower() + "'")
                                myresult = mycursor.fetchall()
                                logger.debug("create_json - and result:: %s", myresult)
                                result = []
                                for t in myresult:
                                    for x in t:
                                        sf.append(bres3['id'] + ":::" + str(x))
            else:
                for bod in body['resourceRelationship']:
                    for bres in bod:
                        # print("INSIDE PARSER::"+bres)
                        if bres == 'resource':
                            for bres2 in bod[bres]:
                                res_id = bod[bres]['id']
                                if bres2 == 'activationFeature':
                                    for bres3 in bod[bres][bres2]:
                                        if not bres3['isBundle']:
                                            act_feat_id = bres3['id'].split(":::")
                                            mycursor.execute("SELECT f_name,f_replicationind FROM c3p_m_features where f_id = %s", (act_feat_id[2],))
                                            logger.debug(
                                                "create_json - Feature ID:: %s", act_feat_id[2])
                                            myresult = mycursor.fetchone()
                                            result = []
                                            for t in myresult:
                                                result.append(t)
                                            count = count + 1
                                            isFile = True
                                            data["templateId"] = ""
                                            fc = 0
                                            # Replication Logic
                                            for bres4 in bres3['featureCharacteristic']:
                                                fc = fc + 1
                                                sf_temp = sf_temp + "'" + bres4['id'] + "',"
                                                attrs["label"] = bres4['name']
                                                attrs["name"] = bres4['id']
                                                attrs["value"] = bres4['value']
                                                attrs["type"] = "Non-Template"
                                                attrs["templateid"] = ""
                                                if int(act_feat_id[1]) == 1:
                                                    dyn_attr.append(attrs)
                                                    if fc == 1:
                                                        non_temp_attrs["fId"] = act_feat_id[2]
                                                        non_temp_attrs["fName"] = result[0]
                                                        non_temp_attrs["fReplicationFlag"] = (
                                                            (lambda: False, lambda: True)[int(result[1]) == 1]())
                                                        sff.append(non_temp_attrs)
                                                        non_temp_attrs = {}
                                                else:
                                                    feat_reps.append(attrs)
                                                attrs = {}
                                            if int(act_feat_id[1]) > 1:
                                                rep_attrs["featureId"] = act_feat_id[2]
                                                rep_attrs["featureName"] = bres3['name']
                                                rep_attrs["templateid"] = ""
                                                rep_attrs["featureAttribDetails"] = feat_reps
                                                rep_array.append(rep_attrs)
                                                rep_attrs = {}
                                                feat_reps = []
                                            logger.debug(
                                                "create_json - FEAT_REPS:: %s", feat_reps)
                                            rep_attrs = {}
                                        # Generate config file logic starts here
                                        else:
                                            # isFile = True
                                            isTemplate = True
                                            rr.append(bres3['id'])
                                            for bres4 in bres3['featureCharacteristic']:
                                                feat_char_id = bres4['id'].split(":::")
                                                mycursor.execute("Select m_characteristic_id from t_attrib_m_attribute where id = %s", (feat_char_id[2],))
                                                logger.debug(
                                                    "create_json - SQL:: %s",
                                                    "Select m_characteristic_id from t_attrib_m_attribute where id = '" +
                                                    feat_char_id[2] + "'")
                                                myresult = mycursor.fetchone()
                                                logger.debug(
                                                    "create_json - and result:: %s", myresult)
                                                feat_char_id[2] = ''.join(myresult)
                                                if int(feat_char_id[1]) == 1:
                                                    sf_temp = sf_temp + "'" + \
                                                              feat_char_id[2] + "',"
                                                    attrs["label"] = bres4['name']
                                                    attrs["name"] = feat_char_id[2]
                                                    attrs["value"] = bres4['value']
                                                    attrs["type"] = "Template"
                                                    attrs["templateid"] = bres3['id']
                                                    dyn_attr.append(attrs)
                                                    attrs = {}
                                                else:
                                                    attrs["label"] = bres4['name']
                                                    attrs["name"] = feat_char_id[2]
                                                    attrs["value"] = bres4['value']
                                                    attrs["type"] = "Template"
                                                    attrs["templateid"] = bres3['id']
                                                    feat_reps.append(attrs)
                                                    attrs = {}
                                                    # queries for fetching feature id and feature name will be here
                                                    sql = "SELECT distinct c3p_m_features.f_id,c3p_m_features.f_name " \
                                                        "FROM c3p_m_characteristics INNER JOIN c3p_m_features " \
                                                        "ON c3p_m_features.f_id  in (select distinct(c_f_id) from c3p_m_characteristics where c_id = %s)"
                                                    mycursor.execute(sql, (feat_char_id[2],))
                                                    myresult = mycursor.fetchall()
                                                    result = []
                                                    for t in myresult:
                                                        for x in t:
                                                            result.append(x)
                                            if int(feat_char_id[1]) > 1:
                                                rep_attrs["featureId"] = result[0]
                                                rep_attrs["featureName"] = result[1]
                                                rep_attrs["templateid"] = bres3['id']
                                                rep_attrs["featureAttribDetails"] = feat_reps
                                                rep_array.append(rep_attrs)
                                                feat_reps = []
                                                rep_attrs = {}
                                            sf_temp2 = list(sf_temp)
                                            sf_temp2[len(sf_temp2) - 1] = ')'
                                            sf_temp3 = "".join(sf_temp2)
                                            mycursor.execute("Select distinct(feature_id) from t_attrib_m_attribute where m_characteristic_id in " + sf_temp3 + " and lower(template_id) = '" +
                                             bres3['id'].lower() + "'")
                                            logger.debug("create_json - SQL:: Select distinct(feature_id) from t_attrib_m_attribute where m_characteristic_id in " + sf_temp3 + " and lower(template_id) = '" +
                                             bres3['id'].lower() + "'")
                                            myresult = mycursor.fetchall()
                                            logger.debug(
                                                "create_json - and result:: %s", myresult)
                                            result = []
                                            for t in myresult:
                                                for x in t:
                                                    sf.append(bres3['id'] + ":::" + str(x))

        if isFile:
            config_gen.append('Non-Template')
            data["selectedFeatures"] = sff
            data["dynamicAttribs"] = dyn_attr
            data["replication"] = rep_array
        if isTemplate:
            config_gen.append('Template')

        data["configGenerationMethod"] = config_gen
        if not isFile:
            data["templateId"] = rr
            data["selectedFeatures"] = sf
            data["dynamicAttribs"] = dyn_attr
            data["replication"] = rep_array
        json_data = json.dumps(data)
        mycursor.execute("UPDATE c3p_rfo_decomposed set od_request_json = %s where od_rowid=%s", (json_data, row_id,))
        logger.debug("create_json - record updated. %s", mycursor.rowcount)
        mydb.commit()
        logger.debug('create_json - json_data ::%s', json_data)
        newHeaders = {"Content-type": "application/json",
                      "Accept": "application/json"}
        url = configs.get("C3P_Application") + \
              configs.get("Config_Create")

        req = requests.post(url, data=json_data, headers=newHeaders)
        # print ('req ::', req)
        resp = req.json()
        resp_json = resp
        if len(resp) == 0:
            wflow = True
        logger.debug('create_json - req JSON :: %s', resp)

        # if no response received from java send status True and update rfo_decomposed as failure
        mycursor.execute("update c3p_rfo_decomposed set od_requeststatus = %s,od_request_id = %s where od_rowid = %s", (resp_json['output'], resp_json['requestId'], row_id,))
        mydb.commit()
        if isFile:
            mycursor.execute("update c3p_resourcecharacteristicshistory set so_request_id = %s where so_request_id=%s", (resp['requestId'], rand_str2,))
            mydb.commit()
        if param_feat == "connection":
            mycursor.execute("update c3p_endpoints set request_id =%s where rfo_id=%s and device_id=%s", (resp['requestId'], v_so_num, reso_id,))
            mydb.commit()
    except Exception as err:
        logger.error("Exception in create_json: %s", err)
    finally:
        mydb.close
    return wflow

    # call C3P/ConfigurationManagement/create as Post
    # return request_id,request_version,status
'''{
    "output": "Submitted",
    "requestId": "SLGC-31D62BD",
    "version": 1.0
}'''

def checkTag(result, key, key_val, rfo_url_param_id):
    for val in result:
        if val[0] == key:
            performAction(key, key_val, val[2])
    return "SOMETHING"

def performAction(key, key_val, key_level):
    act = ""
    global depth, resource_key
    mydb = Connections.create_connection()
    try:
        mycursor = mydb.cursor(buffered=True)
        # print(depth)
        logger.debug("performAction - Key is --> %s", key)
        if type(key) is str:
            mycursor.execute(
                "SELECT to_action,to_is_parent_tag FROM c3p_task_orch where to_tag_name= %s", (key,))
            record = mycursor.fetchone()
            if depth > 0:
                # print("CAME HERE")
                # print("SELECT to_action,to_is_parent_tag FROM c3p.c3p_task_orch where to_tag_name='"+key+"' and to_is_parent_tag='N'")
                mycursor.execute(
                    "SELECT to_action,to_is_parent_tag FROM c3p_task_orch where to_tag_name like %s and to_is_parent_tag='N'", ('%' + key + '%',))
                record = mycursor.fetchone()
                if record is not None:
                    act = ''.join(record)
        if ((type(key_val) is dict) or (type(key_val) is list)):
            logger.debug("performAction - Type(key_val) %s", type(key_val))
            depth = depth + 1
            performActionJSON(key, key_val, key_level)
        else:
            logger.debug("performAction - Function - performAction key :: %s", key)
            # print("ACTION IS "+act)
            # print(act + "  "+str(key))
            # print ("KEY nd KEYVAL "+str(key) + "  "+str(key_val))
        if act == "DBUPDATEY":
            # print("UPDATE c3p_resource_function the rf_"+str(key)+" and its value "+str(key_val))
            colname = "rf_" + str(key)
            mycursor.execute("SHOW COLUMNS FROM c3p_resourcefunction like %s", (colname,))
            # print(mycursor.rowcount)
            if mycursor.rowcount == 1:
                # print ("UPDATE c3p.c3p_resourcefunction set "+colname+"='"+str(key_val)+"' where rf_id='"+rfo_url_param_id+"'")
                mycursor.execute("UPDATE c3p_resourcefunction set %s=%s where rf_id=%s", (colname, key_val, rfo_url_param_id,))
                mydb.commit()
        elif act == "DBUPDATEN" and resource_key == "resource":
            colname = "r_" + str(key)
            mycursor.execute("SHOW COLUMNS FROM c3p_deviceinfo_ext like %s", (colname,))
            # print(mycursor.rowcount)
            if mycursor.rowcount == 1:
                # print ("UPDATE c3p.c3p_deviceinfo_ext set "+colname+"='"+str(key_val)+"' where r_device_id='"+rfo_url_param_id+"'")
                mycursor.execute("UPDATE c3p_deviceinfo_ext set %s=%s where r_device_id=2", (colname,key_val,))
                mydb.commit()
    except Exception as err:
        logger.error("Exception in performAction: %s", err)
    finally:
        mydb.close
    return "SOME"

def performActionJSON(key, key_val, key_level):
    # print(str(key) + " is a JSON or list")
    global resource_key, resource_id, rfo_id, rfo_url_param_id
    mydb = Connections.create_connection()
    try:
        mycursor = mydb.cursor(buffered=True)
        if type(key_val) is dict:
            if str(key) == "resource":
                key_level = "R"
                if rfo_id[0:2] == "SR":
                    resource_id = rfo_url_param_id
                else:
                    #   print("THE resource id is ::"+str(key_val['id']))
                    resource_id = str(key_val['id'])
            resource_key = str(key)
            # colname = "rf_"+str(key)
            body_dict = key_val.keys()
            for keys in body_dict:
                performAction(keys, key_val[keys], key_level)

        else:
            logger.debug(str(key) + " is a List")
            act = ''
            mycursor.execute(
                        "SELECT to_action, to_is_parent_tag FROM c3p_task_orch WHERE to_tag_name LIKE %s AND to_key_level = %s",
                        ('%' + key + '%', key_level,)
                    )
            record = mycursor.fetchone()
            if record is not None:
                act = ''.join(record)
                logger.debug("performActionJSON - act- %s", act)
            if rfo_id[0:2] == "SR":
                resource_id = rfo_url_param_id
            if act == 'RAISE_SRN':
                logger.debug("performActionJSON - ADD values in RFO_DECOMPOSED")
                # global rfo_id, rfo_url_param_id
                sql = "INSERT INTO c3p_rfo_decomposed(od_rfo_id,od_param_id,od_seq,od_rf_taskname,od_req_resource_id,od_request_id,od_requeststatus,od_created_by,od_created_date,od_updated_by,od_updated_date) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
                # print (rfo_id)
                mycursor.execute("SELECT to_task_seq FROM c3p_task_orch where to_tag_name like %s and to_key_level= %s", ('%' + key + '%', key_level,))
                record2 = mycursor.fetchone()
                # act2=''.join(record2)
                task_pr = int(''.join(map(str, record2)))
                sx = datetime.datetime.now()
                # sx = x.strftime("%Y%m%d %H:%M:%S")
                val = (rfo_id, rfo_url_param_id, task_pr, key, resource_id,
                       '', 'queued', 'system', sx, 'system', sx)
                mycursor.execute(sql, val)
                mydb.commit()

            for res in key_val:
                performAction(res, res, key_level)
    except Exception as err:
        logger.error("Exception in performActionJSON: %s", err)
    finally:
        mydb.close
    return ""

def notify_BMC(so_num):
    json_data = {}
    mydb = Connections.create_connection()

    try:
        mycursor = mydb.cursor(buffered=True)
        v_so_num = so_num
        logger.debug("tmf:c3p_tmf_get_api::notify_BMC: - v_so_num - %s", v_so_num)
        mycursor.execute(
            "SELECT rfo_url_param_id,rfo_apioperation,rfo_created_date,rfo_apibody FROM c3p_rf_orders where rfo_id=%s", (v_so_num,))
        rf_res = mycursor.fetchone()
        # logger.debug("tmf:c3p_tmf_get_api::notify_BMC: - rf_res - %s", rf_res)

        now = datetime.datetime.now()
        tmz = str(now.astimezone().tzinfo)
        logger.debug("tmf:c3p_tmf_get_api::notify_BMC: - tmz - %s", tmz)
        formatted_date = now.strftime('%Y-%m-%d %H:%M:%S')
        ev_dt = formatted_date + " " + tmz
        logger.debug("tmf:c3p_tmf_get_api::notify_BMC: - ev_dt - %s", ev_dt)

        server_name = str(request.environ['SERVER_NAME'])

        logger.debug("tmf:c3p_tmf_get_api::notify_BMC: Entered at BMC_Test_Logic_Shraddha ")
        notify_apibody = {}
        u_event = {}
        results = []
        BMC_req = {}
        values = {}
        values["values"] = notify_apibody

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

            elif rf_res[1] == 'DELETE':
                event_type = 'ResourceFunctionDeleteEvent'

        mycursor.execute('INSERT INTO c3p_event (eventTime, eventType) VALUES (%s, %s)',
                         (rf_res[2], event_type,))  # Insert a row in event table
        mydb.commit()

        # Find the row_id of the record
        mycursor.execute("SELECT e_rowid, eventTime, eventType FROM c3p_event WHERE e_rowid = (select last_insert_id())")
        v_event = mycursor.fetchone()
        logger.debug("tmf:c3p_tmf_get_api::notify_BMC - v_event - %s", v_event)

        x = datetime.datetime.now()
        rand_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=5))
        event_ID = str(v_event[0]) + x.strftime("%Y%m%d") + rand_str  # Generate an Event Id for this event
        logger.debug("tmf:c3p_tmf_get_api::notify_BMC - event_ID - %s", event_ID)

        mycursor.execute(
            "UPDATE c3p_event SET eventID = %s WHERE e_rowid = %s", (event_ID,v_event[0],))
        mydb.commit()


        notify_apibody["u_event_id"] = v_so_num
        logger.debug("tmf:c3p_tmf_get_api::notify_BMC: v_so_num -%s ", v_so_num)
        notify_apibody["u_event_time"] = (str(v_event[1]) + " " + tmz)
        notify_apibody["u_event_type"] = str(v_event[2])
        notify_apibody["u_resource_function_id"] = str(rf_res[0])
        logger.debug("tmf:c3p_tmf_get_api::notify_BMC: v_so_num -%s ", str(v_event[2]))

        notify_apibody["u_event_status"] = "successful"

        notify_apibody["u_time_occured"] = ev_dt

        notify_apibody["u_event"] = u_event

        res_id = "SELECT od_req_resource_id FROM c3p_rfo_decomposed WHERE od_rfo_id = %s"
        mycursor.execute(res_id, (v_so_num,))  # execute above mysql instruction
        res_id = mycursor.fetchone()  # fetch the data
        logger.debug("tmf:c3p_tmf_get_api::notify_BMC -res_id -%s ", res_id)

        if res_id is not None:

            get_resrc_id = "SELECT od_request_id FROM c3p_rfo_decomposed WHERE od_rfo_id =%s"
            logger.debug("tmf:c3p_tmf_get_api::notify_BMC: get_request_id -%s ", get_resrc_id)
            mycursor.execute(get_resrc_id, (v_so_num,))
            resrc_id = mycursor.fetchall()  # fetch the data
            logger.debug("tmf:c3p_tmf_get_api::notify_BMC: request_id -%s ", resrc_id)

            for rid in resrc_id:

                # fetch the data from deviceinfo table
                mgmtipsql = "SELECT d_mgmtip,d_hostname,d_id,d_ref_device_id FROM c3p_deviceinfo  WHERE d_ref_device_id = %s"
                mycursor.execute(mgmtipsql, (res_id[0],))
                device_sql = mycursor.fetchone()

                logger.debug("tmf:c3p_tmf_get_api::notify_BMC: request_id in for loop is -%s ", resrc_id)
                logger.debug("tmf:c3p_tmf_get_api::notify_BMC: ip_address -%s ", device_sql[0])


                BMC_req["u_reference_device_id"] = device_sql[3]
                BMC_req["u_ip_addres"] = device_sql[0]
                BMC_req["u_device_id"] = device_sql[2]

                req_sql = "SELECT r_status,r_date_of_processing,r_end_date_of_processing FROM c3p_t_request_info  WHERE r_alphanumeric_req_id = %s"
                mycursor.execute(req_sql, (rid[0],))  # execute above mysql instruction
                req_sql = mycursor.fetchone()  # fetch the data

                BMC_req["u_request_id"] = rid[0]
                BMC_req["u_request_status"] = req_sql[0]
                BMC_req["u_hostname"] = device_sql[1]
                BMC_req["u_request_start_time"] = ((req_sql[1]) + " " + tmz)
                BMC_req["u_request_stop_time"] = ((req_sql[2]) + " " + tmz)
                logger.debug("tmf:c3p_tmf_get_api::notify_BMC: BMC_Notification_Request_StopTime -%s ",
                             (str(req_sql[2])))
                if description is None:
                    logger.debug("tmf:c3p_tmf_get_api::notify_BMC: inside description None ")
                    BMC_req["u_description"] = 'Successful Execution'
                else:
                    BMC_req["u_description"] = description
                # Common for all
                report_url = "http://" + server_name + ":8080/C3P/GetReportData/customerReport"

                BMC_req["u_report_url"] = report_url

                results.append(BMC_req)

        else:
            logger.debug("tmf:c3p_tmf_get_api::notify_BMC: Id is null else part ")
            rfo_apibody2 = json.loads(rf_res[3])
            logger.debug("tmf:c3p_tmf_get_api::notify_BMC: rfo_apibody2 -%s ", rfo_apibody2)

            for res_out in rfo_apibody2['resourceRelationship']:
                for res in res_out.keys():
                    if res == 'resource':
                        logger.debug("tmf:c3p_tmf_get_api::notify_BMC: inside if ")

                        BMC_req["u_reference_device_id"] = res_out[res]['id']
                        BMC_req["u_ip_addres"] = None
                        BMC_req["u_device_id"] = None

                        BMC_req["u_request_id"] = None
                        BMC_req["u_request_status"] = "Failure"
                        BMC_req["u_hostname"] = res_out[res]['name']
                        BMC_req["u_request_start_time"] = None
                        BMC_req["u_request_stop_time"] = None
                        if description is None:
                            BMC_req["u_description"] = "Requested Id Already Exists"
                        else:
                            BMC_req["u_description"] = description
                        # Common for all
                        report_url = "http://" + server_name + ":8080/C3P/GetReportData/customerReport"
                        BMC_req["u_report_url"] = report_url

                        results.append(BMC_req)

        logger.debug("tmf:c3p_tmf_get_api::notify_BMC: request_id id null -%s ", res_id)

        u_event["results"] = results

        json_data = json.dumps(values)
        logger.debug('tmf:c3p_tmf_get_api::notify_BMC - json_data ::%s', json_data)
        mycursor.execute("UPDATE c3p_event SET e_api_body = %s WHERE e_rowid = (select last_insert_id())", (json_data,))
        mydb.commit()

    except Exception as err:
        logger.error("tmf:c3p_tmf_get_api::notify_BMC: Exception in notify_BMC: %s", err)
    finally:
        mydb.close
    return json_data
'''******************************* End BMC notification: Shraddha***************************'''

def findNextPriorityReq():
    sourceSystem = ''
    wflow_status = True  # return created JSON
    rfo_apibody = json.dumps(request.json)
    logger.debug("findNextPriorityReq -rfo_apibody - %s", rfo_apibody)
    conn_flag = 0
    seq_res = 0
    # Value Computations begin
    v_so_num = request.json['SO_number']
    mydb = Connections.create_connection()
    try:
        mycursor = mydb.cursor(buffered=True)
        logger.debug("findNextPriorityReq - v_so_num - %s", v_so_num)
        v_minseq = "SELECT min(od_seq) FROM c3p_rfo_decomposed " \
        "WHERE od_rfo_id =%s AND lower(od_requeststatus) = 'queued'"  # this will select rowid and resourceid when requestid exist
        logger.debug("findNextPriorityReq - v_minseq - %s", v_minseq)
        mycursor.execute(v_minseq, (v_so_num,))  # execute above mysql instruction
        min_seq = mycursor.fetchone()  # fetch the data
        if v_so_num[0:2] == "SP":
            mycursor.execute("SELECT qt_source_system FROM c3p_t_qt_dashboard where qt_id=%s", (v_so_num,))
            sourceSystem = mycursor.fetchone()
            logger.debug("findNextPriorityReq -sourceSystem - %s", sourceSystem[0])
        if v_so_num[0:2] == 'SP' and sourceSystem[0] == 'c3p-ui':
            logger.debug("findNextPriorityReq -internal sourceSystem - %s", sourceSystem)
        else:
            # code for generation of source_system
            # is_External= True
            logger.debug("findNextPriorityReq -c3p_rf_orders - external source")
            mycursor.execute("SELECT rfo_apibody FROM c3p_rf_orders where rfo_id=%s", (v_so_num,))
            myresult = mycursor.fetchone()
            rfo_apibody = json.loads(''.join(myresult))
        # row_id = []     # List variable to store rowid
        # created_req = True
        if min_seq[0] is not None:
            v_row = "SELECT od_rowid, od_req_resource_id,od_rf_taskname FROM c3p_rfo_decomposed " \
            "WHERE od_rfo_id =%s AND lower(od_requeststatus) = 'queued' AND od_seq =%s"  # this will select rowid and resourceid when min sequenceid exist
            logger.debug("findNextPriorityReq - v_row - %s", v_row)
            mycursor.execute(v_row, (v_so_num, min_seq[0],))  # execute above mysql instruction
            rowid = mycursor.fetchall()  # fetch the data
            for row in rowid:
                # un-tuple the data to list
                logger.debug(
                    " findNextPriorityReq -ROW FOR JSON PREPRARER:: %s", row)
                if (row[2] == 'activationFeature' or row[2] == 'connection'):
                    device_specs = tmf2.getDeviceSpecs(row[1])
                    wflow_status = create_json(
                        v_so_num, device_specs, row[0], row[2], conn_flag, row[1])
                    v_rowstatus = "UPDATE c3p_rf_orders SET rfo_status = 'In Progress',rfo_updated_date = %s,rfo_updated_by='System'  WHERE rfo_id = %s"  # update the rfo status
                    logger.debug(
                        "findNextPriorityReq - v_rowstatus - %s", v_rowstatus)
                    # execute above mysql instruction
                    mycursor.execute(v_rowstatus, (datetime.datetime.now(), v_so_num,))
                    mydb.commit()
                    conn_flag = conn_flag + 1
                elif (row[2] == 'resourceCharacteristic'):
                    '''Added Dhanshri Mane :23/02/2021.
                    To Create OSupgrade Request exract json and check  resourceCharacteristic object present then
                    check into that vlaue os_version is present for name and new for value then create osupgrade request '''

                    mycursor.execute(
                        "SELECT rfo_apibody FROM c3p_rf_orders where rfo_id=%s", (v_so_num,))
                    myresult = mycursor.fetchone()
                    rfo_apibody = ''.join(myresult)
                    body = json.loads(rfo_apibody)
                    for bod in body['resourceRelationship']:
                        for bres in bod.keys():
                            if bres == "resource":

                                osUpgradeFlag = False
                                resource_data = bod['resource']
                                charid = resource_data['resourceCharacteristic']
                                for charData in charid:
                                    nameFlag = False
                                    valueFlag = False
                                    for dataValue in charData.keys():
                                        if dataValue == "name" and charData['name'] == 'os_version':
                                            nameFlag = True
                                        if dataValue == "value" and charData['value'] == 'new':
                                            valueFlag = True
                                        if (nameFlag and valueFlag):
                                            device_specs = tmf2.getDeviceSpecs(
                                                resource_data['id'])
                                            wflow_status = tmf2.create_osUpgrade_json(
                                                v_so_num, device_specs, resource_data['id'], row[2], conn_flag, row[1])

                                            v_rowstatus ="UPDATE c3p_rf_orders SET rfo_status = 'In Progress',rfo_updated_date = %s,rfo_updated_by='System'  WHERE rfo_id = %s"  # update the rfo status
                                            logger.debug(
                                                "findNextPriorityReq - v_rowstatus - %s", v_rowstatus)
                                            # execute above mysql instruction
                                            mycursor.execute(v_rowstatus, (datetime.datetime.now(), v_so_num,))
                                            mydb.commit()
                                            osUpgradeFlag = True
                                            conn_flag = conn_flag + 1
                                            break
                                if (osUpgradeFlag == False):
                                    msg = {}
                                    msg["msg"] = "No appropriate change found to raise request in C3P"
                                    json_data = json.dumps(msg)
                                    mycursor.execute("UPDATE c3p_rfo_decomposed set od_requeststatus ='Completed',od_request_json=%s where od_req_resource_id=%s", (json_data,resource_data['id'],))
                                    mydb.commit()
                                    conn_flag = conn_flag + 1

                else:
                    if (row[2] == 'test'):
                        device_specs = tmf2.getDeviceSpecs(row[1])
                        wflow_status = create_test_json(
                            v_so_num, device_specs, row[0], row[2], conn_flag, row[1])
                        v_rowstatus = "UPDATE c3p_rf_orders SET rfo_status = 'In Progress',rfo_updated_date = %s,rfo_updated_by='System'  WHERE rfo_id = %s"  # update the rfo status
                        logger.debug(
                            "findNextPriorityReq - v_rowstatus - %s", v_rowstatus)
                        # execute above mysql instruction
                        mycursor.execute(v_rowstatus, (datetime.datetime.now(), v_so_num,))
                        mydb.commit()
                        conn_flag = conn_flag + 1
                    elif (row[2] == 'backup'):
                        device_specs = tmf2.getDeviceSpecs(row[1])
                        wflow_status = tmf2.create_backup_json(
                            v_so_num, device_specs, row[0], row[2], conn_flag, row[1])
                        v_rowstatus = "UPDATE c3p_rf_orders SET rfo_status = 'In Progress',rfo_updated_date = %s,rfo_updated_by='System'  WHERE rfo_id = %s"  # update the rfo status
                        logger.debug(
                            "findNextPriorityReq - v_rowstatus - %s", v_rowstatus)
                        # execute above mysql instruction
                        mycursor.execute(v_rowstatus, (datetime.datetime.now(), v_so_num,))
                        mydb.commit()
                        conn_flag = conn_flag + 1
                    elif (row[2] == 'discovery'):
                        # enter logic to perform the discovery
                        v_rowstatus = "UPDATE c3p_rf_orders SET rfo_status = 'In Progress',rfo_updated_date = %s,rfo_updated_by='System'  WHERE rfo_id = %s"  # update the rfo status
                        logger.debug(
                            "findNextPriorityReq - v_rowstatus - %s", v_rowstatus)
                        # execute above mysql instruction
                        mycursor.execute(v_rowstatus, (datetime.datetime.now(), v_so_num,))
                        mydb.commit()
                        logger.debug(
                            'findNextPriorityReq - *********** Discovery Status Return Before ::: %s', wflow_status)
                        wflow_status = CSDRN.extDiscovery(v_so_num)
                        logger.debug(
                            'findNextPriorityReq - *********** Discovery Status Return After ::: %s', wflow_status)
                        # post dicovery completion
                        # update the c3p_rfo_decomposed  table, set status = 'Completed' for the given rfo_id
                        mycursor.execute(
                            "update c3p_rfo_decomposed SET od_requeststatus = 'Completed' WHERE od_rfo_id = %s", (v_so_num,))
                        logger.debug(
                            "findNextPriorityReq - decomposed record updated for discovery. %s", mycursor.rowcount)
                        mydb.commit()
                        # Call Camunda Workflow 2 once discovery is completed
                        url = configs.get("Camunda_Engine") + \
                              "/C3P_SO_NextRun_Workflow/start"
                        inp = {}
                        inp['businessKey'] = v_so_num
                        inp['variables'] = {"version": {"value": "1.0"}}
                        data_json = json.dumps(inp)
                        newHeaders = {"Content-type": "application/json",
                                      "Accept": "application/json"}

                        f = requests.post(url, data=data_json, headers=newHeaders)
                        logger.debug('datatodb - Response :: %s', f.json())
                    elif (row[2] == 'DeleteInstance'):
                        device_specs = tmf2.getDeviceSpecs(row[1])
                        wflow_status = tmf2.create_delete_instance_json(
                            v_so_num, device_specs, row[0], row[2], conn_flag, row[1])
                        v_rowstatus = "UPDATE c3p_rf_orders SET rfo_status = 'In Progress',rfo_updated_date = %s,rfo_updated_by='System'  WHERE rfo_id = %s"  # update the rfo status
                        logger.debug("findNextPriorityReq - v_rowstatus - %s", v_rowstatus)
                        # execute above mysql instruction
                        mycursor.execute(v_rowstatus, (datetime.datetime.now(),v_so_num,))
                        mydb.commit()
                        conn_flag = conn_flag + 1
                    elif (row[2] == 'ping'):
                        # enter logic to perform the discovery
                        if sourceSystem != 'c3p-ui':
                            v_rowstatus = "UPDATE c3p_rf_orders SET rfo_status = 'In Progress',rfo_updated_date = %s,rfo_updated_by='System'  WHERE rfo_id = %s"  # update the rfo status
                            logger.debug("findNextPriorityReq - v_rowstatus - %s", v_rowstatus)
                        # execute above mysql instruction
                        mycursor.execute(v_rowstatus, (datetime.datetime.now(),v_so_num,))
                        mydb.commit()
                        logger.debug(
                            'findNextPriorityReq - *********** ping Status Return Before ::: %s', wflow_status)
                        wflow_status = CIP.performPingIps(v_so_num)
                        logger.debug(
                            'findNextPriorityReq - *********** ping Status Return After ::: %s', wflow_status)
                        # post dicovery completion
                        # update the c3p_rfo_decomposed  table, set status = 'Completed' for the given rfo_id
                        mycursor.execute(
                            "update c3p_rfo_decomposed SET od_requeststatus = 'Completed' WHERE od_rfo_id =%s", (v_so_num,))
                        logger.debug(
                            "findNextPriorityReq - decomposed record updated for discovery. %s", mycursor.rowcount)
                        mydb.commit()
                        # Call Camunda Workflow 2 once discovery is completed
                        url = configs.get("Camunda_Engine") + \
                              "/C3P_SO_NextRun_Workflow/start"
                        inp = {}
                        inp['businessKey'] = v_so_num
                        inp['variables'] = {"version": {"value": "1.0"}}
                        data_json = json.dumps(inp)
                        newHeaders = {"Content-type": "application/json",
                                      "Accept": "application/json"}

                        f = requests.post(url, data=data_json, headers=newHeaders)
                        logger.debug('datatodb - Response :: %s', f.json())
                    else:
                        # new gcp request json creater function here
                        logger.debug("findNextPriorityReq - rfo_apibody - %s", rfo_apibody)
                        wflow_status = tmf2.create_json_gcp(
                            v_so_num, rfo_apibody, rfo_apibody['resourceRelationship'][seq_res], row[0])
                        # if wflw status is True update rf orders as failed
                        v_rowstatus = "UPDATE c3p_rf_orders SET rfo_status = 'In Progress',rfo_updated_date = %s,rfo_updated_by='System'  WHERE rfo_id = %s"  # update the rfo status
                        # print(v_rowstatus)
                        # execute above mysql instruction
                        mycursor.execute(v_rowstatus, (datetime.datetime.now(),v_so_num,))
                        mydb.commit()
                        seq_res = seq_res + 1

        else:  # rowid is not exist then mark rfo_status as "completed" in c3p_rf_orders table
            logger.debug("findNextPriorityReq - I am in else")
            wflow_status = True
            v_rowstatus = "UPDATE c3p_rf_orders SET rfo_status = 'Completed',rfo_updated_date = %s,rfo_updated_by='System'  WHERE rfo_id = %s"  # update the rfo status
            # connections, ports table to be updated here
            mycursor.execute(v_rowstatus, (datetime.datetime.now(),v_so_num,))  # execute above mysql instruction
            mydb.commit()
            mycursor.execute("update c3p_connections set co_status = 'Operational' where co_endpoint_a in (select ep_rowid from c3p_endpoints where rfo_id=%s)", (v_so_num,))
            mydb.commit()
            mycursor.execute("update c3p_ports set port_status='Occupied' where port_id in (select port_id from c3p_endpoints where rfo_id= %s)", (v_so_num,))
            mydb.commit()

    # function call
    # status_code = flask.Response(status=200)
    # SO_number: 232dds, workflow_status:true
    # need to send SO number and true if row id is none else so_number and false
    except Exception as err:
        global description
        description = str(err)
        logger.error("Exception in findNextPriorityReq: %s", err)
    finally:
        mydb.close
    return jsonify(SO_number=v_so_num, workflow_status=wflow_status), status.HTTP_200_OK

def ResourceFunction():
    status = []
    mydb = Connections.create_connection()
    try:
        mycursor = mydb.cursor(buffered=True)
        ids = request.args['id']
        v_status = "SELECT rfo_status, rfo_updated_date FROM c3p_rf_orders WHERE rfo_id = %s"  # this will select rowid and resourceid when requestid exist
        mycursor.execute(v_status, (ids,))  # execute above mysql instruction
        rf_status = mycursor.fetchall()  # fetch the data
        logger.debug("ResourceFunction - rf_status - %s", rf_status)
        status = rf_status[0]
        print(status[0], status[1], '\n')
    except Exception as err:
        logger.error("Exception in ResourceFunction: %s", err)
    finally:
        mydb.close
    return (status[0] + ' \t ' + str(status[1]))

""" Function : VNF Instantiation via C3P UI 04/Mar/2021 @ Sangita A  """
def internal_create_vnf_req():
    logger.debug("internal_create_vnf_req - request.json :: %s", request.json)
    try:
        apibody = request.get_json()
        if apibody["apiCallType"] == "c3p-ui":
            logger.debug('internal_create_vnf_req - api calltype is c3p-ui')
            json_data = json.dumps(tmf2.buildCreateVNFRequest(apibody))
            logger.debug(
                "internal_create_vnf_req - ICVR json_data :: %s", json_data)
            rand_str = tmf2.updateResourceCharacteristicData(apibody)
            newHeaders = {"Content-type": "application/json",
                          "Accept": "application/json"}
            url = configs.get("C3P_Application") + \
                  configs.get("Config_Create")
            req = requests.post(url, data=json_data, headers=newHeaders)
            resp_json = req.json()
            if len(resp_json) == 0:
                resp_json = {"output": "Error", "requestId": "", "version": ""}
            else:
                if "requestId" in resp_json:
                    tmf2.updateRequestIdResourceHistory(
                        resp_json['requestId'], rand_str)

            logger.debug(
                "internal_create_vnf_req - ICVR resp_json :: %s", resp_json)
            return resp_json
        else:
            logger.debug(
                "internal_create_vnf_req - Internal Create VNF Request API Call Type :: External")
        logger.debug(
            "internal_create_vnf_req - Internal Create VNF Request :: %s", apibody["customer"])
        return 'Pass'
    except Exception as err:
        logger.error("Exception in internal_create_vnf_req: %s", err)
        error_json = {"Error": err.__class__.__name__,
                      "requestId": "", "version": ""}
        return error_json

def notification(so_num):
    mydb = Connections.create_connection()
    try:
        mycursor = mydb.cursor(buffered=True)
        v_so_num = so_num
        logger.debug("tmf:c3p_tmf_get_api::notification - v_so_num - %s", v_so_num)

        mycursor.execute(
            "SELECT rfo_sourcesystem FROM c3p_rf_orders where rfo_id=%s", (v_so_num,))
        rf_srcsystm = mycursor.fetchone()
        logger.debug("tmf:c3p_tmf_get_api::notification - rf_srcsystm - %s", rf_srcsystm)

        if rf_srcsystm[0] == "CEBMCIN1":
            mycursor.execute("SELECT ss_name FROM c3p_m_source_system where ss_code= %s", (rf_srcsystm[0],))
            verify_source = mycursor.fetchone()
            logger.debug("tmf:c3p_tmf_get_api::notification - verify_source - %s", verify_source)

            if verify_source[0] == "BMC":
                jsondt = notify_BMC(v_so_num)
                #            logger.debug("tmf:c3p_tmf_get_api::notification:BMC - jsondt - %s", jsondt)

                mycursor.execute("SELECT srm_response_url,srm_auth_u_param,srm_auth_p_param FROM c3p_m_ss_response_mapping where srm_ss_code=%s and srm_module_code='CMNOTITK'", (rf_srcsystm[0],))
                url_tokn = mycursor.fetchone()
                logger.debug("tmf:c3p_tmf_get_api::notification:BMC - URL_tokn - %s", url_tokn)
                #           url = "https://techmgosi-restapi.onbmc.com/api/jwt/login"
                headers = {"Authorization": "AR-JWT{{jwt}}", "Content-Type": "application/x-www-form-urlencoded",
                           "Connection": "keep-alive"}

                login_data = {}
                login_data["username"] = url_tokn[1]
                login_data["password"] = url_tokn[2]
                logger.debug("tmf:c3p_tmf_get_api::notification:BMC - login_data - %s", login_data)

                token = requests.request("POST", url_tokn[0], headers=headers, data=login_data)
                print(token.text)
                logger.debug("tmf:c3p_tmf_get_api::notification:BMC - token - %s", token.text)
                #            url2 = "https://techmgosi-restapi.onbmc.com/api/arsys/v1/entry/C3P Interface update"

                mycursor.execute("SELECT srm_response_url FROM c3p_m_ss_response_mapping where srm_ss_code=%s and srm_module_code='CMNOTIAC'", (rf_srcsystm[0],))
                url_actual = mycursor.fetchone()
                logger.debug("tmf:c3p_tmf_get_api::notification:BMC - URL_Actual - %s", url_actual)

                headers2 = {"Content-Type": "application/json", "Authorization": "AR-JWT{{jwt}}",
                            "Cookie": "AR-JWT=" + token.text}
                respnse = requests.post(url_actual[0], headers=headers2, data=jsondt)
                print(respnse)
                logger.debug("tmf:c3p_tmf_get_api::notification:BMC - json_resp - %s", respnse)
                logger.debug('notification - Response JSON :: %s', respnse)
                logger.debug('notification - Status Code :: %s', respnse.status_code)
                if respnse.status_code == 201:
                    data = {"workflow_status": True}

                else:
                    data = {"workflow_status": False}  # Return back to Camunda flow
                print("response: Successfully Uploaded ", respnse.text)

        else:
            jsondt = tmf2.notify(v_so_num)
            #    resp=c3p_tmf_api.notify(jsondt)
            newHeaders = {"Content-type": "application/json", "Accept": "application/json"}
            url = configs.get("SNow_C3P_Notification")
            # Publish Notification
            #            respnse = requests.post(url, data=jsondt, headers=newHeaders, auth=HTTPBasicAuth(configs.get("SNow_C3P_User"), configs.get("SNow_C3P_Password")))
            respnse = requests.post(url, data=jsondt, headers=newHeaders,
                                    auth=(configs.get("SNow_C3P_User"),
                                          configs.get("SNow_C3P_Password")))
            #            json_resp = respnse.json()

            logger.debug('notification - Response JSON :: %s', respnse)
            logger.debug('notification - Status Code :: %s', respnse.status_code)
            if respnse.status_code == 201:
                data = {"SO_number": escape(request.json['SO_number']), "workflow_status": True}  # Return back to Camunda flow
                # Write code to call ServiceNow API to send discovered data
                # if request.json['SO_number'][0:2] == 'SD':
                # sendDiscoveryData = c3p_lib.sendDiscoveryData(request.get_json("SO_number"))
                # url='https://techmahindramspsvsdemo3.service-now.com/api/now/table/u_received_notifications' # Publish Notification
                # resp = requests.post(url,data=sendDiscoveryData, headers=newHeaders,auth=HTTPBasicAuth('webUser', 'Admin*123'))
                # Service Now API End
            else:
                data = {"SO_number": escape(request.json['SO_number']), "workflow_status": False}  # Return back to Camunda flow

            print("response: Successfully Uploaded ", respnse.text)

        global description
        description = None

    except Exception as err:
        logger.error("tmf:c3p_tmf_get_api::notification:Exception in notification: %s", err)
    finally:
        mydb.close
    return data

"""### milestone changes """
def milestoneStatus(content):
    mydb = Connections.create_connection()
    try:
        mycursor = mydb.cursor(buffered=True)
        v_so_num = content['so_id']

        mycursor = mydb.cursor(buffered=True)
        logger.debug("tmf:c3p_tmf_get_api::milestoneStatus - v_so_num - %s", v_so_num)

        mycursor.execute("SELECT rfo_sourcesystem FROM c3p_rf_orders where rfo_id=%s", (v_so_num,))
        rf_srcsystm = mycursor.fetchone()
        logger.debug("tmf:c3p_tmf_get_api::milestoneStatus - rf_srcsystm - %s", rf_srcsystm)

        if rf_srcsystm[0] == "CEBMCIN1":
            values = {}

            values["values"] = content
            respnc = tmf2.bMC_Authentication(rf_srcsystm[0], values)
            logger.debug("tmf:c3p_tmf_get_api::milestoneStatus - respnc - %s", respnc)
            logger.debug("tmf:c3p_tmf_get_api::milestoneStatus - respnc - %s", respnc.status_code)
            if respnc.status_code == 201:
                data = {"workflow_status": True}
            else:
                data = {"workflow_status": False}
        else:
            jsondt = str(content)
            newHeaders = {"Content-type": "application/json", "Accept": "application/json"}
            url = configs.get("SNow_C3P_Milestone")
            logger.debug('Milestone - url JSON :: %s', url)
            respnse = requests.post(url, data=jsondt, headers=newHeaders,
                                    auth=(configs.get("SNow_C3P_User"),
                                          configs.get("SNow_C3P_Password")))

            logger.debug('SNow_milestone - Response JSON :: %s', respnse)
            logger.debug('SNow_milestone - Status Code :: %s', respnse.status_code)
            logger.debug('SNow_milestone - Status Code :: %s', respnse.content)
            if respnse.status_code == 201:
                data = {"workflow_status": True}  # Return back to Camunda flow
            else:
                data = {"workflow_status": False}  # Return back to Camunda flow

        global description
        description = None
    except Exception as err:
        logger.error("tmf:c3p_tmf_get_api::milestoneStatus:Exception in milestoneStatus: %s", err)
    finally:
        mydb.close
    return data