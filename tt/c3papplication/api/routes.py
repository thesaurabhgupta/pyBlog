from c3papplication.basicauth import jwt_auth
from c3papplication.basicauth.jwt_auth import *
from flask import request, render_template, session, redirect,escape
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
from c3papplication.camara import c3p_camara_api, c3p_camara_get_api
from c3papplication.SNow import incidentWrkFlow, c3p_confg_req, incidentmgmt, ran_config

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

@c3p_api_blueprint.route('/c3p-p-core/api/ext/useraccess/', methods=['POST'])
@cross_origin(origin='*')
@authenticate
def userAccess():
    content = request.get_json()
    logger.debug("userAccess -body %s", content)
    user = str(content.get('username'))
    response = escape(f"Hello {user}, Welcome to C3P")
    return response


@c3p_api_blueprint.route('/c3p-p-core/api/ext/get/', methods=['GET'])
@cross_origin(origin='*')
@requireAuth()
def usersAccess():
    response = ("Hello, Welcome to C3P")
    return response


@c3p_api_blueprint.route('/c3p-p-core/api')
@cross_origin(origin='*')
def index():
    logger.info('index - inside c3p')
    return 'pass'


""" To perform : Ping Test endpoint : /C3P/api/PingTest/"""


@c3p_api_blueprint.route('/c3p-p-core/api/PingTest/', methods=['POST'])
@cross_origin(origin='*')
# @login_required
def pingTest():
    logger.debug('pingTest -start')
    content = request.get_json()
    logger.debug("pingTest -body %s", content)
    pingResult = c3p_lib.performPingTest(str(content['ipAddress']))
    return jsonify(pingResult)


""" To perform : Trace Route endpoint : /C3P/api/TraceRoute/"""


@c3p_api_blueprint.route('/c3p-p-core/api/TraceRoute/', methods=['POST'])
@cross_origin(origin='*')
def traceRoute():
    logger.debug('traceRoute -start')
    content = request.get_json()
    logger.debug('traceRoute -JSON :: %s', content)
    trResult = c3p_lib.performTraceRoute(str(content['ipAddress']))
    logger.debug('TraceRoute Return :: %s', trResult)
    return jsonify(trResult)


@c3p_api_blueprint.route('/c3p-p-core/api/PerfromTest/', methods=['POST'])
@cross_origin(origin='*')
def PerformTest():
    testResResponse = []
    content = request.get_json()
    testResults = c3p_lib.performTest(content)
    testResResponse = {"requestId": content['requestId'], "reqTestCategory": content['reqTestCategory'],
                       "reqTestMgmtIp": content['reqTestMgmtIp'], 'testResults': testResults}
    # print('test result response ::', testResResponse)
    return jsonify(testResResponse)


@c3p_api_blueprint.route('/c3p-p-core/api/Resource/v4/<int:id>/', methods=['POST', 'GET', 'PATCH', 'DELETE'])
@cross_origin(origin='*')
# @authenticate
def resourceId(id):
    if request.environ['REQUEST_METHOD'] == 'GET':
        args = request.args
        return get_api.listResource(str(id), args)
    else:
        return c3p_tmf_api.datatodb(id)


@c3p_api_blueprint.route('/c3p-p-core/api/Resource/v4/', methods=['POST', 'GET', 'PATCH', 'DELETE'])
@cross_origin(origin='*')
# @authenticate
def resource():
    if request.environ['REQUEST_METHOD'] == 'GET':
        args = request.args
        return get_api.listResource(None, args)
    else:
        return c3p_tmf_api.datatodb("SR")


@c3p_api_blueprint.route('/c3p-p-core/api/ResourceFunction/v4/<id>', methods=['POST', 'PATCH', 'GET', 'DELETE', 'PUT'])
@cross_origin(origin='*')
# @authenticate
def resourceFunctionId(id):
    if request.environ['REQUEST_METHOD'] == 'GET':
        # import pdb;pdb.set_trace()
        args = request.args
        return get_api.listRf(id, args)
    else:
        return c3p_tmf_api.datatodb(id)


