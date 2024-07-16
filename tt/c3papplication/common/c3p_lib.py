import difflib
import datetime
import ipaddress
import json
import logging
import mysql.connector
import pdfkit
import random
import os

from icmplib import traceroute
from lxml.html import fromstring
from ncclient import manager
from pysnmp.entity.rfc3413.oneliner import cmdgen
from pythonping import ping
from markupsafe import escape
from c3papplication.common import c3p_network_tests as networkTests
from c3papplication.common import Connections, ipcalc
from c3papplication.discovery import c3p_snmp_disc_rec_new as CSDRN
from c3papplication.ipmanagement import c3p_jumpssh

# mydb = Connections.create_connection()
# mycursor = mydb.cursor(buffered=True)

# def dbConnection():
#     try:
#         # mydb = mysql.connector.connect(
#         #         host="10.62.0.42",
#         #         port="3306",
#         #         user="root",  
#         #         password="root@1234",
#         #         database="c3pdbschema"
#         # )
#         if mydb.is_connected():
#             db_Info = mydb.get_server_info()
#             print("Connected to MySQL Server version ", db_Info)
#     except Error as e:
#         print("Error while connecting to MySQL", e)

logger = logging.getLogger(__name__)

# ************************ Device Discovery  ******************************
""" Perform Validation Test as per the request using OIDs defined in Master OID Table under 
PreTest Catagolry
"""


def performTest(reqTest):
    mydb = Connections.create_connection()
    mycursor = mydb.cursor(buffered=True)

    mgmtip = reqTest['reqTestMgmtIp']
    community = reqTest['reqTestCommunity']

    reqTestRes = []
    # myReqTest = mydb.cursor(buffered=True)

    sql = "SELECT oid_m_no, oid_m_display_name FROM c3p_m_oid_master_info where oid_m_category = %s and oid_m_network_type = %s and oid_m_scope_flag ='Y'"

    try:
        mycursor.execute(sql, (reqTest['reqTestCategory'],reqTest['reqTestNType'],))
        myReqTest = mycursor.fetchall()
    except mysql.connector.errors.ProgrammingError as err:
        logger.error('performTest - Error -%s', err)
        # mycursor.close()
        return ('Error : Failed')

    """ get all OIDs from Master OID table to perfrom Test """

    for r in myReqTest:
        reqOID = r[0]
        reqDis = r[1]

        # print('OID :: ', r[0], 'Display :: ', r[1])

        generator = cmdgen.CommandGenerator()
        comm_data = cmdgen.CommunityData('server', community, 1)  # 1 means version SNMP v2c
        transport = cmdgen.UdpTransportTarget((mgmtip, 161))

        real_fun = getattr(generator, 'getCmd')
        res = (errorIndication, errorStatus, errorIndex, varBinds) \
            = real_fun(comm_data, transport, reqOID)

        if not errorIndication is None or errorStatus is True:
            # print ("Error: %s %s %s %s" )
            print('%s at %s' % (errorStatus, errorIndex and varBinds[int(errorIndex) - 1][0] or '?'))
            return ('1')
            # break
        else:
            for varBind in varBinds:  # varBind has type ObjectType
                if (reqDis == 'OS'):
                    reqOSDis = reqDis + reqTest['reqTestNType']
                    resValue = CSDRN.extract_discoveryValue(reqOSDis, varBind[1])
                    logger.debug('performTest - OS :: %s', reqOSDis)
                else:
                    resValue = CSDRN.extract_discoveryValue(reqDis, varBind[1])

                logger.debug('performTest - OID :: %s  Display Name :: %s   Value received :: %s', reqOID, reqDis,
                             varBind[1])
                logger.debug('performTest - Post Extraction :: %s', resValue)

                res = {reqDis: resValue}
                reqTestRes.append(res)

            # print('Test Result ::', reqTestRes)
    # myReqTest.close()
    mydb.close
    return reqTestRes


# def createDiscoveryRecord(disInfo):

#     myDisRec    = mydb.cursor(buffered=True)

#     dT  =''
#     ipT =''


#     disType = disInfo['discoveryType']
#     ipType  = disInfo['ipType']
#     disName = disInfo['discoveryName']
#     sIP     = disInfo['startIp']
#     eIP     = disInfo['endIp']
#     netMask = disInfo['netMask']
#     #disCom  = disInfo['community']
#     disCom_temp  = disInfo['community']
#     sql = "SELECT cr_profile_name FROM c3p_t_credential_management where cr_login_read='"+disCom_temp+"'"
#     print('disCom SQL :: ', sql)
#     mycursor.execute(sql)
#     result = mycursor.fetchone()
#     print('disCom result :: ', result)
#     disCom = ''.join(result)
#     disCby  = disInfo['createdBy']
#     #disSrc  = disInfo['sourcesystem']
#     disSrc  = (lambda: "",lambda : disInfo['sourcesystem'])['sourcesystem' in disInfo.keys()]()
#     disStart= datetime.today().strftime('%Y-%m-%d %H:%M:%S')

#     # logic to generate the discovery id


#     if (disType == 'ipSingle'):
#         dT = 'S'
#     elif(disType == 'ipRange'):
#         dT = 'R'
#     elif(disType == 'import'):
#         dT = 'I'
#     if (ipType == 'ipv4') :
#         ipT = '4'
#     elif(ipType == 'ipv6'):
#         ipT ='6'

