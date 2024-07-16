from c3papplication.basicauth import jwt_auth
from c3papplication.basicauth.jwt_auth import *
from flask import request, render_template, session, redirect
from markupsafe import escape
from . import c3p_api_blueprint
# import c3p_snmp_discovery_reconcilation as CSDR
# from c3p_ip_range_calculate import *
import ipaddress
from c3papplication.discovery import c3p_topology
from c3papplication.discovery import c3p_physical_topology as phyTopo
from c3papplication.common import c3p_lib
from c3papplication.email import c3p_emailOperations
from c3papplication.conf.springConfig import springConfig
# import concurrent.futures
import json
import time
from flask_cors import cross_origin
import requests
from c3papplication.tmf import c3p_tmf_api
from c3papplication.gcp import c3p_gcp_api
from requests.auth import HTTPBasicAuth
from flask_api import status
from c3papplication.discovery import c3p_snmp_disc_rec_new as CSDRN
from c3papplication.common import c3p_network_tests as networkTests
from c3papplication.openstack.C3POpenStackAPI import C3POpenStackAPI
from jproperties import Properties
from c3papplication.templatemanagement.TemplateManagment import TemplateManagment
from c3papplication.templatemanagement import TemplateComparison
from c3papplication.templatemanagement import XMLComparison
from c3papplication.yang import yangExtractor
import logging, logging.config

# from pymongo import MongoClient
from pprint import pprint
# from gridfs import GridFS
# from bson import objectid
# from os import path
# Connections,
from apscheduler.schedulers.background import BackgroundScheduler
# from datetime import datetime
from c3papplication.scheduler import C3PSchedulerLib as c3pscheduler
from apscheduler.jobstores.mongodb import MongoDBJobStore
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor

from werkzeug.security import gen_salt
from authlib.integrations.flask_oauth2 import current_token
from authlib.oauth2 import OAuth2Error
from c3papplication.oauth.models import db, User, OAuth2Client
from c3papplication.oauth.oauth2 import authorization, require_oauth
from c3papplication.basicauth.basic_auth import *
from c3papplication.common import c3p_netconf_rpc as netconf
from c3papplication.ipmanagement.c3p_ip_management import getPoolId, checkHostIp, allocateHostIp
# from c3papplication.chatbot.c3p_chatterbot import getbotresponse
from c3papplication.openstack.c3p_terraform import deployInstance
from c3papplication.openstack.c3p_Orchestration import deployStack
from c3papplication.tmf import c3p_tmf_get_api as get_api
from c3papplication.openstack import c3p_Compute
from c3papplication.gcp import c3p_gcp_compute
from c3papplication.ipmanagement import c3p_ip_ping
from c3papplication.tmf import c3p_tmf_res_spec_get_apiv2 as get_apiv2
from c3papplication.inventory import c3p_inventory
from c3papplication.templatemanagement import backupDelivery
from c3papplication.ran import c3p_ran
from c3papplication.tmf import c3p_tmf_incident_raise
from c3papplication.camara import c3p_camara_api,c3p_camara_get_api,c3p_dvclctn
from c3papplication.SNow import incidentWrkFlow, c3p_confg_req, incidentmgmt, ran_config,c3p_config_tt
from c3papplication.basicauth.OAuth2 import requireAuth


# log_file_path = path.join(path.dirname(path.abspath(__file__)), 'conf/logging.conf')
# logging.config.fileConfig(log_file_path, disable_existing_loggers=False)
logger = logging.getLogger(__name__)

# c3p_api_blueprint.config['CORS_HEADERS'] = 'application/json'
openStackAPI = C3POpenStackAPI()

configs = springConfig().fetch_config()

# Scheduler initialization needs to be done from main class as it needs imports
jobstores = {
    'default': MongoDBJobStore(database='c3pdbschema', collection='jobs', host='localhost', port=27017)
}
executors = {
    'default': ThreadPoolExecutor(10),
    'processpool': ProcessPoolExecutor(5)
}
job_defaults = {
    'coalesce': False,
    'max_instances': 5
}
scheduler = BackgroundScheduler({'apscheduler.timezone': configs.get('APP_SERVER_TIMEZONE')}, jobstores=jobstores,
                                executors=executors, job_defaults=job_defaults)


# scheduler.start()
""" To perform : Physical topology : /C3P/api/ptopology/"""
""" Author: Ruchita Salvi"""
""" Function to generate physical"""
""" Date: 22/07/2021"""