@c3p_api_blueprint.route('/c3p-p-core/api/ResourceFunction/v4/', methods=['POST', 'PATCH', 'GET', 'DELETE', 'PUT'])
@cross_origin(origin='*')
# @authenticate
def resourceFunction():
    if request.environ['REQUEST_METHOD'] == 'GET':
        args = request.args
        return get_api.listRf(None, args)
    else:
        return c3p_tmf_api.datatodb(None)


@c3p_api_blueprint.route('/c3p-p-core/api/ResourceFunction/v4/decomp/', methods=['POST'])
@cross_origin(origin='*')
# @authenticate
def decompose():
    return c3p_tmf_api.decompose()


@c3p_api_blueprint.route('/c3p-p-core/api/ResourceFunction/Cloud/compute/instances/', methods=['POST'])
@cross_origin(origin='*')
def instanceCreationOnCloud():
    logger.info("instanceCreationOnCloud - start")
    try:
        apibody = request.json
        cloud = c3p_lib.findCloudPlatform(apibody)
        logger.debug("instanceCreationOnCloud - cloud: %s", cloud)
        if cloud == 'GCP':
            return c3p_gcp_api.gcpcreator(apibody)
        elif cloud == 'OpenStack':
            return openStackAPI.createVNFInstance(apibody)
        else:
            return jsonify({"Error": "Unable to find the Cloud information"}), status.HTTP_400_BAD_REQUEST

    except Exception as err:
        logger.error("instanceCreationOnCloud - Exception: %s", err)
        return jsonify({"Error": "Unable to create instance"}), status.HTTP_400_BAD_REQUEST


@c3p_api_blueprint.route('/c3p-p-core/api/ResourceFunction/GCP/compute/instances/', methods=['POST'])
@cross_origin(origin='*')
def gcpcreator():
    logger.info("gcpcreator - start")
    apibody = request.json
    return c3p_gcp_api.gcpcreator(apibody)


@c3p_api_blueprint.route('/c3p-p-core/api/ResourceFunction/GCP/delete/instances/', methods=['DELETE'])
@cross_origin(origin='*')
def deleteInstance():
    logger.info("gcpremover - start")
    apibody = request.get_json()
    return c3p_gcp_api.gcpremover(apibody)


@c3p_api_blueprint.route('/c3p-p-core/api/ResourceFunction/OpenStack/image/images', methods=['GET'])
@cross_origin(origin='*')
def openstackFetchImages():
    return openStackAPI.fetchImages()


@c3p_api_blueprint.route('/c3p-p-core/api/ResourceFunction/OpenStack/compute/flavors', methods=['GET'])
@cross_origin(origin='*')
def openstackFetchFlavors():
    return openStackAPI.fetchFlavors()


@c3p_api_blueprint.route('/c3p-p-core/api/ResourceFunction/OpenStack/compute/flavors', methods=['POST'])
@cross_origin(origin='*')
def openstackCreatFlavors():
    return openStackAPI.createFlavor()


@c3p_api_blueprint.route('/c3p-p-core/api/ResourceFunction/OpenStack/compute/zones', methods=['GET'])
@cross_origin(origin='*')
def openstackFetchOSZones():
    return openStackAPI.fetchOSZones()


@c3p_api_blueprint.route('/c3p-p-core/api/ResourceFunction/OpenStack/compute/servers', methods=['GET'])
@cross_origin(origin='*')
def openstackFetchServers():
    return openStackAPI.fetchServers()


@c3p_api_blueprint.route('/c3p-p-core/api/ResourceFunction/OpenStack/compute/servers/<serverId>', methods=['GET'])
@cross_origin(origin='*')
def openstackFetchServerDetails(serverId):
    logger.debug("openstackFetchServerDetails - serverId :: %s", serverId)
    return openStackAPI.fetchServerDetails(serverId)


@c3p_api_blueprint.route('/c3p-p-core/api/ResourceFunction/OpenStack/compute/servers', methods=['POST'])
@cross_origin(origin='*')
def openstackCreateServer():
    requestbody = request.json
    return openStackAPI.createServer(requestbody)


@c3p_api_blueprint.route('/c3p-p-core/api/ResourceFunction/OpenStack/network/networks', methods=['GET'])
@cross_origin(origin='*')
def openstackFetchNetworks():
    return openStackAPI.fetchNetworks()