#     # prepare the discovery id
#     disStC =disStart.replace("-","")
#     disStC =disStC.replace(":","")
#     disStC =disStC.replace(" ","")
#     disID = 'S'+'D'+dT+ipT+disStC

#     #print('discovert ID : ', disID)

#     # inserting discovery record into a table
#     # SDS4 / SDR4 / SDS6 / SDR6 / SDRI followed by 6 ID

#     sql = "INSERT   INTO c3p_t_discovery_dashboard (dis_dash_id,dis_name,dis_status,dis_ip_type,dis_discovery_type,dis_start_ip,dis_end_ip,dis_network_mask,dis_profile_name,dis_schedule_id,dis_created_date,dis_created_by,dis_import_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
#     insValue = ( disID , disName ,'InProgress', ipType , disType , sIP , eIP , netMask , disCom ,'', disStart, disCby,'')

#     #print('sql =', sql)
#     #print('value = ', insValue)
#     """
#     Create Order Id as the discovery request received from an external system e.g. ServiceNow (SNOW)
#     If request is genereated internally it will not generate the Order Id
#     """
#     if not disSrc == 'c3p-ui':
#         """ Create a Order record in c3p_rf_order rfo_id = disID"""
#         print('disInfo ::', json.dumps(disInfo))
#         sqlOrder = "INSERT INTO c3p_rf_orders (rfo_id,rfo_apibody,rfo_apioperation,rfo_apiurl,rfo_sourcesystem,rfo_apiauth_status,rfo_status,rfo_created_date) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)"
#         insValueOrder = ( disID , json.dumps(disInfo) ,'POST', '/C3P/api/ext/discovery/' , disSrc , 'Pass' , 'InProgress' , disStart)
#         myDisRec.execute(sqlOrder,insValueOrder)
#         print(myDisRec.rowcount, "Order record inserted.")
#         disRowID=myDisRec.lastrowid
#         print('Order id :: ', disRowID)
#         mydb.commit()
#         print('sqlOrder :: ', sqlOrder)
#         print('value Order :: ', insValueOrder)

#     try:
#         myDisRec.execute(sql,insValue)
#         print(myDisRec.rowcount, " discovery record inserted.")
#         disRowID=myDisRec.lastrowid
#         myDisRec.close()
#         mydb.commit()
#         return(disRowID, disID, disStart)
#     except mysql.connector.errors.ProgrammingError as e:
#         print('Error discovery inserting record')
#         myDisRec.close()
#         return('','Error 502',disStart)


# def performDiscovery(sIP,disID,disCom,disCBy,disSource):
#     pD=[]
#     # inside the perform Discovery
#     #print('sIP :', sIP)
#     #print('type of sIP', type(sIP))
#     #print('discovery ID : ', disID)
#     # check the IP address is available in inventory
#     for m in sIP:
#         print(' performDiscovery TempsIP :: ', m)
#         dID = checkIPinInv(m,disID, disCom, disCBy, disSource)
#         pD.append(dID)

#         print('performDiscovery pD :: ', pD)
#         #print('Type dID = ', type(dID))

#         # with concurrent.futures.ProcessPoolExecutor() as executor:
#         #     results = executor.map(checkIPinInv, m,disID, disCom)

#     return pD


# def checkIPinInv(cIP, cdisID,cCom, cCBy, cSource):
#     # Check th e inventory for the IP address, its status, network type and the current status

#     b=(cIP, cdisID,cCom)
#     d=(cIP,cdisID,cCom,'#','#','#','#', cCBy, cSource)
#     c=(cCBy, cSource)
#     myInvChk = mydb.cursor(buffered=True)

#     #print('cIP=', cIP)

#     sql="SELECT d_id, d_vendor,d_vnf_support, d_hostname  FROM c3p_deviceinfo where d_decomm=0 and d_mgmtip='"+str(cIP)+"'"
#     myInvChk.execute(sql)
#     for m in myInvChk:
#         d=b+m+c
#     print('d :', d)
#     myInvChk.close()
#     return d


# **************************    Update the discovery dashboard and Status of each IP table  **********************
# def upDateDisDashandStatus(rDDS):
#     print('inside upDateDisDashandStatus function')
#     myUDDS      = mydb.cursor(buffered=True)
#     disRowID    = 0
#     valDDs      = []
#     disStat     = 'Completed'
#     disUpdate   = datetime.today().strftime('%Y-%m-%d %H:%M:%S')


#     insSql = "INSERT INTO  c3p_t_discovery_status ( ds_ip_addr ,  ds_created_date ,  ds_created_by , ds_updated_date , ds_status ,  ds_comment ,  ds_device_id ,  ds_hostname , ds_device_flag , ds_discovery_id ) VALUES (%s, %s,%s,%s,%s,%s,%s,%s,%s,%s)"

#     for dRe in rDDS:
#         dReVal = ( dRe[0], dRe[11], dRe[14],dRe[12], dRe[10], str(dRe[7])+' : '+str(dRe[8])+' : '+str(dRe[9]), dRe[3],dRe[13], dRe[4], dRe[2])
#         #print('Dis Status', dRe[10])
#         # if (dRe[10] != '200'):
#         #     disStat = 'Failed'
#         disRowID = dRe[2]
#         valDDs.append(dReVal)

#         #print('SQl : ', insSql , valDDs)
#     try:
#         myUDDS.executemany(insSql, valDDs)
#         mydb.commit()
#         print(myUDDS.rowcount, "record inserted.")
#         #myUDDS.close()
#         # return f'{myUDDS.rowcount} record inserted.'
#     except mysql.connector.errors.ProgrammingError as e:
#         print('Inser Error in processing')
#         myUDDS.close()
#         return('Error')