@c3p_api_blueprint.route('/c3p-p-core/api/physicaltopology/', methods=['POST'])
@cross_origin(origin='*')
def physicaltopology():
    response = ""
    logger.info('physicaltopology - start')
    content = request.get_json()
    # print("input",content)
    logger.info('physicaltopology -content-> %s', content)
    response = phyTopo.triggerPhysicalTopology(content)
    return response


""" To perform : Physical topology : /C3P/api/physicaltopologycsv/"""
""" Author: Ruchita Salvi"""
""" Function to generate physical topologys csv file"""
""" Date: 22/07/2021"""


@c3p_api_blueprint.route('/c3p-p-core/api/physicaltopologycsv/', methods=['POST'])
@cross_origin(origin='*')
def physicaltopologycsv():
    response = []
    logger.info('physicaltopologycsv - start')
    content = request.get_json()
    # print("input",content)
    logger.info('physicaltopologycsv -content-> %s', content)
    response = phyTopo.createCSV(content)
    return jsonify({'output': response})


""" To perform : Inset file in mongo  : /C3P/api/mongo/insert/file"""
""" Author: Ruchita Salvi"""
""" Function to insert file in mongo db, this is a generic standalone function and can be resued"""
""" Date: 22/07/2021"""


@c3p_api_blueprint.route('/c3p-p-core/api/mongo/insert/file', methods=['POST'])
@cross_origin(origin='*')
def mongoinsert():
    response = ""
    logger.info('mongoinsert - start')
    content = request.get_json()
    # print("input",content)
    logger.info('mongoinsert -content-> %s', content)
    response = phyTopo.mongofileinsert(content)
    return response


""" To perform : GET of  file from Mongo : /C3P/api/file"""
""" Author: Ruchita Salvi"""
""" Function to get file from mongo db, this is a generic standalone function and can be resued"""
""" Date: 22/07/2021"""


@c3p_api_blueprint.route('/c3p-p-core/api/file', methods=['POST'])
@cross_origin(origin='*')
def getFileFromMongo():
    json_object = {}
    result = dict()
    content = request.get_json()
    result["file"] = yangExtractor.getScript(content)
    json_object = json.dumps(result, indent=4)
    return json_object


""" To perform : GET of  file from Mongo : /C3P/api/file"""
""" Author: Ruchita Salvi"""
"""ONLY FOR TESTING PUROSE"""


@c3p_api_blueprint.route('/c3p-p-core/api/createLogicalTopology', methods=['POST'])
@cross_origin(origin='*')
def createLogicalTopology():
    json_object = ""
    content = request.get_json()
    json_object = c3p_topology.create_logical_topology(content)
    return json_object


""" To perform :Update Device Role after Discover/Customer Onboarding"""
""" Author: Dhanshri Mane"""
""" Date: 9/8/2021"""


@c3p_api_blueprint.route('/c3p-p-core/api/updateDevieRole', methods=['POST'])
@cross_origin(origin='*')
def updatedeviceRole():
    response = dict()
    content = request.get_json()
    hostName = content['hostName']
    ipAddress = content['ipAddress']
    response['message'] = CSDRN.setDeviceRole(hostName, ipAddress)
    return response


# if __name__ == '__main__':
#   app.run(debug=True, threaded = True, port = 5000, host="0.0.0.0")

@c3p_api_blueprint.route('/c3p-p-core/api/configDifference/', methods=['POST'])
@cross_origin(origin='*')
def performconfigDifference():
    logger.info('configDifference - start')
    content = request.get_json()
    logger.info('configDifference -content-> %s', content)
    response = c3p_lib.computeConfigDifferenceCount(content["file1"], content["file2"])
    return response


""" To perform : GET of  IP pool ranges from ip pool range management : /C3P/api/ippool"""
""" Author: Mahesh"""
"""Date: 24/8/2021"""


@c3p_api_blueprint.route('/c3p-p-core/api/getIpPoolRanges', methods=['GET'])
@cross_origin(origin='*')
def getIpPoolRanges():
    poolId = getPoolId()
    return jsonify(poolId)


""" To perform : GET pool id and ip from host ip management : /C3P/api/ipallocate"""
""" Author: Mahesh"""
"""Date: 24/8/2021"""