@c3p_api_blueprint.route('/c3p-p-core/api/ResourceFunction/OpenStack/network/subnets', methods=['GET'])
@cross_origin(origin='*')
def openstackFetchSubnets():
    return openStackAPI.fetchSubnets()


@c3p_api_blueprint.route('/c3p-p-core/api/ResourceFunction/OpenStack/network/security-groups', methods=['GET'])
@cross_origin(origin='*')
def openstackFetchSecurityGroups():
    return openStackAPI.fetchSecurityGroups()


@c3p_api_blueprint.route('/c3p-p-core/api/ConfigurationManagement/instantiate/', methods=['POST'])
@cross_origin(origin='*')
# @require_oauth('profile')
# @authenticate
def internalVnfReq():
    logger.info("internalVnfReq - start")
    return c3p_tmf_api.internal_create_vnf_req()


@c3p_api_blueprint.route('/c3p-p-core/api/discovery/data/', methods=['POST'])
@cross_origin(origin='*')
def discoveryData():
    return c3p_lib.sendDiscoveryData(request.get_json("SO_number"))


@c3p_api_blueprint.route('/c3p-p-core/api/ResourceFunction/v4/notification/', methods=['POST'])
@cross_origin(origin='*')
# @authenticate
def respnc_notification():
    #    respnc=c3p_tmf_api.notification('SOPO2022052308295884')
    respnc = c3p_tmf_api.notification(request.json['SO_number'])
    print("END")
    return respnc, status.HTTP_200_OK


@c3p_api_blueprint.route('/c3p-p-core/api/ResourceFunction/v4/findNextPriorityReq/', methods=['POST'])
@cross_origin(origin='*')
# @authenticate
def findNextPriorityReq():
    return c3p_tmf_api.findNextPriorityReq()


@c3p_api_blueprint.route('/c3p-p-core/api/ResourceFunction/v4/monitor/')
@cross_origin(origin='*')
# @authenticate
def ResourceFunction():
    return c3p_tmf_api.ResourceFunction()


"""
Discovery for an external applications
"""


@c3p_api_blueprint.route('/c3p-p-core/api/ext/discovery/', methods=['POST'])
@cross_origin(origin='*')
def extDiscovery():
    # c3p_lib.dbConnection()
    ipAddrList = []
    disReturn = []
    if request.method == 'POST':

        content = request.get_json()
        if content['discoveryType'] == 'ipRange':
            if content['ipType'] == 'ipv4':
                if content['netMask'].split(".")[3] == '254':
                    logger.debug('Error - No IPs for discovery')
                    return 'Error - No IPs for discovery'

                """ get list of ip address in the given subnet """

                # ipAddrList=getAllIPsForDiscovery(content["startIp"], content["netMask"], content["endIp"])
                """ Create a discovery record """

                disRowInfo = CSDRN.createDiscoveryRecord(content)
                # disRowID    = disRowInfo[0]
                # disId       = disRowInfo[1]
                # disStart    = disRowInfo[2]
                rfo_id = disRowInfo[1]
                logger.debug("extDiscovery - rfo_id = %s", rfo_id)
                """ perform the discovery for each IP and Save the resultant """

                url = configs.get("Camunda_Engine") + "/decompWorkflow/start"
                inp = {}
                inp['businessKey'] = rfo_id
                inp['variables'] = {"version": {"value": "1.0"}}
                data_json = json.dumps(inp)
                newHeaders = {"Content-type": "application/json", "Accept": "application/json"}
                logger.debug("extDiscovery - test ..... data_json is %s", data_json)
                f = requests.post(url, data=data_json, headers=newHeaders)
                # print('f :: ', f.json())

                rhref = configs.get(
                    "Python_Application") + '/c3p-p-core/api/ResourceFunction/v4/monitor/?id=' + rfo_id
                return jsonify({"content": request.json, "href": rhref}), status.HTTP_202_ACCEPTED

            elif ((content['ipType']) == 'ipv6'):
                discoveryFlag = 'range ipv6'
                # print('iprange for ipv6')

            """ *********** for single IP - Device discovery ************* """
        elif (content['discoveryType'] == 'ipSingle'):
            if ((content['ipType']) == 'ipv4'):
                # print('single for ipv4')
                disRowId = []
                # Create a discovery record

                disRowInfo = CSDRN.createDiscoveryRecord(content)
                # disRowID = disRowInfo[0]
                # disId = disRowInfo[1]
                # disStart = disRowInfo[2]

                rfo_id = disRowInfo[1]
                logger.debug("extDiscovery - rfo_id = %s", rfo_id)
                """ perform the discovery for each IP and Save the resultant """

                url = configs.get("Camunda_Engine") + "/decompWorkflow/start"
                inp = {}
                inp['businessKey'] = rfo_id
                inp['variables'] = {"version": {"value": "1.0"}}
                data_json = json.dumps(inp)
                logger.debug("extDiscovery - Data JSON :: %s", data_json)
                newHeaders = {"Content-type": "application/json", "Accept": "application/json"}

                f = requests.post(url, data=data_json, headers=newHeaders)
                # logger.debug('extDiscovery - response :: %s', f.json())

                rhref = configs.get(
                    "Python_Application") + '/c3p-p-core/api/ResourceFunction/v4/monitor/?id=' + rfo_id
                return jsonify({"content": request.json, "href": rhref}), status.HTTP_202_ACCEPTED

            elif ((content['ipType']) == 'ipv6'):
                discoveryFlag = c3pdefination(content)
    else:
        logger.debug('extDiscovery - else block')
        return 'Inside Discovery GET Method'