#     updSql = "UPDATE c3p_t_discovery_dashboard SET dis_status ='"+ disStat +"', dis_updated_date = '"+disUpdate+"' WHERE dis_row_id = '"+str(disRowID)+"'"

#     try:
#         myUDDS.execute(updSql)
#         mydb.commit()
#         print(myUDDS.rowcount, "record Updated.")
#         myUDDS.close()
#         # return f'{myUDDS.rowcount} record inserted.'
#     except mysql.connector.errors.ProgrammingError as e:
#         print('Update Error in processing')
#         myUDDS.close()
#         return('502', disUpdate)

#     return (disStat, disUpdate)


# (arg_discoveryType, arg_ipType, arg_mgmtIP, arg_community, arg_discoveryID,
# arg_deviceID, newDevice, arg_vendor, arg_NetworkType, statusGet, statusWalk,
# statusResStep1, statusDiscovery, sDT, datetime.today().strftime('%Y-%m-%d %H:%M:%S'), hostName)

""" Function to perfrom the ping test against any IP Address, uses ICMP protocol  """


def performPingTest(rIP):
    """ setup parameters for the ping test """

    pSize = 40
    pCount = 5
    res = []

    mydb = Connections.create_connection()
    mycursor = mydb.cursor(buffered=True)
    sql = "select d_id,d_connect from c3p_deviceinfo where d_mgmtip = %s"
    logger.debug("common::c3p_lib::performPingTest - sql here :: %s", sql)
    mycursor.execute(sql, (rIP,))
    devinfo = mycursor.fetchone()
    deviceid = devinfo[0]
    if devinfo[1] == "JSSH":
        command = 'ping -c 4 ' + rIP
        logger.debug("inside JSSH command:%s", command)
        jRes = c3p_jumpssh.connectJumpHost(command, deviceid)
        pRes = c3p_jumpssh.jumpPingTestParser(jRes)
    else:
        pResponse = ping(rIP, size=pSize, count=pCount)
        for m in pResponse:
            res.append(str(m).replace(',', ' ', 2))
        pRes = {"ipAddress": rIP, "pingReply": res, "min": pResponse.rtt_min_ms, "avg": pResponse.rtt_avg_ms,
                "max": pResponse.rtt_max_ms}
    mydb.close
    return pRes


""" Function to perfrom the Trace Route against any IP Address, uses ICMP protocol  """


def performTraceRoute(rIP):
    res = []
    mydb = Connections.create_connection()
    mycursor = mydb.cursor(buffered=True)
    sql = "select d_id,d_connect from c3p_deviceinfo where d_mgmtip = %s"
    logger.debug("common::c3p_lib::performPingTest - sql here :: %s", sql)
    mycursor.execute(sql, (rIP,))
    devinfo = mycursor.fetchone()
    deviceid = devinfo[0]
    if devinfo[1] == "JSSH":
        command = 'traceroute -In ' + rIP
        jRes = c3p_jumpssh.connectJumpHost(command, deviceid)
        resTR = c3p_jumpssh.jumpTracerouteParser(jRes, rIP)
    else:
        tRes = traceroute(rIP, max_hops=10, fast=True, timeout=2, count=2)
        last_distance = 0
        logger.debug("common::c3p_lib::traceroute -tRes :: %s", tRes)
        for tr in tRes:
            if last_distance + 1 != tr.distance:
                logger.debug('performTraceRoute - Some rousters are not responding')

            res.append({"Distance(ttl)": tr.distance, "IPaddress": tr.address, "Min": tr.min_rtt, "Avg": tr.avg_rtt,
                        "Max": tr.max_rtt})
            last_distance = tr.distance

        resTR = {"reqIP": rIP, "TraceRoute": res}
    mydb.close
    return resTR


# def extDiscovery(rfo_id):
#     sIP = []
#     eIP = []
#     ipAddrList=[]
#     disReturn=[]
#     mycursor.execute("SELECT dis_row_id FROM c3p_t_discovery_dashboard  where dis_dash_id='"+rfo_id+"'")
#     myresult = mycursor.fetchone()
#     dis_row_id=myresult[0]
#     #dis_row_id=''.join(myresult)

#     mycursor.execute("SELECT rfo_apibody FROM c3p_rf_orders where rfo_id='"+rfo_id+"'")
#     myresult = mycursor.fetchone()
#     print("myresults ::: ", myresult)
#     rfo_apibody = ''.join(myresult)

#     body_dict = json.loads(rfo_apibody).keys()

#     if (rfo_id[0:3] == 'SDS'):
#         for dbd in body_dict:
#             if dbd == "startIp":
#                 print('### dbd', json.loads(rfo_apibody)[dbd])
#                 sIP.append(str(json.loads(rfo_apibody)[dbd]))
#                 print('sIP ::: ', sIP )
#             if dbd == "community":
#                 community = json.loads(rfo_apibody)[dbd]
#             if dbd == "createdBy":
#                 createdBy = json.loads(rfo_apibody)[dbd]
#             if dbd == "sourcesystem":
#                 sourcesystem = json.loads(rfo_apibody)[dbd]