@c3p_api_blueprint.route('/c3p-p-core/api/ipToAllocate', methods=['POST', 'GET'])
@cross_origin(origin='*')
def ipToAllocate():
    if request.method == 'POST':
        content = request.get_json()
        poolId = content['poolId']
        ip = checkHostIp(poolId)
        return jsonify(ip)


""" To perform : update the status in host ip management and ip pool range  : /C3P/api/status"""
""" Author: Mahesh"""
"""Date: 24/8/2021"""


@c3p_api_blueprint.route('/c3p-p-core/api/updateHostStatus', methods=['POST'])
@cross_origin(origin='*')
def updateHostStatus():
    if request.method == 'POST':
        content = request.get_json()
        myData = allocateHostIp(content)
        return jsonify(myData)


@c3p_api_blueprint.route('/c3p-p-core/api/templateComparison', methods=['POST'])
@cross_origin(origin='*')
def performTemplateDifference():
    logger.info('templateComparison - start')
    content = request.get_json()
    logger.info('templateComparison -content-> %s', content['templates'])
    response = TemplateComparison.computeTemplateDifference(content['templates'])
    return response


@c3p_api_blueprint.route('/c3p-p-core/api/content/comparison', methods=['POST'])
@cross_origin(origin='*')
def performDifference():
    logger.info('comparison - start')
    content = request.get_json()
    logger.info('comparison -content-> %s', content['inputs'])
    response = c3p_lib.computeDifference(content['inputs'])
    return response


####################################################
# Chatbot app
###################################################
# @c3p_api_blueprint.route('/c3p-p-core/chatbot/getData', methods=['POST'] )
# @cross_origin(origin='*')
# def getBotData():
#     content = request.get_json()
#     return getbotresponse(content)


""" To perform : Deploye the instance in openstack"""


@c3p_api_blueprint.route('/c3p-p-core/api/deploy/instance', methods=['POST'])
@cross_origin(origin='*')
def createInstance():
    content = request.get_json()
    return deployInstance(content['folderPath'])


""" To perform : ID generation endpoint : /C3P/api/generateId/"""
""" Author: Rahul Tiwari"""
""" Function to perform id generation"""
""" Date: 12/01/2022"""


@c3p_api_blueprint.route('/c3p-p-core/core/generateId', methods=['POST'])
@cross_origin(origin='*')
def generateId():
    logger.info('generateId - start')
    content = request.get_json()
    logger.info('inside idGenerate -content-> %s', content)
    response = c3p_lib.generateId(content["sourceSystem"], content["requestingPageEntity"], content["requestType"],
                                  content["requestingModule"])
    return response


""" To perform : Deploye the stack in openstack"""


@c3p_api_blueprint.route('/c3p-p-core/api/openstack/deploy/stack', methods=['POST'])
@cross_origin(origin='*')
def createStack():
    content = request.get_json()
    logger.info('inside openstack -content-> %s', content)
    return deployStack(template_id=content['templateId'], stackName=content['stack_name'], parameters=content)


""" To perform : Deploye the MCC in openstack"""


@c3p_api_blueprint.route('/c3p-p-core/api/openstack/deploy/instancemcc', methods=['POST'])
@cross_origin(origin='*')
def computeInstance():
    content = request.get_json()
    logger.info('openstack computeinstanceMcc -content-> %s', content)
    return c3p_Compute.computeInstanceMcc(content)


""" To perform : VNF Scaling"""


@c3p_api_blueprint.route('/c3p-p-core/api/vnf/scaling', methods=['POST'])
@cross_origin(origin='*')
def vnfScaling():
    content = request.get_json()
    if content["cloud"] == "GCP" and content["scalingFeature"] == "diskSize":
        status = c3p_gcp_compute.disksResize(content)
    elif content["cloud"] == "GCP" and content["scalingFeature"] == "machineType":
        status = c3p_gcp_compute.setMachineType(content)
    elif content["cloud"] == "openStack" and content["scalingFeature"] == "diskSize":
        status = c3p_Compute.volumeResize(content)
    elif content["cloud"] == "openStack" and content["scalingFeature"] == "flavor":
        status = c3p_Compute.resizeFlavor(content)
    else:
        pass
    return status


""" To perform :execution of ping test"""


@c3p_api_blueprint.route('/c3p-p-core/api/pingflow/', methods=['POST'])
@cross_origin(origin='*')
def pingflow():
    pingInfo = request.get_json()
    return c3p_ip_ping.pingTestflow(pingInfo)