"""
End discovery for external applications
"""


@c3p_api_blueprint.route('/c3p-p-core/api/discovery/', methods=['POST'])
@cross_origin(origin='*')
# @cross_origin(origin='http://10.62.0.42:8080')
def discovery():
    # c3p_lib.dbConnection()
    ipAddrList = []
    if request.method == 'POST':
        content = request.get_json()
        if (content['discoveryType'] == 'ipRange'):
            if ((content['ipType']) == 'ipv4'):
                if (content['netMask'].split(".")[3] == '254'):
                    logger.debug('discovery - Error - No IPs for discovery')
                    return 'Error - No IPs for discovery'

                """ get list of ip address in the given subnet """
                ipAddrList = getAllIPsForDiscovery(content["startIp"], content["netMask"], content["endIp"])
                """ Create a discovery record """
                rOut = CSDRN.resultDiscoveryReconciliation(content,
                                                           ipAddrList)  # single call to perform Discovery and Reconciliation
                return jsonify(rOut)

            elif ((content['ipType']) == 'ipv6'):
                discoveryFlag = 'range ipv6'
                # print('iprange for ipv6')

                """ *********** for single IP - Device discovery ************* """
        elif (content['discoveryType'] == 'ipSingle'):
            if ((content['ipType']) == 'ipv4'):
                # print('single for ipv4')
                ipAddrList = [content["startIp"], ]
                rOut = CSDRN.resultDiscoveryReconciliation(content,
                                                           ipAddrList)  # single call to perform Discovery and Reconciliation

                return jsonify(rOut)
            elif ((content['ipType']) == 'ipv6'):
                discoveryFlag = c3pdefination(content)
        elif (content['discoveryType'] == 'ipList'):
            if ((content['ipType']) == 'ipv4'):
                ipAddrList = content["startIp"]
                rOut = CSDRN.resultDiscoveryReconciliation(content,
                                                           ipAddrList)  # single call to perform Discovery and Reconciliation

                return jsonify(rOut)
            elif ((content['ipType']) == 'ipv6'):
                discoveryFlag = c3pdefination(content)
    else:
        logger.debug('discovery - Inside else block')
        return 'Inside Discovery GET Method'


@c3p_api_blueprint.route('/nav_to.do/')
def snow_request():
    logger.info('snow_request - Received snow request')
    return 'Pass'


@c3p_api_blueprint.route('/user/<username>')
def profile(username):
    logger.info('profile - inside user :: %s', username)
    return '{}\'s profile'.format(escape(username))


@c3p_api_blueprint.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        logger.info('login - Inside Post Method')
        return {"discovery": "post", "type": "range", "ip": "10.0.0.1"}
    else:
        logger.info('login - Inside GET Method')
        return 'show the login form'


""" Call Service Now hosted API to check the connectivity """