#         # dID=c3p_lib.performDiscovery(sIP,disRowID,community,createdBy,)
#         dID=performDiscovery(sIP,dis_row_id,community,createdBy, sourcesystem)
#         print('ext Discovery dID :: ', dID)
#         #with concurrent.futures.ProcessPoolExecutor() as executor:
#         #    results = executor.map(CSDR.c3pDiscovery,dID)

#         #for result in results:
#         #   disReturn.append(result)

#         uDDS = upDateDisDashandStatus(disReturn)
#         print('ext Discovery uDDS :: ', uDDS)

#     elif (rfo_id[0:3] == 'SDR'):
#         for dbd in body_dict:
#             if dbd == "startIp":
#                 sIP = json.loads(rfo_apibody)[dbd]
#             if dbd == "community":
#                 community = json.loads(rfo_apibody)[dbd]
#             if dbd == "createdBy":
#                 createdBy = json.loads(rfo_apibody)[dbd]
#             if dbd == "netMask":
#                 netMask = json.loads(rfo_apibody)[dbd]
#             if dbd == "endIp":
#                 eIP = json.loads(rfo_apibody)[dbd]
#             if dbd == "sourcesystem":
#                 sourcesystem = json.loads(rfo_apibody)[dbd]

#         ipAddrList=getAllIPsForDiscovery(sIP, netMask, eIP)

#         dID=performDiscovery(ipAddrList,dis_row_id,community,createdBy, sourcesystem)
#         #print('dID :: ', dID)

#     with concurrent.futures.ProcessPoolExecutor() as executor:
#         results = executor.map(CSDR.c3pDiscovery,dID)

#     for result in results:
#         disReturn.append(result)
#         print('discovery range result ::', result)

#     uDDS = upDateDisDashandStatus(disReturn)
#     print('discovery uDDS ::', uDDS)

#     return False

def getAllIPsForDiscovery(sIP, netMask, eIP, exclusionIpList):
    rsIP = sIP
    seIP = []
    masks = {'255': 1, '254': 2, '252': 4, '248': 8, '240': 16, '224': 32, '192': 64, '128': 128, '0': 255}
    ipAddrRange = []
    # prepare the subnets request
    logger.debug('getAllIPsForDiscovery - excluded ip list : %s', exclusionIpList)
    logger.debug('getAllIPsForDiscovery - sIP : %s', sIP)
    logger.debug('getAllIPsForDiscovery - eIP : %s', eIP)
    while (ipaddress.ip_address(sIP) <= ipaddress.ip_address(eIP)):
        logger.debug('getAllIPsForDiscovery - inside while ')
        subnets = [str(sIP) + "/" + str(netMask)]
        logger.debug('getAllIPsForDiscovery - subnets ::%s', subnets)
        ipList = calculate_subnets(subnets)
        logger.debug('getAllIPsForDiscovery - ipList ::%s', ipList)
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
            if not exclusionIpList:
                seIP.append(cIP)
            else:
                for item in exclusionIpList:
                    if (item == cIP):
                        logger.debug('getAllIPsForDiscovery - excluded ip : %s', cIP)
                    else:
                        seIP.append(cIP)
        else:
            logger.debug('getAllIPsForDiscovery - reject ip : %s', cIP)
    # print('seIP Type:', type(seIP))
    return seIP


# def sendDiscoveryData(rfo_id):
#     print('Inside sendDiscoveryData', rfo_id)
#     json_data = {}
#     host_data = []
#     fork_data = []

#     mycursor.execute("SELECT dis_row_id FROM c3p_t_discovery_dashboard  where dis_dash_id='"+rfo_id["SO_number"]+"'")
#     dis_row_id = mycursor.fetchone()[0]
#     print('dis_row_id :: ', dis_row_id)
#     mycursor.execute("SELECT hdr_ip_address, device_id, hdr_oid_no, hdr_discovered_value, hdr_discovery_id FROM c3p_t_host_discovery_result where hdr_discovery_id='" + str(dis_row_id) + "'")
#     row_header = [x[0].replace('hdr_','') for x in mycursor.description]
#     hostData = mycursor.fetchall()

#     for m in hostData:
#         # print('m .... ', m[4])
#         # if m[4] == dis_row_id:
#         # print('inside ..... ###')
#         ml = list(m)
#         ml[4] = rfo_id["SO_number"]
#         m = tuple(ml)
#         # print('m .... ', m)
#         host_data.append(dict(zip(row_header,m)))

#     json_data['host'] = host_data

#     #print('Host ::: ', host_data)

#     mycursor.execute("SELECT fdr_ip_address, device_id, fdr_oid_no, fdr_child_oid_no, fdr_discovered_value, fdr_discovery_id FROM c3p_t_fork_discovery_result where fdr_discovery_id ='" + str(dis_row_id) + "'")
#     row_header = [x[0].replace('fdr_','') for x in mycursor.description]
#     forkData = mycursor.fetchall()
#     for m in forkData:
#         ml = list(m)
#         ml[5] = rfo_id["SO_number"]
#         m = tuple(ml)
#         fork_data.append(dict(zip(row_header,m)))

#     json_data['fork'] = fork_data

#     #print('Host ::: ', fork_data)
#     print('Discovered Data :: ', json_data)

#     return jsonify(json_data)

""" Author: Ruchita Salvi"""
""" Date: 13/1/2021"""


def performThroughput(contentJson):
    destinationIp = contentJson['destMgmtIP']
    if (len(destinationIp) == 0):
        # call client directly
        # print('Inside if dest ip is null::', contentJson['srcMgmtIP'])
        response = networkTests.performThroughputClient(contentJson)
    else:
        # call server then call client this code is to be done in future
        logger.debug('performThroughput - Inside if dest ip is not null:: %s', contentJson['destMgmtIP'])
    return response