@c3p_api_blueprint.route('/c3p-p-core/api/ResourceSpec/v41/<id>/', methods=['GET'])
@cross_origin(origin='*')
# @authenticate
def resourceSpecId(id):
    if request.environ['REQUEST_METHOD'] == 'GET':
        args = request.args
        return get_apiv2.listResourceSpec(str(id), args)


@c3p_api_blueprint.route('/c3p-p-core/api/ResourceSpec/v41/', methods=['GET'])
@cross_origin(origin='*')
# @authenticate
def resourceSpec():
    if request.environ['REQUEST_METHOD'] == 'GET':
        args = request.args
        return get_apiv2.listResourceSpec(None, args)


@c3p_api_blueprint.route('/c3p-p-core/api/PhysicalResourceSpec/v41/<id>/', methods=['GET'])
@cross_origin(origin='*')
# @authenticate
def physicalResourceSpecId(id):
    if request.environ['REQUEST_METHOD'] == 'GET':
        args = request.args
        return get_apiv2.listPhysicalResourceSpec(str(id), args)


@c3p_api_blueprint.route('/c3p-p-core/api/PhysicalResourceSpec/v41/', methods=['GET'])
@cross_origin(origin='*')
# @authenticate
def physicalResourceSpec():
    if request.environ['REQUEST_METHOD'] == 'GET':
        args = request.args
        return get_apiv2.listPhysicalResourceSpec(None, args)


@c3p_api_blueprint.route('/c3p-p-core/api/LogicalResourceSpec/v41/<id>/', methods=['GET'])
@cross_origin(origin='*')
# @authenticate
def logicalresourceSpecId(id):
    if request.environ['REQUEST_METHOD'] == 'GET':
        args = request.args
        return get_apiv2.listLogicalResourceSpec(str(id), args)


@c3p_api_blueprint.route('/c3p-p-core/api/LogicalResourceSpec/v41/', methods=['GET'])
@cross_origin(origin='*')
# @authenticate
def logicalresourceSpec():
    if request.environ['REQUEST_METHOD'] == 'GET':
        args = request.args
        return get_apiv2.listLogicalResourceSpec(None, args)


@c3p_api_blueprint.route('/c3p-p-core/api/ResourceSpecRelationship/v41/', methods=['GET'])
@cross_origin(origin='*')
# @authenticate
def resourceSpecRelationship():
    if request.environ['REQUEST_METHOD'] == 'GET':
        args = request.args
        return get_apiv2.listResourceSpecRelationship(None)


@c3p_api_blueprint.route('/c3p-p-core/api/ResourceSpecRelationship/v41/<id>/', methods=['GET'])
@cross_origin(origin='*')
# @authenticate
def resourceSpecRelationshipId(id):
    if request.environ['REQUEST_METHOD'] == 'GET':
        args = request.args
        return get_apiv2.listResourceSpecRelationship(str(id))


@c3p_api_blueprint.route('/c3p-p-core/api/ResourceFuncSpecification/v41/', methods=['GET'])
@cross_origin(origin='*')
# @authenticate
def resourceFuncRelationship():
    if request.environ['REQUEST_METHOD'] == 'GET':
        args = request.args
        return get_apiv2.listResourceFuncSpecification(None, args)


@c3p_api_blueprint.route('/c3p-p-core/api/ResourceFuncSpecification/v41/<id>/', methods=['GET'])
@cross_origin(origin='*')
# @authenticate
def resourceFuncRelationshipId(id):
    if request.environ['REQUEST_METHOD'] == 'GET':
        args = request.args
        return get_apiv2.listResourceFuncSpecification(str(id), args)


""" To perform : inventory data with external system(BMC)"""


@c3p_api_blueprint.route('/c3p-p-core/api/ext/inventory/NeDetails/', methods=['POST'])
@cross_origin(origin='*')
#@authenticate
@requireAuth()
def inventoryDataWithExternalSystem():
    content = request.get_json()
    logger.debug("routes:inventoryDataWithExternalSystem ::content json: %s", content)
    return c3p_inventory.bmcInventory(content)


@c3p_api_blueprint.route('/c3p-p-core/api/ResourceFunction/v4/milestonestatus/', methods=['POST'])
@cross_origin(origin='*')
# @authenticate
def respnc_milestone():
    content = request.get_json()
    respnc = c3p_tmf_api.milestoneStatus(content)
    return respnc, status.HTTP_200_OK