@c3p_api_blueprint.route('/c3p-p-core/api/calltoservicenow/', methods=['POST'])
@cross_origin(origin='*')
def calltoservicenow():
    url = configs.get("SNow_C3P_Instance") + "/api/now/table/u_cmdb_netgear_import"
    inp = {}
    inp['u_id'] = 521
    inp['u_auto_status'] = "true"
    data_json = json.dumps(inp)
    logger.debug('calltoservicenow - data_json - %s', data_json)
    newHeaders = {"Content-type": "application/json", "Accept": "application/json", }
    f = requests.post(url, data=data_json, headers=newHeaders,
                      auth=HTTPBasicAuth(configs.get("SNow_C3P_User"), configs.get("SNow_C3P_Password")))
    logger.debug('calltoservicenow - Response :: %s', f.json())
    return f.json()


@c3p_api_blueprint.route('/c3p-p-core/api/testRequest', methods=['POST'])
@cross_origin(origin='*')
# @authenticate
def TestRequest():
    logger.info('TestRequest - start')
    return c3p_tmf_api.datatodb(None)


""" For Backup Request For Device : /C3P/api/backupRequest"""
""" Author: Dhanshri Mane"""
""" Date: 21/1/2021"""


@c3p_api_blueprint.route('/c3p-p-core/api/backupRequest', methods=['POST'])
@cross_origin(origin='*')
# @authenticate
def backUpRequest():
    logger.info('backUpRequest - start')
    return c3p_tmf_api.datatodb(None)


@c3p_api_blueprint.route('/hello/')
@c3p_api_blueprint.route('/hello/<name>')
def hello(name=None):
    return render_template('hello.html', name=name)


def getAllIPsForDiscovery(sIP, netMask, eIP):
    rsIP = sIP
    seIP = []
    masks = {'255': 1, '254': 2, '252': 4, '248': 8, '240': 16, '224': 32, '192': 64, '128': 128, '0': 255}
    ipAddrRange = []
    # prepare the subnets request
    while (ipaddress.ip_address(sIP) <= ipaddress.ip_address(eIP)):
        subnets = [str(sIP) + "/" + str(netMask)]
        ipList = c3p_lib.calculate_subnets(subnets)
        for m in range(len(ipList['ipaddrs'])):
            sIP = ipaddress.ip_address(ipList['ipaddrs'][0])
            ipAddrRange.append(ipList['ipaddrs'][m])

        sIP = ipaddress.ip_address(sIP) + masks[netMask.split(".")[3]]

    for m in range(len(ipAddrRange)):
        cIP = ipAddrRange[m]
        # print('cIP : ', cIP)
        if ((ipaddress.ip_address(cIP) >= ipaddress.ip_address(rsIP)) and (
                ipaddress.ip_address(cIP) <= ipaddress.ip_address(eIP))):
            # print('selected ip : ', cIP)
            seIP.append(cIP)
        else:
            logger.debug('getAllIPsForDiscovery - reject ip : %s', cIP)
    # print('seIP Type:', type(seIP))
    return seIP

    # ******************** preparing return output in JSON format *********************


def resultInJsonFormat(rdID, rdSt, rRes):
    # print('inside formattor', rRes)
    rDisStatus = rRes[0]
    rDisStart = rdSt
    rDisEnd = rRes[1]

    # print(rdID, rDisStatus,rDisStart,rDisEnd)
    rOut = {"DisID ": rdID, "DisStatus": rDisStatus, "DisStart": rDisStart, "DisEnd": rDisEnd}
    # print('rOut =', rOut, type(rOut))
    # [('10.62.0.27', 'public', 23, 9, ' ', 'Cisco', 'PNF', '1', 'N', 'N', '510', '2020-09-13 14:01:24', '2020-09-13 14:01:31', 'C3P_CSR_Router1', 'admin')]
    return rOut


def hello_world():
    return 'Hello C3P'


""" To perform : Network Test throughput : /C3P/api/throughput/"""
""" Author: Ruchita Salvi"""
""" Date: 13/1/2021"""