''' 
    Author: Rahul Tiwari"""
    Date: 08/2/2021"""
    Function to perform backup when device type is VNF
'''


def backupVNF(ipAddress, host, source, port, requestId, stage, version):
    # deviceDetails = mydb.cursor(buffered=True)
    mydb = Connections.create_connection()
    mycursor = mydb.cursor(buffered=True)

    dconnectValue = ''
    sql = "SELECT d_connect FROM c3p_deviceinfo where d_mgmtip= %s and d_hostname=%s"
    # print('SQL :: ', sql)
    try:
        # deviceDetails.execute(sql)
        mycursor.execute(sql, (ipAddress, host,))
        deviceDetails = mycursor.fetchall()

        for dconnect in deviceDetails:
            dconnectValue = dconnect[0]
        # deviceDetails.close()
        profileName = ''
        # print('dconnectValue :: ', dconnectValue)

        # deviceDetails = mydb.cursor(buffered=True)
        if (dconnectValue == 'SSH'):
            sql = "SELECT d_ssh_cred_profile FROM c3p_deviceinfo where d_mgmtip= %s and d_connect= %s"
        elif (dconnectValue == 'TELNET'):
            sql = "SELECT d_telnet_cred_profile FROM c3p_deviceinfo where d_mgmtip= %s and d_connect= %s"
        elif (dconnectValue == 'SNMP'):
            sql = "SELECT d_snmp_cred_profile FROM c3p_deviceinfo where d_mgmtip= %s and d_connect= %s"
        # deviceDetails.execute(sql)
        mycursor.execute(sql, (ipAddress,dconnectValue,))
        # r = deviceDetails.fetchone()
        r = mycursor.fetchone()
        profileName = r[0]
        logger.debug('backupVNF - Profile Name :: %s', profileName)

        # deviceDetails.close()
        # credDetails = mydb.cursor(buffered=True)
        ''' 
            get the credential details like user and pass based on profile name
        '''
        sql = "SELECT cr_login_read, cr_password_write FROM c3p_t_credential_management where cr_profile_name= %s"
        mycursor.execute(sql, (profileName,))
        # credDetails.execute(sql)
        # r1 = credDetails.fetchone()
        r1 = mycursor.fetchone()
        user = r1[0]
        password = r1[1]
        # print('User  :: ', user)
        # print('Password :: ', password)
        configData = ''
        try:
            with manager.connect_ssh(host=ipAddress, port=port, username=user, hostkey_verify=False,
                                     password=password) as m:
                configData = m.get_config(source=source).data_xml
            # credDetails.close()
        except Exception as conferr:
            logger.error('backupVNF - Error :: %s', str(conferr))
            return 'Error getting config'
    except mysql.connector.errors.ProgrammingError as e:
        logger.error('backupVNF - ProgrammingError - %s', e)
        return "ProgrammingError"
    except IOError as err:
        logger.error('backupVNF - IOError - %s', err)
        return "IOError"
    except Exception as err1:
        logger.error('backupVNF - Exception - %s', err1)
        return "Unknown Error"
    finally:
        mydb.close
    logger.info('backupVNF - sending getconfig response ')
    return configData


""" Function : Find the cloud platform for VNF Instantiation @ Anjireddy Reddem  """


def findCloudPlatform(inputRequest):
    logger.debug(" findCloudPlatform: %s", inputRequest)
    mydb = Connections.create_connection()
    try:
        mycursor = mydb.cursor(buffered=True)
        sql = "SELECT rc_value FROM c3p_resourcecharacteristicshistory where so_request_id = %s and rc_name='CloudPlatform'"
        mycursor.execute(sql, (inputRequest['requestId'],))
        result = mycursor.fetchone()
        cloud = result[0]
        return cloud
    except Exception as err:
        logger.error("Exception in findCloudPlatform: %s", err)
        return "Error"
    finally:
        mydb.close


""" Function : Fetch VNF Image details from the c3p_vnfimage_info table @ Anjireddy Reddem  """


def fetchVnfImageDetails(platform, image):
    result = []
    mydb = Connections.create_connection()
    try:
        mycursor = mydb.cursor(buffered=True)
        if platform == "GCP":
            sqlCondition = f"TRIM(v_imagename)= TRIM('{image}')"
        elif platform == "OpenStack":
            sqlCondition = f"TRIM(v_image_ref)= TRIM('{image}')"
        else:
            sqlCondition = f"TRIM(v_imagename)= TRIM('{image}')"

        sql = f"SELECT v_model,v_os,v_osversion,v_devicetype,v_family,v_vendor FROM c3p_vnfimage_info where " + sqlCondition
        logger.debug("fetchVnfImageDetails SQL IS :: %s", sql)
        mycursor.execute(sql)
        myresult = mycursor.fetchall()
        result = []
        for x in myresult:
            for t in x:
                result.append(t)
    except Exception as err:
        logger.error("Exception in fetchVnfImageDetails: %s", err)
    finally:
        mydb.close
    return result


""" Function : Fetch Cloud Resource details from the c3p_resourcecharacteristicshistory table @ Anjireddy Reddem  """


