# #from flask import url_for, request, render_template, jsonify, session, redirect
# from markupsafe import escape
# #from . import c3p_api_blueprint
# # import c3p_snmp_discovery_reconcilation as CSDR
# # from c3p_ip_range_calculate import *
# import ipaddress
#
# from c3papplication.discovery import c3p_topology
# from c3papplication.discovery import c3p_physical_topology as phyTopo
# from c3papplication.common import c3p_lib
# # import concurrent.futures
# import json
# import time
# #from flask_cors import cross_origin
# import requests
# from c3papplication.tmf import c3p_tmf_api
# from c3papplication.gcp import c3p_gcp_api
# from requests.auth import HTTPBasicAuth
# #from flask_api import status
# from c3papplication.discovery import c3p_snmp_disc_rec_new as CSDRN
# from c3papplication.common import c3p_network_tests as networkTests
# from c3papplication.openstack.C3POpenStackAPI import C3POpenStackAPI
# from jproperties import Properties
# from c3papplication.templatemanagement.TemplateManagment import TemplateManagment
# from c3papplication.templatemanagement import TemplateComparison
# from c3papplication.yang import yangExtractor
# import logging, logging.config
#
# # from pymongo import MongoClient
# from pprint import pprint
# # from gridfs import GridFS
# # from bson import objectid
# # from os import path
# # Connections,
# from apscheduler.schedulers.background import BackgroundScheduler
# # from datetime import datetime
# from c3papplication.scheduler import C3PSchedulerLib as c3pscheduler
# from apscheduler.jobstores.mongodb import MongoDBJobStore
# from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor
#
# from werkzeug.security import gen_salt
# #from authlib.integrations.flask_oauth2 import current_token
# from authlib.oauth2 import OAuth2Error
# from c3papplication.oauth.models import db, User, OAuth2Client
# from c3papplication.oauth.oauth2 import authorization, require_oauth
# from c3papplication.basicauth.basic_auth import *
# from c3papplication.common import c3p_netconf_rpc as netconf
# from c3papplication.ipmanagement.c3p_ip_management import getPoolId, checkHostIp, allocateHostIp
# #from c3papplication.chatbot.c3p_chatterbot import getbotresponse
# from c3papplication.openstack.c3p_terraform import deployInstance
# from c3papplication.openstack.c3p_Orchestration import deployStack
# from c3papplication.tmf import c3p_tmf_get_api as get_api
# from c3papplication.openstack import c3p_Compute
# from c3papplication.gcp import c3p_gcp_compute
# from c3papplication.ipmanagement import c3p_ip_ping
# from c3papplication.tmf import c3p_tmf_res_spec_get_apiv2 as get_apiv2
# from c3papplication.conf.springConfig import springConfig
# from typing import Union,Dict,List,AnyStr,Any
#
# ##import for Fastapi
# from c3papplication.api import c3p_fast_api
# from fastapi import Request,Body
# from fastapi.encoders import jsonable_encoder
# from c3papplication.conf import base_model as bs_mdl
# from fastapi.responses import RedirectResponse
#
# logger = logging.getLogger(__name__)
#
# # c3p_api_blueprint.config['CORS_HEADERS'] = 'application/json'
# openStackAPI = C3POpenStackAPI()
#
#configs = springConfig().fetch_config()
# # Scheduler initialization needs to be done from main class as it needs imports
# jobstores = {
#     'default': MongoDBJobStore(database='c3pdbschema', collection='jobs', host='localhost', port=27017)
# }
# executors = {
#     'default': ThreadPoolExecutor(10),
#     'processpool': ProcessPoolExecutor(5)
# }
# job_defaults = {
#     'coalesce': False,
#     'max_instances': 5
# }
# scheduler = BackgroundScheduler({'apscheduler.timezone': configs.get('APP_SERVER_TIMEZONE')}, jobstores=jobstores,
#                                 executors=executors, job_defaults=job_defaults)
# # scheduler.start()
#
# @c3p_fast_api.api_route('/c3p-p-core/api')
# #@cross_origin(origin='*')
# def index():
#     logger.info('index - inside c3p')
#     return 'pass'
#
#
# @c3p_fast_api.api_route('/c3p-p-core/api/PingTest/', methods=['POST'] )
# async def pingTest(info : Request):
#     logger.debug('pingTest -start')
#     logger.debug('pingTest -info %s',info.method)
#     req_info = await info.json()
#     logger.debug("pingTest -body %s",req_info)
#     pingResult = c3p_lib.performPingTest(str(req_info['ipAddress']))
#     return jsonable_encoder(pingResult)
#
# # Method 2)
# @c3p_fast_api.post("/c3p-p-core/api/PingTest1")
# async def pingTest(info: bs_mdl.pingItem ):
#     info=info.dict()
#     pingResult = c3p_lib.performPingTest(str(info['ipAddress']))
#     return jsonable_encoder(pingResult)
#
# """ To perform : Trace Route endpoint : /c3p-p-core/api/TraceRoute/"""
# @c3p_fast_api.post('/c3p-p-core/api/TraceRoute/')
# async def traceRoute(info: bs_mdl.pingItem):
#     logger.debug('traceRoute -start')
#     info=info.dict()
#     logger.debug('traceRoute -JSON :: %s', info)
#     trResult = c3p_lib.performTraceRoute(str(info['ipAddress']))
#     logger.debug('TraceRoute Return :: %s', trResult )
#     return jsonable_encoder(trResult)
#
# @c3p_fast_api.post('/c3p-p-core/api/PerfromTest/')
# def PerformTest(info: bs_mdl.performTest):
#     content = info.dict()
#     testResults = c3p_lib.performTest(content)
#     testResResponse = {"requestId": content['requestId'], "reqTestCategory": content['reqTestCategory'], "reqTestMgmtIp": content['reqTestMgmtIp'], 'testResults': testResults }
#     # print('test result response ::', testResResponse)
#     return jsonable_encoder(testResResponse)
#
# @c3p_fast_api.api_route('/c3p-p-core/api/Resource/v4/{id}', methods=['POST','GET','PATCH', 'DELETE'])
# #@authenticate
# async def resource(info:Request):
#     if info.method == 'GET' :
#         logger.debug("await %s",info.path_params)
#         id = info.path_params["id"]
#         args= info.query_params
#         logger.debug("args %s",args)
#         return get_api.listResource(id,args)
#     else :
#         id = info.path_params["id"]
#         data = await request.json()
#         return c3p_tmf_api.datatodb(id,request,data)
#
# #Method 2
# # @c3p_fast_api.get("/c3p-p-core/api/Resource/v4/{id}",tags=["Resource"])
# # def resource(id:str, field: Union[str, None] = None,category:Union[str, None] = None):
# #          args = {}
# #          if field:
# #              args={"field":field,"category":category}
# #          return get_api.listResource(id,args)
#
#
# @c3p_fast_api.api_route('/c3p-p-core/api/Resource/v4/', methods=['POST','GET','PATCH', 'DELETE'])
# #@authenticate
# async def resource(request:Request):
#     if request.method == 'GET' :
#         args = request.query_params
#         return get_api.listResource(None,args)
#     else :
#         data=await request.json()
#         return c3p_tmf_api.datatodb("SR",request,data)
#
# @c3p_fast_api.api_route('/c3p-p-core/api/ResourceFunction/v4/{id}', methods=['POST', 'PATCH', 'GET', 'DELETE', 'PUT'])
# #@authenticate
# async def resourceFunctionId(request:Request):
#   if request.method == 'GET' :
#      #import pdb;pdb.set_trace()
#      id=request.path_params["id"]
#      args = request.query_params
#      return get_api.listResource(id,args)
#   else :
#      id = request.path_params["id"]
#      data = await request.json()
#      return c3p_tmf_api.datatodb(id,request,data)
#
# @c3p_fast_api.api_route('/c3p-p-core/api/ResourceFunction/v4/', methods=['POST', 'PATCH', 'GET', 'DELETE', 'PUT'])
# #@authenticate
# async def resourceFunction(request:Request):
#   if request.method == 'GET' :
#     args = request.query_params
#     return get_api.listRf(None,args)
#   else :
#      data=await request.json()
#      return c3p_tmf_api.datatodb(None,request,data)
#
# @c3p_fast_api.post('/c3p-p-core/api/ResourceFunction/v4/decomp/')
# #@authenticate
# async def decompose(request:Request) :
#     data= await request.json()
#     return c3p_tmf_api.decompose(data)
#
# @c3p_fast_api.post('/c3p-p-core/api/ResourceFunction/Cloud/compute/instances/')
# async def instanceCreationOnCloud(request:Request):
#     logger.info("instanceCreationOnCloud - start")
#     try:
#         apibody = await request.json()
#         cloud = c3p_lib.findCloudPlatform(apibody)
#         logger.debug("instanceCreationOnCloud - cloud: %s", cloud)
#         if cloud == 'GCP':
#             return c3p_gcp_api.gcpcreator(apibody)
#         elif cloud == 'OpenStack':
#             return openStackAPI.createVNFInstance(apibody)
#         else:
#             return jsonable_encoder({"Error": "Unable to find the Cloud information"}), status.HTTP_400_BAD_REQUEST
#
#     except Exception as err:
#         logger.error("instanceCreationOnCloud - Exception: %s", err)
#         return jsonable_encoder({"Error": err}), status.HTTP_400_BAD_REQUEST
#
# @c3p_fast_api.post('/c3p-p-core/api/ResourceFunction/GCP/compute/instances/')
# async def gcpcreator(request:Request) :
#     logger.info("gcpcreator - start")
#     apibody = await request.json()
#     return c3p_gcp_api.gcpcreator(apibody)
#
# @c3p_fast_api.delete('/c3p-p-core/api/ResourceFunction/GCP/delete/instances/')
# async def deleteInstance(info:Request) :
#     logger.info("gcpremover - start")
#     apibody = await info.json()
#     return c3p_gcp_api.gcpremover(apibody)
#
# @c3p_fast_api.get('/c3p-p-core/api/ResourceFunction/OpenStack/image/images')
# def openstackFetchImages() :
#     return openStackAPI.fetchImages()
#
# @c3p_fast_api.get('/c3p-p-core/api/ResourceFunction/OpenStack/compute/flavors')
# def openstackFetchFlavors() :
#     return openStackAPI.fetchFlavors()
#
# @c3p_fast_api.post('/c3p-p-core/api/ResourceFunction/OpenStack/compute/flavors')
# def openstackCreatFlavors(request:Request) :
#     return openStackAPI.createFlavor(request)
#
# @c3p_fast_api.get('/c3p-p-core/api/ResourceFunction/OpenStack/compute/zones')
# def openstackFetchOSZones() :
#     return openStackAPI.fetchOSZones()
#
# @c3p_fast_api.get('/c3p-p-core/api/ResourceFunction/OpenStack/compute/servers')
# def openstackFetchServers() :
#     return openStackAPI.fetchServers()
#
# @c3p_fast_api.get('/c3p-p-core/api/ResourceFunction/OpenStack/compute/servers/<serverId>')
# def openstackFetchServerDetails(serverId) :
#     logger.debug("openstackFetchServerDetails - serverId :: %s",serverId)
#     return openStackAPI.fetchServerDetails(serverId)
#
# @c3p_fast_api.post('/c3p-p-core/api/ResourceFunction/OpenStack/compute/servers')
# async def openstackCreateServer(request:Request) :
#     requestbody=await request.json()
#     return openStackAPI.createServer(requestbody)
#
# @c3p_fast_api.get('/c3p-p-core/api/ResourceFunction/OpenStack/network/networks')
# def openstackFetchNetworks() :
#     return openStackAPI.fetchNetworks()
#
# @c3p_fast_api.get('/c3p-p-core/api/ResourceFunction/OpenStack/network/subnets')
# def openstackFetchSubnets() :
#     return openStackAPI.fetchSubnets()
#
# @c3p_fast_api.get('/c3p-p-core/api/ResourceFunction/OpenStack/network/security-groups')
# def openstackFetchSecurityGroups() :
#     return openStackAPI.fetchSecurityGroups()
#
# @c3p_fast_api.post('/c3p-p-core/api/ConfigurationManagement/instantiate/')
# #@require_oauth('profile')
# #@authenticate
# def internalVnfReq(request:Request) :
#     logger.info("internalVnfReq - start")
#     return c3p_tmf_api.internal_create_vnf_req(request)
#
# @c3p_fast_api.post('/c3p-p-core/api/discovery/data/')
# async def discoveryData(request:Request):
#     info = await request.json()
#     return c3p_lib.sendDiscoveryData( info["SO_number"])
#
# @c3p_fast_api.post('/c3p-p-core/api/ResourceFunction/v4/notification/')
# #@cross_origin(origin='*')
# #@authenticate
# async def respnc_notification(request:Request):
# #    respnc=c3p_tmf_api.notification('SOPO2022052308295884')
#     info = await request.json()
#     respnc=c3p_tmf_api.notification(info['SO_number'])
#     print("END")
#     return respnc,status.HTTP_200_OK
#
# @c3p_fast_api.post('/c3p-p-core/api/ResourceFunction/v4/findNextPriorityReq/')
# #@authenticate
# async def findNextPriorityReq(request:Request):
#     info=await request.json()
#     return c3p_tmf_api.findNextPriorityReq(info)
#
# @c3p_fast_api.api_route('/c3p-p-core/api/ResourceFunction/v4/monitor/')
# #@authenticate
# async def ResourceFunction(request:Request):
#     info =await request.json()
#     return c3p_tmf_api.ResourceFunction(info)
#
# """
# Discovery for an external applications
# """
# @c3p_fast_api.post('/c3p-p-core/api/ext/discovery/')
# async def extDiscovery(request:Request):
#     # c3p_lib.dbConnection()
#     ipAddrList = []
#     disReturn = []
#     if request.method == 'POST':
#
#         content = await request.json()
#         if (content['discoveryType'] == 'ipRange'):
#             if ((content['ipType']) == 'ipv4'):
#                 if (content['netMask'].split(".")[3] == '254'):
#                     logger.debug('Error - No IPs for discovery')
#                     return 'Error - No IPs for discovery'
#
#                 """ get list of ip address in the given subnet """
#
#                 # ipAddrList=getAllIPsForDiscovery(content["startIp"], content["netMask"], content["endIp"])
#                 """ Create a discovery record """
#
#                 disRowInfo = CSDRN.createDiscoveryRecord(content)
#                 # disRowID    = disRowInfo[0]
#                 # disId       = disRowInfo[1]
#                 # disStart    = disRowInfo[2]
#                 rfo_id = disRowInfo[1]
#                 logger.debug("extDiscovery - rfo_id = %s", rfo_id)
#                 """ perform the discovery for each IP and Save the resultant """
#
#                 url = configs.get("Camunda_Engine") + "/decompWorkflow/start"
#                 inp = {}
#                 inp['businessKey'] = rfo_id
#                 inp['variables'] = {"version": {"value": "1.0"}}
#                 data_json = json.dumps(inp)
#                 newHeaders = {"Content-type": "application/json", "Accept": "application/json"}
#                 logger.debug("extDiscovery - test ..... data_json is %s", data_json)
#                 f = requests.post(url, data=data_json, headers=newHeaders)
#                 # print('f :: ', f.json())
#
#                 rhref = configs.get("Python_Application") + '/c3p-p-core/api/ResourceFunction/v4/monitor/?id=' + rfo_id
#                 return jsonable_encoder({"content": request.json, "href": rhref}), status.HTTP_202_ACCEPTED
#
#             elif ((content['ipType']) == 'ipv6'):
#                 discoveryFlag = 'range ipv6'
#                 # print('iprange for ipv6')
#
#             """ *********** for single IP - Device discovery ************* """
#         elif (content['discoveryType'] == 'ipSingle'):
#             if ((content['ipType']) == 'ipv4'):
#                 # print('single for ipv4')
#                 disRowId = []
#                 # Create a discovery record
#
#                 disRowInfo = CSDRN.createDiscoveryRecord(content)
#                 # disRowID = disRowInfo[0]
#                 # disId = disRowInfo[1]
#                 # disStart = disRowInfo[2]
#
#                 rfo_id = disRowInfo[1]
#                 logger.debug("extDiscovery - rfo_id = %s", rfo_id)
#                 """ perform the discovery for each IP and Save the resultant """
#
#                 url = configs.get("Camunda_Engine") + "/decompWorkflow/start"
#                 inp = {}
#                 inp['businessKey'] = rfo_id
#                 inp['variables'] = {"version": {"value": "1.0"}}
#                 data_json = json.dumps(inp)
#                 logger.debug("extDiscovery - Data JSON :: %s", data_json)
#                 newHeaders = {"Content-type": "application/json", "Accept": "application/json"}
#
#                 f = requests.post(url, data=data_json, headers=newHeaders)
#                 # logger.debug('extDiscovery - response :: %s', f.json())
#
#                 rhref = configs.get("Python_Application") + '/c3p-p-core/api/ResourceFunction/v4/monitor/?id=' + rfo_id
#                 return jsonable_encoder({"content": request.json, "href": rhref}), status.HTTP_202_ACCEPTED
#
#             elif ((content['ipType']) == 'ipv6'):
#                 discoveryFlag = c3pdefination(content)
#     else:
#         logger.debug('extDiscovery - else block')
#         return 'Inside Discovery GET Method'
# """ End discovery for external applications """
#
# @c3p_fast_api.post('/c3p-p-core/api/discovery/')
# # @cross_origin(origin='http://10.62.0.42:8080')
# async def discovery(request:Request,):
#     # c3p_lib.dbConnection()
#     ipAddrList = []
#     if request.method == 'POST':
#         content = await request.json()
#         if (content['discoveryType'] == 'ipRange'):
#             if ((content['ipType']) == 'ipv4'):
#                 if (content['netMask'].split(".")[3] == '254'):
#                     logger.debug('discovery - Error - No IPs for discovery')
#                     return 'Error - No IPs for discovery'
#
#                 """ get list of ip address in the given subnet """
#                 ipAddrList = getAllIPsForDiscovery(content["startIp"], content["netMask"], content["endIp"])
#                 """ Create a discovery record """
#                 rOut = CSDRN.resultDiscoveryReconciliation(content,
#                                                            ipAddrList)  # single call to perform Discovery and Reconciliation
#                 return jsonable_encoder(rOut)
#
#             elif ((content['ipType']) == 'ipv6'):
#                 discoveryFlag = 'range ipv6'
#                 # print('iprange for ipv6')
#
#                 """ *********** for single IP - Device discovery ************* """
#         elif (content['discoveryType'] == 'ipSingle'):
#             if ((content['ipType']) == 'ipv4'):
#                 # print('single for ipv4')
#                 ipAddrList = [content["startIp"], ]
#                 rOut = CSDRN.resultDiscoveryReconciliation(content,
#                                                            ipAddrList)  # single call to perform Discovery and Reconciliation
#
#                 return jsonable_encoder(rOut)
#             elif ((content['ipType']) == 'ipv6'):
#                 discoveryFlag = c3pdefination(content)
#         elif (content['discoveryType'] == 'ipList'):
#             if ((content['ipType']) == 'ipv4'):
#                 ipAddrList = content["startIp"]
#                 rOut = CSDRN.resultDiscoveryReconciliation(content,
#                                                            ipAddrList)  # single call to perform Discovery and Reconciliation
#
#                 return jsonable_encoder(rOut)
#             elif ((content['ipType']) == 'ipv6'):
#                 discoveryFlag = c3pdefination(content)
#     else:
#         logger.debug('discovery - Inside else block')
#         return 'Inside Discovery GET Method'
#
# @c3p_fast_api.api_route('/nav_to.do/')
# def snow_request():
#     logger.info('snow_request - Received snow request')
#     return 'Pass'
#
# @c3p_fast_api.api_route('/user/<username>')
# def profile(username):
#     logger.info('profile - inside user :: %s', username)
#     return '{}\'s profile'.format(escape(username))
#
# @c3p_fast_api.api_route('/login', methods=['GET', 'POST'])
# def login(request:Request):
#     if request.method == 'POST':
#         logger.info('login - Inside Post Method')
#         return { "discovery": "post", "type": "range", "ip": "10.0.0.1" }
#     else:
#         logger.info('login - Inside GET Method')
#         return 'show the login form'
#
# """ Call Service Now hosted API to check the connectivity """
#
# @c3p_fast_api.post('/c3p-p-core/api/calltoservicenow/')
# def calltoservicenow():
#     url=configs.get("SNow_C3P_Instance")+"/api/now/table/u_cmdb_netgear_import"
#     inp={}
#     inp['u_id']= 521
#     inp['u_auto_status']= "true"
#     data_json = json.dumps(inp)
#     logger.debug('calltoservicenow - data_json - %s', data_json)
#     newHeaders={"Content-type":"application/json","Accept":"application/json", }
#     f =requests.post(url,data=data_json, headers=newHeaders, auth=HTTPBasicAuth(configs.get("SNow_C3P_User"), configs.get("SNow_C3P_Password")))
#     logger.debug('calltoservicenow - Response :: %s', f.json())
#     return f.json()
#
# @c3p_fast_api.post('/c3p-p-core/api/testRequest')
# #@authenticate
# async def TestRequest(request:Request):
#     data = await request.json()
#     logger.info('TestRequest - start')
#     return c3p_tmf_api.datatodb(None,request,data)
#
#
# """ For Backup Request For Device : /c3p-p-core/api/backupRequest"""
# """ Author: Dhanshri Mane"""
# """ Date: 21/1/2021"""
#
# @c3p_fast_api.post('/c3p-p-core/api/backupRequest' )
# #@authenticate
# async def backUpRequest(request:Request):
#     logger.info('backUpRequest - start')
#     data = await request.json()
#     return c3p_tmf_api.datatodb(None,request,data)
#
# @c3p_fast_api.api_route('/hello/')
# @c3p_fast_api.api_route('/hello/<name>')
# def hello(name=None):
#     return render_template('hello.html', name=name)
#
# def getAllIPsForDiscovery(sIP, netMask, eIP):
#     rsIP = sIP
#     seIP = []
#     masks = {'255': 1, '254': 2, '252': 4, '248': 8, '240': 16, '224': 32, '192': 64, '128': 128, '0': 255}
#     ipAddrRange = []
#     # prepare the subnets request
#     while (ipaddress.ip_address(sIP) <= ipaddress.ip_address(eIP)):
#         subnets = [str(sIP) + "/" + str(netMask)]
#         ipList = c3p_lib.calculate_subnets(subnets)
#         for m in range(len(ipList['ipaddrs'])):
#             sIP = ipaddress.ip_address(ipList['ipaddrs'][0])
#             ipAddrRange.append(ipList['ipaddrs'][m])
#
#         sIP = ipaddress.ip_address(sIP) + masks[netMask.split(".")[3]]
#
#     for m in range(len(ipAddrRange)):
#         cIP = ipAddrRange[m]
#         # print('cIP : ', cIP)
#         if ((ipaddress.ip_address(cIP) >= ipaddress.ip_address(rsIP)) and (
#                 ipaddress.ip_address(cIP) <= ipaddress.ip_address(eIP))):
#             # print('selected ip : ', cIP)
#             seIP.append(cIP)
#         else:
#             logger.debug('getAllIPsForDiscovery - reject ip : %s', cIP)
#     # print('seIP Type:', type(seIP))
#     return seIP
#
#     # ******************** preparing return output in JSON format *********************
#
# def resultInJsonFormat(rdID, rdSt, rRes):
#     # print('inside formattor', rRes)
#     rDisStatus = rRes[0]
#     rDisStart = rdSt
#     rDisEnd = rRes[1]
#
#     # print(rdID, rDisStatus,rDisStart,rDisEnd)
#     rOut = {"DisID ": rdID, "DisStatus": rDisStatus, "DisStart": rDisStart, "DisEnd": rDisEnd}
#     # print('rOut =', rOut, type(rOut))
#     # [('10.62.0.27', 'public', 23, 9, ' ', 'Cisco', 'PNF', '1', 'N', 'N', '510', '2020-09-13 14:01:24', '2020-09-13 14:01:31', 'C3P_CSR_Router1', 'admin')]
#     return rOut
#
# def hello_world():
#     return 'Hello C3P'
#
#
# """ To perform : Network Test throughput : /c3p-p-core/api/throughput/"""
# """ Author: Ruchita Salvi"""
# """ Date: 13/1/2021"""
#
# @c3p_fast_api.post('/c3p-p-core/api/throughput/')
# async def throughput(request:Request):
#     logger.info('throughput - start')
#     content = await request.json()
#     thrResult = c3p_lib.performThroughput(content)
#     #print('throughput Return :: ', thrResult )
#     return thrResult
#
# """ To perform :Parameterized Ping Test endpoint : /c3p-p-core/api/PingTest/"""
# """ Author: Ruchita Salvi"""
# """ Date: 15/1/2021"""
# @c3p_fast_api.post('/c3p-p-core/api/ping/')
# async def parameterizedPingTest(request:Request):
#     print('inside PingTest')
#     content = await request.json()
#     pingResult = networkTests.performPing(content)
#     return jsonable_encoder(pingResult)
#
# """ To perform :Latency endpoint : /c3p-p-core/api/latency/"""
# """ Author: Ruchita Salvi"""
# """ Date: 15/1/2021"""
# @c3p_fast_api.post('/c3p-p-core/api/latency/')
# async def performLatency(request:Request):
#     logger.info('performLatency - start')
#     content = await request.json()
#     result = networkTests.performLatency(content)
#     return jsonable_encoder(result)
#
# """ To perform :Frameloss endpoint : /c3p-p-core/api/frameloss/"""
# """ Author: Ruchita Salvi"""
# """ Date: 15/1/2021"""
# @c3p_fast_api.post('/c3p-p-core/api/frameloss/')
# async def performFrameloss(request:Request):
#     logger.info('performFrameloss - start')
#     content = await request.json()
#     result = networkTests.performFrameloss(content)
#     return jsonable_encoder(result)
#
# """ To perform : VNF Backup endpoint : /c3p-p-core/api/backupVNF/"""
# """ Author: Rahul Tiwari"""
# """ Function to perform backup when device type is VNF"""
# """ Date: 08/2/2021"""
# @c3p_fast_api.post('/c3p-p-core/api/backupVNF/')
# async def backupVNF(request:Request):
#     logger.info('performFrameloss - start')
#     content = await request.json()
#     logger.info('inside backup vnf -content-> %s',content)
#     response= c3p_lib.backupVNF(content["ip"],content["hostname"],content["source"], content["port"], content["requestId"], content["stage"], content["version"])
#     return response
#
# @c3p_fast_api.post('/c3p-p-core/api/ipCalculator/')
# async def ipCalculator(request:Request):
#     logger.info('ipCalculator - start')
#
#     ''' Caluclate IPs valid between Start and End IP witing given Subnet Mask.
#         If EndIP is not provided calculate it based on Subnet Mask
#         input parameters ip, mask, there will not be end IP
#         In return program will send back ip, mask and list of all valid ips
#     '''
#     content = await request.json()
#     masks = {'255': 1, '254': 2, '252': 4, '248': 8, '240': 16, '224': 32, '192': 64, '128': 128, '0': 255}
#     logger.debug("ipCalculator - IP content :: %s", content["ip"].split(".")[3])
#     eeIP = content["ip"].split(".")[3]
#     eM = masks[content["mask"].split(".")[3]]
#     logger.debug("ipCalculator -  eM ::%s ", eM)
#
#     if ((int(eeIP) + int(eM)) > 255):
#         eIP = ipaddress.ip_address(content["ip"]) - int(eeIP) + 255
#     else:
#         eIP = ipaddress.ip_address(content["ip"]) + masks[content["mask"].split(".")[3]]
#
#     logger.debug("ipCalculator - Calucated eIP is :: %s", eIP)
#     exclusionList = []
#     sIp = c3p_lib.getAllIPsForDiscovery(content["ip"], content["mask"], eIP, exclusionList)
#     result = {"startip": content["ip"], "mask": content["mask"], "endip": str(eIP), "seIP": sIp}
#     logger.debug("ipCalculator - result - %s", result)
#
#     return result
#
# """ To perform : GET of tree view of features from Mongo : /c3p-p-core/api/yang/features"""
# """ Author: Ruchita Salvi"""
# """ Date: 18/3/2021"""
# @c3p_fast_api.post('/c3p-p-core/api/yang/treeview')
# async def yangFeatures(request:Request):
#     json_object={}
#     result = dict()
#     content = await request.json()
#     filename= content["filename"]
#     result["featureTree"]=yangExtractor.getTreeViewFeatures(filename)
#     json_object = json.dumps(result, indent = 4)
#     return json_object
#
# """ To perform : GET of yang file from Mongo : /c3p-p-core/api/yang"""
# """ Author: Ruchita Salvi"""
# """ Date: 18/3/2021"""
# @c3p_fast_api.post('/c3p-p-core/api/yang')
# async def yangfiles(request:Request):
#     json_object={}
#     result = dict()
#     content = await request.json()
#     filename= content['filename']
#     result["yangFile"]=yangExtractor.getYang(filename)
#     json_object = json.dumps(result, indent = 4)
#     return json_object
#
# """ To Save Netconf Template Details """
# """ endpoint : /c3p-p-core/api/templateManagment"""
# """ Author: Dhanshri Mane """
# """ Date: 17/3/2021"""
# @c3p_fast_api.post('/c3p-p-core/api/templateManagment')
# async def templateManagment(request:Request):
#     logger.info('inside Template Managment')
#     content = await request.json()
#     templateObj = TemplateManagment()
#     result = templateObj.templateManagmentDatatoDB(content)
#     return jsonable_encoder(result)
#
# """ To perform :Add job in scheduler jobstore : /c3p-p-core/api/schedular"""
# """ Author: Ruchita Salvi"""
# """ Date: 16/4/2021"""
# @c3p_fast_api.post('/c3p-p-core/api/schedular')
# async def schedulework(request:Request):
#     logger.info('inside schedular')
#     data = await request.json()
#     job = ""
#     job = c3pscheduler.addJobMtd(data,scheduler)
#     return "job details: %s" % job
#
# """ To perform :Create topology map : /c3p-p-core/api/topology/map"""
# """ Author: Ruchita Salvi"""
# """ Date: 16/4/2021"""
# @c3p_fast_api.post('/c3p-p-core/api/topology/map')
# async def topology(request:Request):
#     logger.info('APP :: Topology')
#     data = await request.json()
#     # Changes by Ruchita for seperation of VLT code in seperate method to loop over devices
#     if (data['operation'] == 'RLT'):
#         results = c3p_topology.create_logical_topology(data)
#     elif (data['operation'] == 'VLT'):
#         results = c3p_topology.show_logical_topology(data)
#     return jsonable_encoder(results)
#
#
# @c3p_fast_api.api_route('/', methods=('GET', 'POST'))
# def Hello():
#      return "HELLO!! Welcome to C3P FastApi"
#
# # # ###################################
# # # # OAuth2.0 Related code
# # # ###################################
# # async def current_user(request:Request):
# #      #if 'id' in request.session:
# #     #uid = request.session["id"]
# #     uid = request.session.get("id", None)
# #     return User.query.get(uid)
# #      #return None
# #
# # def split_by_crlf(s):
# #      return [v for v in s.splitlines() if v]
# #
# #
# # @c3p_fast_api.api_route('/', methods=('GET', 'POST'))
# # #@c3p_fast_api.middleware("http")
# # def home(request:Request):
# #     if request.method == 'POST':
# #         username = request['username']
# #         user = User.query.filter_by(username=username).first()
# #         if not user:
# #             user = User(username=username)
# #             db.session.add(user)
# #             db.session.commit()
# #         request.session['id'] = user.id
# #         # if user is not just to log in, but need to head back to the auth page, then go for it
# #         next_page = request['next']
# #         if next_page:
# #             return RedirectResponse(next_page)
# #         return RedirectResponse('/')
# #     #change i have to make in acc02
# #     user = current_user(request)
# #     ##############################
# #     if user:
# #         clients = OAuth2Client.query.filter_by(user_id=user.id).all()
# #     else:
# #         clients = []
# #
# #     return render_template('home.html', user=user, clients=clients)
# #
# # @c3p_fast_api.api_route('/logout')
# # def logout(request:Request):
# #     del request.session['id']
# #     return RedirectResponse('/')
# #
# # @c3p_fast_api.api_route('/create_client', methods=('GET', 'POST'))
# # def create_client(request:Request):
# #     user = current_user(request)
# #     if not user:
# #         return RedirectResponse('/')
# #     if request.method == 'GET':
# #         return render_template('create_client.html')
# #
# #     client_id = gen_salt(24)
# #     client_id_issued_at = int(time.time())
# #     client = OAuth2Client(
# #         client_id=client_id,
# #         client_id_issued_at=client_id_issued_at,
# #         user_id=user.id,
# #     )
# #
# #     form = request
# #     client_metadata = {
# #         "client_name": form["client_name"],
# #         "client_uri": form["client_uri"],
# #         "grant_types": split_by_crlf(form["grant_type"]),
# #         "redirect_uris": split_by_crlf(form["redirect_uri"]),
# #         "response_types": split_by_crlf(form["response_type"]),
# #         "scope": form["scope"],
# #         "token_endpoint_auth_method": form["token_endpoint_auth_method"]
# #     }
# #     client.set_client_metadata(client_metadata)
# #
# #     if form['token_endpoint_auth_method'] == 'none':
# #         client.client_secret = ''
# #     else:
# #         client.client_secret = gen_salt(48)
# #
# #     db.session.add(client)
# #     db.session.commit()
# #     return RedirectResponse('/')
# #
# # @c3p_fast_api.api_route('/c3p-p-core/api/oauth/authorize', methods=['GET', 'POST'])
# # def authorize(request:Request):
# #     user = current_user(request)
# #     # if user log status is not true (Auth server), then to log it in
# #     if not user:
# #         return RedirectResponse(url_for('website.routes.home', next=request.url))
# #     if request.method == 'GET':
# #         try:
# #             grant = authorization.validate_consent_request(end_user=user)
# #         except OAuth2Error as error:
# #             return error.error
# #         return render_template('authorize.html', user=user, grant=grant)
# #     if not user and 'username' in request.form:
# #         username = request.form('username')
# #         user = User.query.filter_by(username=username).first()
# #     if request.form('confirm'):
# #         grant_user = user
# #     else:
# #         grant_user = None
# #     return authorization.create_authorization_response(grant_user=grant_user)
# #
# # @c3p_fast_api.api_route('/c3p-p-core/api/oauth/token', methods=['POST'])
# # #@cross_origin(origin='*')
# # def issue_token():
# #     return authorization.create_token_response()
# #
# # @c3p_fast_api.post('/c3p-p-core/api/oauth/revoke')
# # def revoke_token():
# #     return authorization.create_endpoint_response('revocation')
# #
# #
# # # #commented out for fastapi error
# # # @c3p_fast_api.api_route('/c3p-p-core/api/me')
# # # #@require_oauth('profile')
# # # def api_me():
# # #     user = current_token.user
# # #     return jsonable_encoder(id=user.id, username=user.username)
#
# @c3p_fast_api.api_route('/c3p-p-core/api/test')
# @require_oauth('profile')
# def api_test():
#     return jsonable_encoder(id='120', username='Test User')
#
# """ To perform : Generate pdf report endpoint : /c3p-p-core/api/generatePdf/"""
# """ Author: Rahul Tiwari"""
# """ Function to perform generate pdf report"""
# """ Date: 08/6/2021"""
# @c3p_fast_api.post('/c3p-p-core/api/generatePdf/')
# async def generatePDFReport(request:Request):
#     logger.info('generatePDFReport - start')
#     content = await request.json()
#     logger.info('inside generatePDFReport -content-> %s',content)
#     response= c3p_lib.generatePDFReport(content["input"], content["output"])
#     return response
#
# """ To perform : Netconf ROC Edit : /c3p-p-core/api/netconfedit/"""
# """ Author: Ruchita Salvi"""
# """ Function to perform generate pdf report"""
# """ Date: 08/6/2021"""
# @c3p_fast_api.post('/c3p-p-core/api/netconfedit/')
# async def netconfEdit(request:Request):
#     logger.info('netconf edit rpc - start')
#     content = await request.json()
#     logger.info('netconf edit rpc -content-> %s',content)
#     response= netconf.editConf(content)
#     return response
#
# """ To perform : Test Netconf : /c3p-p-core/api/netconftest/"""
# """ Author: Rahul Tiwari"""
# """ Function to perform test getrpc"""
# """ Date: 08/6/2021"""
# @c3p_fast_api.post('/c3p-p-core/api/netconftest/')
# async def performTestConf(request:Request):
#     logger.info('netconf test getrpc - start')
#     content = await request.json()
#     logger.info('netconf test getrpc -content-> %s',content)
#     response= netconf.performTestConf(content)
#     return response
#
# """ To perform : Test Netconf : /c3p-p-core/api/configdelta/"""
# """ Author: Ruchita Salvi"""
# """ Function to find delta if present in two text files"""
# """ Date: 07/7/2021"""
# @c3p_fast_api.post('/c3p-p-core/api/configdelta/')
# async def performconfigdelta(request:Request):
#     logger.info('configdelta - start')
#     content = await request.json()
#     logger.info('configdelta -content-> %s',content)
#     response= c3p_lib.computeDeltaInInputs(content["file1"], content["file2"])
#     return response
#
#
# """ To perform : Physical topology : /c3p-p-core/api/ptopology/"""
# """ Author: Ruchita Salvi"""
# """ Function to generate physical"""
# """ Date: 22/07/2021"""
# @c3p_fast_api.post('/c3p-p-core/api/physicaltopology/')
# async def physicaltopology(request:Request):
#     response = ""
#     logger.info('physicaltopology - start')
#     content = await request.json()
#     #print("input",content)
#     logger.info('physicaltopology -content-> %s',content)
#     response= phyTopo.triggerPhysicalTopology(content)
#     return response
#
# """ To perform : Physical topology : /c3p-p-core/api/physicaltopologycsv/"""
# """ Author: Ruchita Salvi"""
# """ Function to generate physical topologys csv file"""
# """ Date: 22/07/2021"""
# @c3p_fast_api.post('/c3p-p-core/api/physicaltopologycsv/')
# async def physicaltopologycsv(request:Request):
#     response = []
#     logger.info('physicaltopologycsv - start')
#     content = await request.json()
#     #print("input",content)
#     logger.info('physicaltopologycsv -content-> %s',content)
#     response= phyTopo.createCSV(content)
#     return jsonable_encoder({'output': response})
#
# """ To perform : Inset file in mongo  : /c3p-p-core/api/mongo/insert/file"""
# """ Author: Ruchita Salvi"""
# """ Function to insert file in mongo db, this is a generic standalone function and can be resued"""
# """ Date: 22/07/2021"""
# @c3p_fast_api.post('/c3p-p-core/api/mongo/insert/file')
# def mongoinsert(request:Request):
#     response = ""
#     logger.info('mongoinsert - start')
#     content = request.json()
#     #print("input",content)
#     logger.info('mongoinsert -content-> %s',content)
#     response= phyTopo.mongofileinsert(content)
#     return response
#
# """ To perform : GET of  file from Mongo : /c3p-p-core/api/file"""
# """ Author: Ruchita Salvi"""
# """ Function to get file from mongo db, this is a generic standalone function and can be resued"""
# """ Date: 22/07/2021"""
# @c3p_fast_api.post('/c3p-p-core/api/file')
# async def getFileFromMongo(request:Request):
#     json_object={}
#     result = dict()
#     content = await request.json()
#     result["file"]=yangExtractor.getScript(content)
#     json_object = json.dumps(result, indent = 4)
#     return json_object
#
# """ To perform : GET of  file from Mongo : /c3p-p-core/api/file"""
# """ Author: Ruchita Salvi"""
# """ONLY FOR TESTING PUROSE"""
# @c3p_fast_api.post('/c3p-p-core/api/createLogicalTopology')
# async def createLogicalTopology(request:Request):
#     json_object=""
#     content = await request.json()
#     json_object=c3p_topology.create_logical_topology(content)
#     return json_object
#
# """ To perform :Update Device Role after Discover/Customer Onboarding"""
# """ Author: Dhanshri Mane"""
# """ Date: 9/8/2021"""
# @c3p_fast_api.post('/c3p-p-core/api/updateDevieRole')
# async def updatedeviceRole(request:Request):
#     response = dict()
#     content = await request.json()
#     hostName = content['hostName']
#     ipAddress = content['ipAddress']
#     response['message'] = CSDRN.setDeviceRole(hostName,ipAddress)
#     return response
#
#
# # if __name__ == '__main__':
# #   app.run(debug=True, threaded = True, port = 5000, host="0.0.0.0")
#
# @c3p_fast_api.post('/c3p-p-core/api/configDifference/')
# async def performconfigDifference(request:Request):
#     logger.info('configDifference - start')
#     content =await request.json()
#     logger.info('configDifference -content-> %s', content)
#     response = c3p_lib.computeConfigDifferenceCount(content["file1"], content["file2"])
#     return response
#
# """" To perform : GET of  IP pool ranges from ip pool range management : /c3p-p-core/api/ippool"""
# """ Author: Mahesh"""
# """Date: 24/8/2021"""
# @c3p_fast_api.get('/c3p-p-core/api/getIpPoolRanges')
# def getIpPoolRanges():
#         poolId=getPoolId()
#         return jsonable_encoder(poolId)
#
# """ To perform : GET pool id and ip from host ip management : /c3p-p-core/api/ipallocate"""
# """ Author: Mahesh"""
# """Date: 24/8/2021"""
# @c3p_fast_api.api_route('/c3p-p-core/api/ipToAllocate',methods=['POST','GET'])
# async def ipToAllocate(request:Request):
#     if request.method == 'POST':
#         content =await request.json()
#         poolId=content['poolId']
#         ip=checkHostIp(poolId)
#         return jsonable_encoder(ip)
#
# """ To perform : update the status in host ip management and ip pool range  : /c3p-p-core/api/status"""
# """ Author: Mahesh"""
# """Date: 24/8/2021"""
# @c3p_fast_api.post('/c3p-p-core/api/updateHostStatus')
# async def updateHostStatus(request:Request):
#     if request.method == 'POST':
#         content =await request.json()
#         myData=allocateHostIp(content)
#         return jsonable_encoder(myData)
#
# @c3p_fast_api.post('/c3p-p-core/api/templateComparison')
# async def performTemplateDifference(request:Request):
#     logger.info('templateComparison - start')
#     content =await request.json()
#     logger.info('templateComparison -content-> %s',content['templates'])
#     response= TemplateComparison.computeTemplateDifference(content['templates'])
#     return response
#
# @c3p_fast_api.post('/c3p-p-core/api/content/comparison')
# async def performDifference(request:Request):
#     logger.info('comparison - start')
#     content =await request.json()
#     logger.info('comparison -content-> %s',content['inputs'])
#     response= c3p_lib.computeDifference(content['inputs'])
#     return response
#
# ####################################################
# #Chatbot app
# ###################################################
# #comment for testing
# # @c3p_fast_api.post('/c3p-p-core/chatbot/getData')
# # async def getBotData(request:Request):
# #     content =await request.json()
# #     return getbotresponse(content)
#
# """ To perform : Deploye the instance in openstack"""
# @c3p_fast_api.post('/c3p-p-core/api/deploy/instance')
# async def createInstance(request:Request):
#     content =await request.json()
#     return deployInstance(content['folderPath'])
#
# """ To perform : ID generation endpoint : /c3p-p-core/api/generateId/"""
# """ Author: Rahul Tiwari"""
# """ Function to perform id generation"""
# """ Date: 12/01/2022"""
# @c3p_fast_api.post('/c3p-p-core/core/generateId')
# async def generateId(request:Request):
#     logger.info('generateId - start')
#     content =await request.json()
#     logger.info('inside idGenerate -content-> %s',content)
#     response= c3p_lib.generateId(content["sourceSystem"],content["requestingPageEntity"],content["requestType"], content["requestingModule"])
#     return response
#
#
# """ To perform : Deploye the stack in openstack"""
# @c3p_fast_api.post('/c3p-p-core/api/openstack/deploy/stack')
# async def createStack(request:Request):
#     content =await request.json()
#     logger.info('inside openstack -content-> %s',content)
#     return deployStack(template_id=content['templateId'],stackName=content['stack_name'],parameters=content)
#
# """ To perform : Deploye the MCC in openstack"""
# @c3p_fast_api.post('/c3p-p-core/api/openstack/deploy/instancemcc')
# async def computeInstance(request:Request):
#     content =await request.json()
#     logger.info('openstack computeinstanceMcc -content-> %s',content)
#     return c3p_Compute.computeInstanceMcc(content)
#
# """ To perform : Deploye the diskResize in gcp"""
# @c3p_fast_api.post('/c3p-p-core/api/gcp/deploy/diskResize')
# async def resizeDisk(request:Request):
#     content =await request.json()
#     return c3p_gcp_compute.disksResize(content)
#
# """ To perform : Deploye the setMachineType in gcp"""
# @c3p_fast_api.post('/c3p-p-core/api/gcp/deploy/setMachineType')
# async def machineType(request:Request):
#     content =await request.json()
#     return c3p_gcp_compute.setMachineType(content)
#
# """ To perform : Deploye the volumeResize in openstack"""
# @c3p_fast_api.post('/c3p-p-core/api/openstack/deploy/volumeResize')
# async def resizeVolume(rquest:Request):
#     content =await request.json()
#     return c3p_Compute.volumeResize(content)
#
# """ To perform : Deploye the  resizeFlavor in openstack"""
# @c3p_fast_api.post('/c3p-p-core/api/openstack/deploy/resizeFlavor')
# async def flavourResize(request:Request):
#     content =await request.json()
#     print(content)
#     return c3p_Compute.resizeFlavor(content)
#
# """ To perform :execution of ping test"""
# @c3p_fast_api.post('/c3p-p-core/api/pingflow/')
# async def pingflow(request:Request):
#     pingInfo =await request.json()
#     return c3p_ip_ping.pingTestflow(pingInfo)
#
# @c3p_fast_api.get('/c3p-p-core/api/ResourceSpec/v41/<id>/')
# # @authenticate
# def resourceSpecId(id,request:Request):
#     if request.method == 'GET' :
#         id=request.path_params["id"]
#         args = request.query_params
#         return get_apiv2.listResourceSpec(str(id),args)
#
# @c3p_fast_api.get('/c3p-p-core/api/ResourceSpec/v41/')
# # @authenticate
# def resourceSpec(request:Request):
#     if request.method == 'GET' :
#         args = request.query_params
#         return get_apiv2.listResourceSpec(None,args)
#
# @c3p_fast_api.get('/c3p-p-core/api/PhysicalResourceSpec/v41/')
# # @authenticate
# def physicalResourceSpec(request:Request):
#     if request.method == 'GET' :
#         args = request.query_params
#         return get_apiv2.listPhysicalResourceSpec(None,args)
#
# @c3p_fast_api.get('/c3p-p-core/api/LogicalResourceSpec/v41/<id>/')
# # @authenticate
# def logicalresourceSpecId(id,request:Request):
#     if request.method == 'GET' :
#         args = request.query_params
#         return get_apiv2.listLogicalResourceSpec(str(id),args)
#
# @c3p_fast_api.get('/c3p-p-core/api/LogicalResourceSpec/v41/')
# # @authenticate
# def logicalresourceSpec(request:Request):
#     if request.method == 'GET' :
#         args = request.query_params
#         return get_apiv2.listLogicalResourceSpec(None,args)
#
# @c3p_fast_api.get('/c3p-p-core/api/ResourceSpecRelationship/v41/')
# # @authenticate
# def resourceSpecRelationship(request:Request):
#     if request.method == 'GET' :
#         args = request.query_params
#         return get_apiv2.listResourceSpecRelationship(None)
#
# @c3p_fast_api.get('/c3p-p-core/api/ResourceSpecRelationship/v41/<id>/')
# # @authenticate
# def resourceSpecRelationshipId(request:Request):
#     if request.method == 'GET' :
#         id = request.path_params
#         args = request.query_params
#         return get_apiv2.listResourceSpecRelationship(str(id))
#
# @c3p_fast_api.post('/c3p-p-core/api/ResourceFunction/v4/milestonestatus/')
# #@authenticate
# async def respnc_milestone(request:Request):
#     content =await request.json()
#     respnc=c3p_tmf_api.milestoneStatus(content)
#     print("END")
#     return respnc,status.HTTP_200_OK