@c3p_api_blueprint.route('/c3p-p-core/api/throughput/', methods=['POST'])
@cross_origin(origin='*')
def throughput():
    logger.info('throughput - start')
    content = request.get_json()
    thrResult = c3p_lib.performThroughput(content)
    # print('throughput Return :: ', thrResult )
    return thrResult


""" To perform :Parameterized Ping Test endpoint : /C3P/api/PingTest/"""
""" Author: Ruchita Salvi"""
""" Date: 15/1/2021"""


@c3p_api_blueprint.route('/c3p-p-core/api/ping/', methods=['POST'])
@cross_origin(origin='*')
def parameterizedPingTest():
    # print('inside PingTest')
    content = request.get_json()
    pingResult = networkTests.performPing(content)
    return jsonify(pingResult)


""" To perform :Latency endpoint : /C3P/api/latency/"""
""" Author: Ruchita Salvi"""
""" Date: 15/1/2021"""


@c3p_api_blueprint.route('/c3p-p-core/api/latency/', methods=['POST'])
@cross_origin(origin='*')
def performLatency():
    logger.info('performLatency - start')
    content = request.get_json()
    result = networkTests.performLatency(content)
    return jsonify(result)


""" To perform :Frameloss endpoint : /C3P/api/frameloss/"""
""" Author: Ruchita Salvi"""
""" Date: 15/1/2021"""


@c3p_api_blueprint.route('/c3p-p-core/api/frameloss/', methods=['POST'])
@cross_origin(origin='*')
def performFrameloss():
    logger.info('performFrameloss - start')
    content = request.get_json()
    result = networkTests.performFrameloss(content)
    return jsonify(result)


""" To perform : VNF Backup endpoint : /C3P/api/backupVNF/"""
""" Author: Rahul Tiwari"""
""" Function to perform backup when device type is VNF"""
""" Date: 08/2/2021"""


@c3p_api_blueprint.route('/c3p-p-core/api/backupVNF/', methods=['POST'])
@cross_origin(origin='*')
def backupVNF():
    logger.info('performFrameloss - start')
    content = request.get_json()
    logger.info('inside backup vnf -content-> %s', content)
    response = c3p_lib.backupVNF(content["ip"], content["hostname"], content["source"], content["port"],
                                 content["requestId"], content["stage"], content["version"])
    return response


@c3p_api_blueprint.route('/c3p-p-core/api/ipCalculator/', methods=['POST'])
@c3p_api_blueprint.route('/C3P/api/ipCalculator/', methods=['POST'])
@cross_origin(origin='*')
def ipCalculator():
    logger.info('ipCalculator - start')

    ''' Caluclate IPs valid between Start and End IP witing given Subnet Mask.
        If EndIP is not provided calculate it based on Subnet Mask
        input parameters ip, mask, there will not be end IP
        In return program will send back ip, mask and list of all valid ips
    '''
    content = request.get_json()
    masks = {'255': 1, '254': 2, '252': 4, '248': 8, '240': 16, '224': 32, '192': 64, '128': 128, '0': 255}
    logger.debug("ipCalculator - IP content :: %s", content["ip"].split(".")[3])
    eeIP = content["ip"].split(".")[3]
    eM = masks[content["mask"].split(".")[3]]
    logger.debug("ipCalculator -  eM ::%s ", eM)

    if ((int(eeIP) + int(eM)) > 255):
        eIP = ipaddress.ip_address(content["ip"]) - int(eeIP) + 255
    else:
        eIP = ipaddress.ip_address(content["ip"]) + masks[content["mask"].split(".")[3]]

    logger.debug("ipCalculator - Calucated eIP is :: %s", eIP)
    exclusionList = []
    sIp = c3p_lib.getAllIPsForDiscovery(content["ip"], content["mask"], eIP, exclusionList)
    result = {"startip": content["ip"], "mask": content["mask"], "endip": str(eIP), "seIP": sIp}
    logger.debug("ipCalculator - result - %s", result)
    return jsonify(result)


""" To perform : GET of tree view of features from Mongo : /C3P/api/yang/features"""
""" Author: Ruchita Salvi"""
""" Date: 18/3/2021"""