def fetchCloudResourceHistoryDetails(requestId):
    result = {}
    mydb = Connections.create_connection()
    try:
        mycursor = mydb.cursor(buffered=True)
        sql = "SELECT rc_name,rc_value FROM c3p_resourcecharacteristicshistory where so_request_id = %s"
        mycursor.execute(sql, (requestId,))
        for x in mycursor.fetchall():
            t = x
            result[t[0]] = t[1]
    except Exception as err:
        logger.error("Exception in fetchCloudResourceHistoryDetails: %s", err)
    finally:
        mydb.close
    return result


""" Function : Fetch Device information from the c3p_resourcecharacteristicshistory table @ Anjireddy Reddem  """


def fetchDeviceInfoResourceHistory(requestId):
    result = {}
    mydb = Connections.create_connection()
    try:
        mycursor = mydb.cursor(buffered=True)
        """

        sql =f"SELECT rc_device_hostname,rfo_id,device_id FROM c3p_resourcecharacteristicshistory where so_request_id = '{requestId}'"
        dataList = []
        mycursor.execute(sql)

        """
        dataList = []
        mycursor.execute(
            "SELECT rc_device_hostname,rfo_id,device_id FROM c3p_resourcecharacteristicshistory where so_request_id = %s",
            (requestId,));

        for x in mycursor.fetchone():
            dataList.append(x)

        result['dev_name'] = dataList[0]
        result['rfo_id'] = dataList[1]
        result['dev_id'] = dataList[2]
    except Exception as err:
        logger.error("Exception in fetchDeviceInfoResourceHistory: %s", err)
    finally:
        mydb.close
    return result


""" Function : Fetch Category Name from RF Orders table @ Anjireddy Reddem  """


def findCategoryFromRfOrder(rfoId):
    r_category = ''
    mydb = Connections.create_connection()
    try:
        mycursor = mydb.cursor(buffered=True)
        # sql =f"SELECT rfo_apibody FROM c3p_rf_orders where rfo_id = '{rfoId}'"
        mycursor.execute("SELECT rfo_apibody FROM c3p_rf_orders where rfo_id = %s",(rfoId,))
        myresult = mycursor.fetchone()
        if myresult != None:
            rfo_apibody = json.loads(''.join(myresult))
            for res in rfo_apibody["resourceRelationship"]:
                if res["resource"]["id"] == dev_id:
                    for reso in res["resource"].keys():
                        if reso == "place":
                            if res["resource"][reso]["role"].lower() == "servingsite":
                                site_id = int(res["resource"][reso]["id"])
                    r_category = res["resource"]["category"]

    except Exception as err:
        logger.error("Exception in findCategoryFromRfOrder: %s", err)
    finally:
        mydb.close
    return r_category


""" Function : Fetch Customer Site Id from Request Info & Customer info tables @ Anjireddy Reddem  """


def findCustSiteIdFromRequestInfo(requestId):
    siteId = 0
    mydb = Connections.create_connection()
    try:
        mycursor = mydb.cursor(buffered=True)
        # sql =f"SELECT custinfo.id FROM c3p_t_request_info reqinfo, c3p_cust_siteinfo custinfo where reqinfo.r_siteid=custinfo.c_site_id and reqinfo.r_alphanumeric_req_id = '{requestId}'"
        mycursor.execute(
            "SELECT custinfo.id FROM c3p_t_request_info reqinfo, c3p_cust_siteinfo custinfo where reqinfo.r_siteid=custinfo.c_site_id and reqinfo.r_alphanumeric_req_id = %s'",
            (requestId,));
        myresult = mycursor.fetchone()
        if myresult != None:
            siteId = myresult[0]
        logger.debug("findCustSiteIdFromRequestInfo siteId:: %s", siteId)
    except Exception as err:
        logger.error("Exception in findCustSiteIdFromRequestInfo: %s", err)
    finally:
        mydb.close
    return siteId


""" Function : Insert the data in c3p_deviceinfo table @ Anjireddy Reddem  """


def insertDeviceInfoData(deviceId, sqlValues):
    mydb = Connections.create_connection()
    try:
        mycursor = mydb.cursor(buffered=True)
        if deviceId != None:
            sql = f"""insert into c3p_deviceinfo(d_id, d_hostname,d_image_filename,d_model,d_os,d_os_version,d_device_family,d_type,d_upsince,d_vnf_support,d_vendor,d_mgmtip,d_macaddress,c_site_id,d_new_device)
            values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"""
        else:
            sql = f"""insert into c3p_deviceinfo(d_hostname,d_image_filename,d_model,d_os,d_os_version,d_device_family,d_type,d_upsince,d_vnf_support,d_vendor,d_mgmtip,d_macaddress,c_site_id,d_new_device)
            values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"""
        mycursor.execute(sql, sqlValues)
        mydb.commit()

        if deviceId == None:
            # Find last inserted d_id in table
            mycursor.execute("SELECT d_id FROM c3p_deviceinfo WHERE d_id = (select last_insert_id())")
            myresult = mycursor.fetchone()
            deviceId = myresult[0]
    except Exception as err:
        deviceId = None
        mydb.rollback()
        logger.error("Exception in insertDeviceInfoData: %s", err)
    finally:
        mydb.close
    return deviceId


""" Function : Insert the data in c3p_deviceinfo_ext table @ Anjireddy Reddem  """