@c3p_api_blueprint.route('/c3p-p-core/api/ext/inventory/list/', methods=['GET'])
@cross_origin(origin='*')
#@authenticate
@requireAuth()
def inventoryDataDetails():
    content = request.get_json()
    logger.debug("routes:inventoryDataDetails ::content json: %s", content)
    return c3p_inventory.deviceInventoryDashboard()


@c3p_api_blueprint.route('/c3p-p-core/api/template/networkBackup/', methods=['POST'])
@cross_origin(origin='*')
def networkBackup():
    content = request.get_json()
    files = backupDelivery.networkBackup(content)
    print("END")
    return files


# @c3p_api_blueprint.route('/c3p-p-core/api/RanDataInsert', methods=['PUT'])
# def RanParaInsert():
#     respnc= upload_data.ranInsertData()
#     return respnc

@c3p_api_blueprint.route('/c3p-p-core/api/importTempData', methods=['POST'])
# Retrieve import Temp data - To Retrieve change data
def retImportedTempData():
    logger.debug('inside temp methd')
    logger.debug('request_json %s', request.get_json())
    input_json = request.get_json()
    logger.debug('input_json %s', input_json)
    respnc = c3p_ran.retImportData(input_json)
    return jsonify(respnc)


# To Update the changed values of xl to db.
@c3p_api_blueprint.route('/c3p-p-core/api/template/ranBaselineParaUpdation', methods=['POST'])
def RanParaUpdate():
    logger.debug('Routes: Ran Baseline Parameter')
    logger.debug('request %s', request)
    uploaded_file = request.files['file']
    logger.debug('uploaded_file %s', uploaded_file)
    data = request.form
    logger.debug('data %s', data)
    respnc = c3p_ran.ranParaValueUpdate(uploaded_file, data)
    return respnc


# API to send mail report to specified users
@c3p_api_blueprint.route('/c3p-p-core/api/c3pSendMailReport', methods=['POST'])
@cross_origin(origin='*')
def sendMail():
    content = request.get_json()
    return c3p_emailOperations.sendEmail(content)


@c3p_api_blueprint.route('/c3p-p-core/api/tmf/incidentTicket', methods=['POST'])
def incidentRaise():
    input_json = request.get_json()
    respnc = jsonify(c3p_tmf_incident_raise.incidntRaise(input_json))
    return respnc


# @c3p_api_blueprint.route('/c3p/naas/api/camara/qod', methods=['POST']) #
# @cross_origin(origin='*')
# @authenticate
# def camaraFunctionId():
#      return c3p_camara_api.camaradatatodb(None)


@c3p_api_blueprint.route('/c3p-p-core/naas/api/camara/qod', methods=['POST'])  #
@cross_origin(origin='*')
@token_required
def camaraFunctionId():
    req_json = request.get_json()
    if req_json:
        res_json = c3p_camara_api.verify_input(req_json)
        if not res_json:
            return c3p_camara_api.camaradatatodb(None)
        else:
            return res_json
    else:
        return jsonify(
            {"code": "Invalid_Input", "status": 400, "message": "Expected property is missing: Request_Body"})


@c3p_api_blueprint.route('/c3p-p-core/naas/api/camara/qod/<id>', methods=['GET'])  #
@cross_origin(origin='*')
@token_required
def camaraQodDetails(id):
    return jsonify(c3p_camara_get_api.camara_qod_details(id))


# @c3p_api_blueprint.route('/c3p-p-core/naas/api/camara/qod/<id>', methods=['DELETE'])  #
# @cross_origin(origin='*')
# @authenticate
# @token_required
# def camaraQodDelete(id):
#    c3p_camara_api.camaradatatodb(id, "SMF")
#    return jsonify({"Code":"Session got deleted"})

@c3p_api_blueprint.route('/c3p-p-core/naas/api/camara/qod/<id>', methods=['DELETE'])  #
@cross_origin(origin='*')
@token_required
def camaraQodDelete(id):
    del_status = c3p_camara_api.verify_del_id(id)
    if not del_status:
        c3p_camara_api.camaradatatodb(id)
        return jsonify({"Code": "Session got deleted"})
    else:
        return del_status


@c3p_api_blueprint.route('/c3p-p-core/naas/api/camara/monitor/')
@cross_origin(origin='*')
# @authenticate
def camaraFunction():
    return c3p_camara_api.camaraMonitorFunction()


@c3p_api_blueprint.route('/c3p-p-core/naas/api/camara/decomp/', methods=['POST'])
@cross_origin(origin='*')
# @authenticate
def camaradecompose():
    return c3p_camara_api.camaradecompose()