@c3p_api_blueprint.route('/c3p-p-core/api/yang/treeview', methods=['POST'])
@cross_origin(origin='*')
def yangFeatures():
    json_object = {}
    result = dict()
    content = request.get_json()
    filename = content['filename']
    result["featureTree"] = yangExtractor.getTreeViewFeatures(filename)
    json_object = json.dumps(result, indent=4)
    return json_object


""" To perform : GET of yang file from Mongo : /C3P/api/yang"""
""" Author: Ruchita Salvi"""
""" Date: 18/3/2021"""


@c3p_api_blueprint.route('/c3p-p-core/api/yang', methods=['POST'])
@cross_origin(origin='*')
def yangfiles():
    json_object = {}
    result = dict()
    content = request.get_json()
    filename = content['filename']
    result["yangFile"] = yangExtractor.getYang(filename)
    json_object = json.dumps(result, indent=4)
    return json_object


""" To Save Netconf Template Details """
""" endpoint : /C3P/api/templateManagment"""
""" Author: Dhanshri Mane """
""" Date: 17/3/2021"""


@c3p_api_blueprint.route('/c3p-p-core/api/templateManagment', methods=['POST'])
@cross_origin(origin='*')
def templateManagment():
    logger.info('inside Template Managment')
    # content = request.get_json()
    content = request.get_data()
    templateObj = TemplateManagment()
    result = templateObj.templateManagmentDatatoDB(content)
    return jsonify(result)


""" To perform :Add job in scheduler jobstore : /C3P/api/schedular"""
""" Author: Ruchita Salvi"""
""" Date: 16/4/2021"""


@c3p_api_blueprint.route('/c3p-p-core/api/schedular', methods=['POST'])
@cross_origin(origin='*')
def schedulework():
    logger.info('inside schedular')
    data = request.get_json()
    job = ""
    job = c3pscheduler.addJobMtd(data, scheduler)

    return "job details: %s" % job


""" To perform :Create topology map : /C3P/api/topology/map"""
""" Author: Ruchita Salvi"""
""" Date: 16/4/2021"""


@c3p_api_blueprint.route('/c3p-p-core/api/topology/map', methods=['POST'])
@cross_origin(origin='*')
def topology():
    logger.info('APP :: Topology')
    data = request.get_json()
    # Changes by Ruchita for seperation of VLT code in seperate method to loop over devices
    if (data['operation'] == 'RLT'):
        results = c3p_topology.create_logical_topology(data)
    elif (data['operation'] == 'VLT'):
        results = c3p_topology.show_logical_topology(data)

    return jsonify(results)


###################################
# OAuth2.0 Related code
###################################
def current_user():
    if 'id' in session:
        uid = session['id']
        return User.query.get(uid)
    return None


def split_by_crlf(s):
    return [v for v in s.splitlines() if v]


@c3p_api_blueprint.route('/', methods=('GET', 'POST'))
def home():
    if request.method == 'POST':
        username = request.form.get('username')
        user = User.query.filter_by(username=username).first()
        if not user:
            user = User(username=username)
            db.session.add(user)
            db.session.commit()
        session['id'] = user.id
        # if user is not just to log in, but need to head back to the auth page, then go for it
        next_page = request.args.get('next')
        if next_page and next_page.startswith('/'):
            return redirect(escape(next_page))
        return redirect('/')
    user = current_user()
    if user:
        clients = OAuth2Client.query.filter_by(user_id=user.id).all()
    else:
        clients = []

    return render_template('home.html', user=user, clients=clients)


@c3p_api_blueprint.route('/logout')
def logout():
    del session['id']
    return redirect('/')


@c3p_api_blueprint.route('/create_client', methods=('GET', 'POST'))
def create_client():
    user = current_user()
    if not user:
        return redirect('/')
    if request.method == 'GET':
        return render_template('create_client.html')

    client_id = gen_salt(24)
    client_id_issued_at = int(time.time())
    client = OAuth2Client(
        client_id=client_id,
        client_id_issued_at=client_id_issued_at,
        user_id=user.id,
    )

    form = request.form
    client_metadata = {
        "client_name": form["client_name"],
        "client_uri": form["client_uri"],
        "grant_types": split_by_crlf(form["grant_type"]),
        "redirect_uris": split_by_crlf(form["redirect_uri"]),
        "response_types": split_by_crlf(form["response_type"]),
        "scope": form["scope"],
        "token_endpoint_auth_method": form["token_endpoint_auth_method"]
    }
    client.set_client_metadata(client_metadata)

    if form['token_endpoint_auth_method'] == 'none':
        client.client_secret = ''
    else:
        client.client_secret = gen_salt(48)

    db.session.add(client)
    db.session.commit()
    return redirect('/')