def insertDeviceInfoExtData(deviceId, category, state, imageInstanceId, adminPass):
    mydb = Connections.create_connection()
    try:
        mycursor = mydb.cursor(buffered=True)
        # sql =f"INSERT INTO c3p_deviceinfo_ext(r_device_id,r_category,r_opertionalState, r_imageInstanceId, r_imageAdminPass) values('{deviceId}','{category}','{state}','{imageInstanceId}','{adminPass}')"
        mycursor.execute(
            f"INSERT INTO c3p_deviceinfo_ext(r_device_id,r_category,r_opertionalState, r_imageInstanceId, r_imageAdminPass) values(%s,%s,%s,%s,%s)", (deviceId,category,state,imageInstanceId,adminPass,))
        mydb.commit()
    except Exception as err:
        mydb.rollback()
        logger.error("Exception in insertDeviceInfoExtData: %s", err)
    finally:
        mydb.close


""" Function : Update the device id info in c3p_resourcecharacteristicshistory table @ Anjireddy Reddem  """


def updateResourceHistoryDeviceId(requestId, deviceId):
    mydb = Connections.create_connection()
    try:
        mycursor = mydb.cursor(buffered=True)
        # sql = f"UPDATE c3p_resourcecharacteristicshistory SET device_id = '{deviceId}' where so_request_id = '{requestId}'"
        mycursor.execute("UPDATE c3p_resourcecharacteristicshistory SET device_id = %s where so_request_id = %s", (deviceId,requestId,))
        mydb.commit()
    except Exception as err:
        mydb.rollback()
        logger.error("Exception in updateResourceHistoryDeviceId: %s", err)
    finally:
        mydb.close


""" Function : Update the data in webserviceinfo table @ Anjireddy Reddem  """


def updateWebServiceInfo(requestId, message):
    mydb = Connections.create_connection()
    try:
        mycursor = mydb.cursor(buffered=True)
        mycursor.execute("UPDATE webserviceinfo SET TextFound_DeliveryTest = %s where alphanumeric_req_id = %s",
                         (message, requestId,));
        mydb.commit()
    except Exception as err:
        mydb.rollback()
        logger.error("Exception in updateWebServiceInfo: %s", err)
    finally:
        mydb.close


""" Function : Update the management IP in c3p_t_request_info table @ Anjireddy Reddem  """


def updateRequestInfoMgmtIp(requestId, managementIp):
    mydb = Connections.create_connection()
    try:
        mycursor = mydb.cursor(buffered=True)
        logger.debug("updateRequestInfoMgmtIp -requestId: %s", requestId)
        logger.debug("updateRequestInfoMgmtIp -managementIp: %s", managementIp)
        mycursor.execute("UPDATE c3p_t_request_info SET r_management_ip = %s where r_alphanumeric_req_id = %s", (managementIp,requestId,));
        mydb.commit()
    except Exception as err:
        mydb.rollback()
        logger.error("Exception in updateRequestInfoMgmtIp: %s", err)
    finally:
        mydb.close


def calculate_subnets(subnets):
    logger.debug("calculate_subnets start")
    result = {"status": "False", "ipaddrs": []}
    if subnets:
        for subnet in subnets:
            for xaddr in ipcalc.Network(subnet):
                xaddr = str(xaddr)
                result["status"] = "True"
                result["ipaddrs"].append(xaddr)
    else:
        logger.debug("calculate_subnets - [x] ip_range_calculate.py -- subnets = []")

    return result


""" Function : To perform generate pdf report @ Rahul Tiwari  """


def generatePDFReport(input, output):
    try:
        config = pdfkit.configuration(wkhtmltopdf=bytes('/usr/local/bin/wkhtmltopdf', 'utf-8'))
        pdfkit.from_string(input, output, configuration=config)
    except Exception as err:
        logger.error("Exception in generatePDFReport: %s", err)
        return "Failed"
    return "Success"


""" Function : To computeDeltaInInputs Ruchita Salvi """


def computeDeltaInInputs(filepath1, filepath2):
    json_data = {}
    hasDelta = False
    json_data['output'] = hasDelta
    try:
        logger.debug("Inside compute delta function")
        """input1 = open(filepath1, "r")
        input2 = open(filepath2, "r")
        data1 = input1.readlines()
        data2 = input2.readlines()
        input1.close()
        input2.close()"""

        # Validating the file path1
        base_path = "/opt/jboss/C3PConfig/ConfigurationFiles/"
        filename = os.path.basename(filepath1)
        filepath1 = os.path.normpath(os.path.join(base_path, filename))
        if not filepath1.startswith(base_path):
            logger.error(f"Invalid file path: {filepath1}")
            return jsonify({"error": f"Invalid file path: {filepath1}"})

        # Validating the file path2
        base_path = "/opt/jboss/C3PConfig/ConfigurationFiles/"
        filename = os.path.basename(filepath2)
        filepath2 = os.path.normpath(os.path.join(base_path, filename))
        if not filepath2.startswith(base_path):
            logger.error(f"Invalid file path: {filepath2}")
            return {"error": f"Invalid file path: {filepath2}"}

        with open(filepath1, "r") as f1:
            data1 = f1.readlines()
        with open(filepath2, "r") as f2:
            data2 = f2.readlines()
        f1.close()
        f2.close()
        if data1 != None and data2 != None:
            s = difflib.SequenceMatcher(lambda x: x == " ",
                                        data1,
                                        data2)
            logger.debug("Delta value between two files::: %s", round(s.ratio(), 3))
            value = round(s.ratio(), 3)
            if value != 1:
                hasDelta = True
            else:
                hasDelta = False
        else:
            hasDelta = False
            logger.error("Either of the file is empty or path incorrect")
        json_data['output'] = hasDelta
    except Exception as err:
        logger.error("Exception in computeDeltaInInputs: %s", err)
        return json_data
    return json_data