@c3p_api_blueprint.route('/c3p-p-core/naas/api/camara/findNextPriorityReq/', methods=['POST'])
@cross_origin(origin='*')
# @authenticate
def camarafindNextPriority():
    return c3p_camara_api.camarafindNextPriorityReq()


@c3p_api_blueprint.route('/c3p-p-core/naas/api/camara/notification/', methods=['POST'])
@cross_origin(origin='*')
# @authenticate
def camara_notification():
    #    respnc=c3p_tmf_api.notification('SOPO2022052308295884')
    respnc = c3p_camara_api.camaranotification(request.json['SO_number'])
    print("END")
    return respnc, status.HTTP_200_OK


@c3p_api_blueprint.route('/c3p-p-core/api/loginauth/token/', methods=['POST'])
def authlogin():
    login = request.get_json()
    output_json = jwt_auth.token_generator(login)
    return output_json


@c3p_api_blueprint.route('/c3p-p-core/api/compareXmlFiles', methods=['POST'])
@cross_origin(origin='*')
def compareXmlFile():
    content = request.get_json()
    return XMLComparison.xmlComparison(content)


# API to fetch html file from the system
@c3p_api_blueprint.route('/c3p-p-core/api/fetchResult', methods=['POST'])
@cross_origin(origin='*')
def fetchResult():
    content = request.get_json()
    response = XMLComparison.fetchXmlComparisonResult(content)
    return response


@c3p_api_blueprint.route('/c3p-p-core/naas/api/camara/homedevice/qod', methods=['PUT'])
@cross_origin(origin='*')
@token_required
def camara_homedvc_func():
    if request.method == 'PUT':
        req_json = request.get_json()
        if req_json:
            res_json = c3p_camara_api.verify_hmdvc_input(req_json)
            if not res_json:
                return c3p_camara_api.camaradatatodb(None)
            else:
                return res_json
        else:
            return jsonify(
                {"code": "Invalid_Input", "status": 400, "message": "Expected property is missing: Request_Body"})


@c3p_api_blueprint.route('/c3p-p-core/naas/api/camara/homedevice/qod/<id>', methods=['GET'])  #
@cross_origin(origin='*')
@token_required
def camaraHomedvcQodDetails(id):
    return jsonify(c3p_camara_get_api.camara_qod_details(id))


@c3p_api_blueprint.route('/c3p-p-core/naas/api/camara/homedevice/qod/<id>', methods=['DELETE'])  #
@cross_origin(origin='*')
@token_required
def camaraHmdvcDelete(id):
    del_status = c3p_camara_api.verify_del_id(id)
    if not del_status:
        response = c3p_camara_api.camaradatatodb(id)
        return response
    else:
        return del_status


###Servicenow Workflow
@c3p_api_blueprint.route('/c3p-p-core/api/incidentFlow', methods=['POST'])  #
@cross_origin(origin='*')
def testIncidentFlow():
    req_json = request.get_json()
    return incidentWrkFlow.incidentworkflow(req_json)


""" To perform :execution of bulk ping test """


@c3p_api_blueprint.route('/c3p-p-core/api/ext/pingflow/', methods=['POST'])
@cross_origin(origin='*')
@authenticate
def pingflowext():
    pingInfo = request.get_json()
    return c3p_ip_ping.pingTestflow(pingInfo)


@c3p_api_blueprint.route('/c3p-p-core/api/ext/pingflow/result/<id>', methods=['GET'])
@cross_origin(origin='*')
@authenticate
def pingReport(id):
    return c3p_ip_ping.PingDetailReport(id)


@c3p_api_blueprint.route('/c3p-p-core/api/ext/conf/request', methods=['POST'])  #
@cross_origin(origin='*')
def confRequest():
    req_json = request.get_json()
    return c3p_confg_req.configrequest(req_json)


@c3p_api_blueprint.route('/c3p-p-core/api/ext/incident/confg', methods=['POST'])
@cross_origin(origin='*')
def incidentRequest():
    req_json = request.get_json()
    return incidentmgmt.incidentmgmtconf(req_json)


@c3p_api_blueprint.route('/c3p-p-core/api/ext/ranconfig', methods=['POST'])
@cross_origin(origin='*')
def ranconfigRequest():
    req_json = request.get_json()
    return jsonify(ran_config.ran_conf(req_json))