@c3p_api_blueprint.route('/c3p-p-core/api/oauth/authorize', methods=['GET', 'POST'])
@cross_origin(origin='*')
def authorize():
    user = current_user()
    # if user log status is not true (Auth server), then to log it in
    if not user:
        return redirect(url_for('website.routes.home', next=request.url))
    if request.method == 'GET':
        try:
            grant = authorization.validate_consent_request(end_user=user)
        except OAuth2Error as error:
            return error.error
        return render_template('authorize.html', user=user, grant=grant)
    if not user and 'username' in request.form:
        username = request.form.get('username')
        user = User.query.filter_by(username=username).first()
    if request.form['confirm']:
        grant_user = user
    else:
        grant_user = None
    return authorization.create_authorization_response(grant_user=grant_user)


@c3p_api_blueprint.route('/c3p-p-core/api/oauth/token', methods=['POST'])
@cross_origin(origin='*')
def issue_token():
    return authorization.create_token_response()


@c3p_api_blueprint.route('/c3p-p-core/api/oauth/revoke', methods=['POST'])
@cross_origin(origin='*')
def revoke_token():
    return authorization.create_endpoint_response('revocation')


@c3p_api_blueprint.route('/c3p-p-core/api/me')
@cross_origin(origin='*')
# @require_oauth('profile')
def api_me():
    user = current_token.user
    return jsonify(id=user.id, username=user.username)


@c3p_api_blueprint.route('/c3p-p-core/api/test')
@cross_origin(origin='*')
# @require_oauth('profile')
def api_test():
    return jsonify(id='120', username='Test User')


""" To perform : Generate pdf report endpoint : /C3P/api/generatePdf/"""
""" Author: Rahul Tiwari"""
""" Function to perform generate pdf report"""
""" Date: 08/6/2021"""


@c3p_api_blueprint.route('/c3p-p-core/api/generatePdf/', methods=['POST'])
@cross_origin(origin='*')
def generatePDFReport():
    logger.info('generatePDFReport - start')
    content = request.get_json()
    logger.info('inside generatePDFReport -content-> %s', content)
    response = c3p_lib.generatePDFReport(content["input"], content["output"])
    return response


""" To perform : Netconf ROC Edit : /C3P/api/netconfedit/"""
""" Author: Ruchita Salvi"""
""" Function to perform generate pdf report"""
""" Date: 08/6/2021"""


@c3p_api_blueprint.route('/c3p-p-core/api/netconfedit/', methods=['POST'])
@cross_origin(origin='*')
def netconfEdit():
    logger.info('netconf edit rpc - start')
    content = request.get_json()
    logger.info('netconf edit rpc -content-> %s', content)
    response = netconf.editConf(content)
    return response


""" To perform : Test Netconf : /C3P/api/netconftest/"""
""" Author: Rahul Tiwari"""
""" Function to perform test getrpc"""
""" Date: 08/6/2021"""


@c3p_api_blueprint.route('/c3p-p-core/api/netconftest/', methods=['POST'])
@cross_origin(origin='*')
def performTestConf():
    logger.info('netconf test getrpc - start')
    content = request.get_json()
    logger.info('netconf test getrpc -content-> %s', content)
    response = netconf.performTestConf(content)
    return jsonify(response)


""" To perform : Test Netconf : /C3P/api/configdelta/"""
""" Author: Ruchita Salvi"""
""" Function to find delta if present in two text files"""
""" Date: 07/7/2021"""


@c3p_api_blueprint.route('/c3p-p-core/api/configdelta/', methods=['POST'])
@cross_origin(origin='*')
def performconfigdelta():
    logger.info('configdelta - start')
    content = request.get_json()
    logger.info('configdelta -content-> %s', content)
    response = c3p_lib.computeDeltaInInputs(content["file1"], content["file2"])
    return jsonify(response)