""" Function : To computeConfigCompare """


def computeConfigDifferenceCount(filepath1, filepath2):
    data = {}
    try:
        logger.debug("Inside compute config compare")

        """input1 = open(filepath1, "r")
        input2 = open(filepath2, "r")
        data1 = input1.readlines()
        data2 = input2.readlines()
        input1.close()
        input2.close()"""

        # Validating the file path1
        base_path = "/opt/jboss/C3PConfig/ConfigurationFiles/"
        filename = os.path.basename(filepath1)
        filepath1 = os.path.normpath(os.path.join(base_path, filename))
        if not filepath1.startswith(base_path):
            logger.error(f"Invalid file path: {filepath1}")
            return jsonify({"error": f"Invalid file path: {filepath1}"})

        # Validating the file path2
        base_path = "/opt/jboss/C3PConfig/ConfigurationFiles/"
        filename = os.path.basename(filepath2)
        filepath2 = os.path.normpath(os.path.join(base_path, filename))
        if not filepath2.startswith(base_path):
            logger.error(f"Invalid file path: {filepath2}")
            return {"error": f"Invalid file path: {filepath2}"}

        with open(filepath1, "r") as f1:
            data1 = f1.readlines()
        with open(filepath2, "r") as f2:
            data2 = f2.readlines()
        f1.close()
        f2.close()

        addCount = 0
        subCount = 0
        modCount = 0
        if data1 != None and data2 != None:
            hDiff = difflib.HtmlDiff().make_table(data1, data2, filepath1, filepath2)
            logger.debug("computeConfigDifferenceCount -- hDiff :: ", hDiff)
            spanClassName = fromstring(hDiff)
            iterableChg = iter(spanClassName.find_class('diff_chg'))
            iterableAdd = iter(spanClassName.find_class('diff_add'))
            iterableMod = iter(spanClassName.find_class('diff_sub'))
            while True:
                try:
                    modLine = next(iterableChg)
                    logger.debug("computeConfigDifferenceCount -- modline :: ", modLine)
                    modCount += 1
                except StopIteration:
                    break

            while True:
                try:
                    addLine = next(iterableAdd)
                    logger.debug("computeConfigDifferenceCount -- addline :: ", addLine)
                    addCount += 1
                except StopIteration:
                    break

            while True:
                try:
                    subLine = next(iterableMod)
                    logger.debug("computeConfigDifferenceCount -- subLine :: ", subLine)
                    subCount += 1
                except StopIteration:
                    break

        else:
            logger.error("Either of the file is empty or path incorrect")
        data['Addition'] = addCount
        data['Deletion'] = subCount
        data['Modification'] = modCount
        json_data = json.dumps(data)
    except Exception as err:
        logger.error("Exception in computeConfigDifferenceCount: %s", err)
        errJson = {"errMessage": "Error ocurred"}
        return errJson
    return json_data


def computeDifference(content):
    input1 = None
    data = {}
    if content is not None:
        for item in content:
            if input1 is None:
                input1 = item
            else:
                input2 = item

    if input1 != None and input2 != None:
        l1 = input1.split("\n")
        l2 = input2.split("\n")
        hDiff = difflib.HtmlDiff().make_file(l1, l2, "Snippet from user",
                                             "Snippet from device")
        data['output'] = hDiff
        json_data = json.dumps(data)
    else:
        logger.error("Comparison -> Either of the inputs is empty")
    return json_data


''' 
    Author: Rahul Tiwari"""
    Date: 12/01/2022"""
    Function to perform id generation
'''


def generateId(sourceSystem, requestingPageEntity, requestType, requestingModule):
    logger.debug("generateId -sourceSystem: %s", sourceSystem)
    logger.debug("generateId -requestingPageEntity: %s", requestingPageEntity)
    logger.debug("generateId -requestType: %s", requestType)
    logger.debug("generateId -requestingModule: %s", requestingModule)
    try:
        currentDT = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        convertCurrentDT = str(currentDT)
        logger.debug("generateId -convertCurrentDT: %s", convertCurrentDT)

        reportName = requestingPageEntity[0]
        reportType = requestType[0]

        reportCategory = ""
        # Traverse the string.
        isSpace = True
        for i in range(len(requestingModule)):
            # If it is space, set isSpace as true.
            if requestingModule[i] == " ":
                isSpace = True
            # Else check if isSpace is true or not.
            # If true, copy character in output
            # reportCategory and set isSpace as false.
            elif requestingModule[i] != " " and isSpace == True:
                reportCategory += requestingModule[i]
                isSpace = False
        logger.debug("generateId - ---> reportCategory: %s", reportCategory)

        # Random value from the list
        randomList = ['1', '2', '3', '4', '5', '6', '7', '8', '9', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J',
                      'K',
                      'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z']
        logger.debug("==>generateId - convertCurrentDT==>: %s", convertCurrentDT)

        generatedId = escape(reportName) + escape(reportType) + escape(reportCategory) + '-' + escape(convertCurrentDT) + random.choice(randomList)
    except Exception as e:
        logger.error('Exception in generateId - Exception - %s', e)
        errJson = {"errMessage": "Error ocurred"}
        return errJson
    logger.info('generateId - sending generatedId as a response ' + generatedId)
    return generatedId