@c3p_api_blueprint.route('/c3p-p-core/api/devicelocation/', methods=['POST'])  #
@cross_origin(origin='*')
def Device_Location():
    req_json = request.get_json()
    return jsonify(c3p_dvclctn.dvc_locatn_test(req_json))


@c3p_api_blueprint.route('/c3p-p-core/naas/api/camara/devicelocation', methods=['POST'])  #
@cross_origin(origin='*')
def Device_Location1():
    req_json = request.get_json()
    verified_val = c3p_dvclctn.verify_dvc_input(req_json)
    if not verified_val:
        return c3p_camara_api.camaradatatodb(None)
    else:
        return verified_val


@c3p_api_blueprint.route('/c3p-p-core/naas/api/nef/ext/devicelocation', methods=['POST'])  #
@cross_origin(origin='*')
def Device_Location2():
    req_json = request.get_json()
    val = c3p_dvclctn.lat_long_ext(req_json)
    logger.debug("Routes2:: val: %s ",val)
    return val


@c3p_api_blueprint.route('/c3p-p-core/api/ext/config/migration', methods=['POST'])  #
@cross_origin(origin='*')
def config_migration():
    logger.debug('request %s', request)
    uploaded_file = request.files['file']
    logger.debug('uploaded_file %s', uploaded_file)
    respnc = c3p_config_tt.config_MPS(uploaded_file)
    return respnc

##-- Camara External Api -- ##

@c3p_api_blueprint.route('/c3p-p-core/naas/api/ext/camara/devicelocation', methods=['POST'])  #
@cross_origin(origin='*')
def Device_Location3():
    req_json = request.get_json()
    verified_val = c3p_dvclctn.verify_dvc_input(req_json)
    if not verified_val:
        return c3p_camara_api.camaradatatodb(None)
    else:
        return verified_val


@c3p_api_blueprint.route('/c3p-p-core/naas/api/ext/camara/homedevice/qod', methods=['PUT'])
@cross_origin(origin='*')
@token_required
def camara_homedvc_func1():
    if request.method == 'PUT':
        req_json = request.get_json()
        if req_json:
            res_json = c3p_camara_api.verify_hmdvc_input(req_json)
            if not res_json:
                return c3p_camara_api.camaradatatodb(None)
            else:
                return res_json
        else:
            return jsonify(
                {"code": "Invalid_Input", "status": 400, "message": "Expected property is missing: Request_Body"})


@c3p_api_blueprint.route('/c3p-p-core/naas/api/ext/camara/homedevice/qod/<id>', methods=['GET'])  #
@cross_origin(origin='*')
@token_required
def camaraHomedvcQodDetails1(id):
    return jsonify(c3p_camara_get_api.camara_qod_details(id))


@c3p_api_blueprint.route('/c3p-p-core/naas/api/ext/camara/homedevice/qod/<id>', methods=['DELETE'])  #
@cross_origin(origin='*')
@token_required
def camaraHmdvcDelete1(id):
    del_status = c3p_camara_api.verify_del_id(id)
    if not del_status:
        response = c3p_camara_api.camaradatatodb(id)
        return response
    else:
        return del_status



@c3p_api_blueprint.route('/c3p-p-core/naas/api/ext/camara/qod', methods=['POST'])  #
@cross_origin(origin='*')
@token_required
def camaraFunctionId1():
    req_json = request.get_json()
    if req_json:
        res_json = c3p_camara_api.verify_input(req_json)
        if not res_json:
            return c3p_camara_api.camaradatatodb(None)
        else:
            return res_json
    else:
        return jsonify(
            {"code": "Invalid_Input", "status": 400, "message": "Expected property is missing: Request_Body"})


@c3p_api_blueprint.route('/c3p-p-core/naas/api/ext/camara/qod/<id>', methods=['GET'])  #
@cross_origin(origin='*')
@token_required
def camaraQodDetails1(id):
    return jsonify(c3p_camara_get_api.camara_qod_details(id))


@c3p_api_blueprint.route('/c3p-p-core/naas/api/ext/camara/qod/<id>', methods=['DELETE'])  #
@cross_origin(origin='*')
@token_required
def camaraQodDelete1(id):
    del_status = c3p_camara_api.verify_del_id(id)
    if not del_status:
        c3p_camara_api.camaradatatodb(id)
        return jsonify({"Code": "Session got deleted"})
    else:
        return del_status

## -end of external --#