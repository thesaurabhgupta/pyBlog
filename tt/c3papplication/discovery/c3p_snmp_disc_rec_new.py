from pysnmp.hlapi import *
import mysql.connector
import sys
import random, string
import json, logging
import pandas as pd
from struct import pack, unpack
from datetime import datetime
from pysnmp.entity.rfc3413.oneliner import cmdgen
from pysnmp.proto.rfc1902 import Integer, IpAddress, OctetString
from flask import jsonify
import concurrent.futures
from c3papplication.common import Connections, c3p_lib
from c3papplication.conf.springConfig import springConfig
import requests
# import getAllIPsForDiscovery
from requests.auth import HTTPBasicAuth
from jproperties import Properties
from c3papplication.discovery import c3p_card_slot_gen as physicalinventorypopulator
from c3papplication.discovery import c3p_topology as CLT, c3p_snmp_disc_rec_new2 as SnmpDRN2

logger = logging.getLogger(__name__)
configs = springConfig().fetch_config()


# *********************** Functionals from c3p_lib for discovery START

def resultDiscoveryReconciliation(content, ipList):
    mydb = Connections.create_connection()
    mycursor = mydb.cursor(buffered=True)

    disReturn = []

    disRowInfo = createDiscoveryRecord(content)

    """ perform the discovery for each IP and Save the resultant """
    disRowID = disRowInfo[0]
    disId = disRowInfo[1]
    disStart = disRowInfo[2]
    logger.debug('resultDiscoveryReconciliation - disRowID :: %s', disRowID)

    """ perform the device discovery for each of the ip identified for the range of ips """

    disCommunity = disRowInfo[3]
    logger.debug('performDiscovery - ipList :: %s', ipList)
    dID = performDiscovery(ipList, disRowID, disCommunity, content["createdBy"], content["sourcesystem"])
    if (len(dID)):
        with concurrent.futures.ProcessPoolExecutor() as executor:
            results = executor.map(c3pDiscovery, dID)

        for result in results:
            disReturn.append(result)
            logger.debug('resultDiscoveryReconciliation - discovery range result :: %s', result)
        if 'importId' in content:
            uDDS = upDateDisDashandStatus(disReturn, content["importId"])
        else:
            uDDS = upDateDisDashandStatus(disReturn, None)
        logger.debug('resultDiscoveryReconciliation - discovery uDDS :: %s', uDDS)

        rOut = {"DisID ": disId, "DisStatus": uDDS[0], "DisStart": disStart, "DisEnd": uDDS[1]}
    else:
        mycursor.execute(
            "UPDATE c3p_t_discovery_dashboard SET dis_status ='Completed', dis_updated_date = %s WHERE dis_row_id = %s", (datetime.today().strftime('%Y-%m-%d %H:%M:%S'), disRowID,  ))
        mydb.commit()
        if 'importId' in content:
            import_id = content["importId"].split("_")
            logger.info("import_id for rejected device ", import_id)
            mycursor.execute(
                "UPDATE c3p_t_ds_import_staging SET is_row_status ='Completed' WHERE is_import_id =%s AND is_seq_id =%s", (import_id[0], import_id[1], ))
            mydb.commit()
        rOut = {"DisStatus": "Rejected Device"}
    return rOut


# elif((content['ipType']) == 'ipv6'):
#     discoveryFlag = 'range ipv6'
#     # print('iprange for ipv6')


def checkIPinInv(cIP, cdisID, cCom, cCBy, cSource):
    # Check the inventory for the IP address, its status, network type and the current status
    myInvChk = []
    mydb = Connections.create_connection()
    logger.debug('checkIPinInv')

    try:
        mycursor = mydb.cursor(buffered=True)
        b = (cIP, cdisID, cCom)
        d = (cIP, cdisID, cCom, '#', '#', '#', '#', cCBy, cSource)
        c = (cCBy, cSource)

        sql = "SELECT d_id, d_vendor,d_vnf_support, d_hostname, d_decomm FROM c3p_deviceinfo where d_mgmtip=%s"
        logger.debug('checkIPinInv - query :%s', sql)

        mycursor.execute(sql, (str(cIP), ))
        myInvChk = mycursor.fetchall()

        for invChk in myInvChk:
            if (invChk[4] == '8'):
                d = "800"
                instSql = "INSERT INTO c3p_t_discovery_status ( ds_ip_addr ,  ds_created_date ,  ds_created_by , ds_updated_date , ds_status ,  ds_comment ,  ds_device_id ,  ds_hostname , ds_device_flag , ds_discovery_id ) VALUES (%s, %s,%s,%s,%s,%s,%s,%s,%s,%s)"
                dReVal = (cIP, datetime.today().strftime('%Y-%m-%d %H:%M:%S'), cCBy,
                          datetime.today().strftime('%Y-%m-%d %H:%M:%S'), '800', 'R : R : R', invChk[0], invChk[3], '',
                          cdisID)
                mycursor.execute(instSql, dReVal)
                mydb.commit()
            elif (invChk[4] == '0'):
                d = b + invChk[0:4] + c
                logger.debug('checkIPinInv - d :%s', d)
    except Exception as err:
        logger.error("Exception in checkIPinInv: %s", err)
    finally:
        mydb.close
    return d


def createDiscoveryRecord(disInfo):
    dT = ''
    ipT = ''
    disRowID = ''
    disID = ''
    disStart = ''
    disCom = ''
    importIp = ''
    mydb = Connections.create_connection()
    try:
        mycursor = mydb.cursor(buffered=True)

        logger.debug("createDiscoveryRecord - disInfo - :: %s", disInfo)
        disType = disInfo['discoveryType']
        ipType = disInfo['ipType']
        disName = disInfo['discoveryName']
        sIP = disInfo['startIp']
        eIP = disInfo['endIp']
        netMask = disInfo['netMask']
        if 'importId' in disInfo:
            importIp = disInfo['importId']
            logger.info("createDiscoveryRecord -> Import IP value ", importIp)
        # disCom  = disInfo['community']
        disCom_temp = disInfo['community']

        if (disType  == 'ipList'):
            listofIps = sIP
            totalNumOfIps = len(listofIps)
            sIP = listofIps[0]
            eIP = listofIps[totalNumOfIps - 1]

        # # sql = "SELECT cr_profile_name FROM c3p_t_credential_management where cr_login_read='"+disCom_temp+"'"
        # sql = "SELECT cr_login_read,cr_version FROM c3p_m_credential_management where cr_profile_name='" + disCom_temp + "' and cr_profile_type='SNMP'"
        # # logger.debug('createDiscoveryRecord - disCom SQL :: %s', sql)

        # mycursor.execute(sql)
        # result = mycursor.fetchone()

        # logger.debug('createDiscoveryRecord - disCom result :: %s', result)
        # if "snmpv3" in result[1].lower():
        #     disCom = 'snmpv3'
        #     logger.debug(' get version snmp :: %s', disCom)
        # else:
        #     disCom = ''.join(result[0])
        #     logger.debug('get community user :: %s', disCom)

        disCby = disInfo['createdBy']

        # disSrc  = disInfo['sourcesystem']

        disSrc = (lambda: "", lambda: disInfo['sourcesystem'])['sourcesystem' in disInfo.keys()]()
        disStart = datetime.today().strftime('%Y-%m-%d %H:%M:%S')

        # logic to generate the discovery id

        if (disType == 'ipSingle'):
            dT = 'S'
        elif (disType == 'ipRange'):
            dT = 'R'
        elif (disType == 'import'):
            dT = 'I'
        elif (disType == 'ipList'):
            dT = 'R'
        if (ipType == 'ipv4'):
            ipT = '4'
        elif (ipType == 'ipv6'):
            ipT = '6'

        # prepare the discovery id
        disStC = disStart.replace("-", "")
        disStC = disStC.replace(":", "")
        disStC = disStC.replace(" ", "")
        logger.info("disStc value is " + disStC)
        disID = 'S' + 'D' + dT + ipT + disStC + ''.join(random.choices(string.ascii_uppercase, k=2))

        logger.debug('createDiscoveryRecord :: discovert ID : %s ', disID)

        # inserting discovery record into a table
        # SDS4 / SDR4 / SDS6 / SDR6 / SDRI followed by 6 ID

        sql = "INSERT  INTO c3p_t_discovery_dashboard (dis_dash_id,dis_name,dis_status,dis_ip_type,dis_discovery_type,dis_start_ip,dis_end_ip,dis_network_mask,dis_profile_name,dis_schedule_id,dis_created_date,dis_created_by,dis_import_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
        insValue = (
        disID, disName, 'InProgress', ipType, disType, sIP, eIP, netMask, disCom_temp, '', disStart, disCby, importIp)
        logger.debug('createDiscoveryRecord :: sql %s', sql)
        logger.debug('createDiscoveryRecord :: insValue %s', insValue)

        """ 
        Create Order Id as the discovery request received from an external system e.g. ServiceNow (SNOW)
        If request is genereated internally it will not generate the Order Id
        """
        if not disSrc == 'c3p-ui':
            """ Create a Order record in c3p_rf_order rfo_id = disID"""
            # logger.debug('createDiscoveryRecord - disInfo :: %s', json.dumps(disInfo))
            sqlOrder = "INSERT INTO c3p_rf_orders (rfo_id,rfo_apibody,rfo_apioperation,rfo_apiurl,rfo_sourcesystem,rfo_apiauth_status,rfo_status,rfo_created_date) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)"
            insValueOrder = (
            disID, json.dumps(disInfo), 'POST', '/C3P/api/ext/discovery/', disSrc, 'Pass', 'InProgress', disStart)

            mycursor.execute(sqlOrder, insValueOrder)
            logger.debug("createDiscoveryRecord - Order record inserted. %s", mycursor.rowcount)

            disRowID = mycursor.lastrowid
            logger.debug('createDiscoveryRecord - Order id :: %s', disRowID)
            mydb.commit()

        try:
            mycursor.execute(sql, insValue)
            logger.debug("createDiscoveryRecord - discovery record inserted. %s", mycursor.rowcount)
            disRowID = mycursor.lastrowid
            mydb.commit()
        except mysql.connector.errors.ProgrammingError as err:
            logger.error('createDiscoveryRecord - Error discovery inserting record :: %s', err)
            disRowID = ''
            disID = 'Error C3P-DR-502'
    except Exception as err:
        logger.error("Exception in createDiscoveryRecord: %s", err)
    finally:
        mydb.close
    return (disRowID, disID, disStart, disCom_temp)


def performDiscovery(sIP, disID, disCom, disCBy, disSource):
    logger.debug('performDiscovery - sIP :: %s', sIP)
    pD = []
    # inside the perform Discovery
    # check the IP address is available in inventory
    for m in sIP:
        # logger.debug('performDiscovery - TempsIP :: %s', m)
        dID = checkIPinInv(m, disID, disCom, disCBy, disSource)
        if "800" not in dID:
            pD.append(dID)

        logger.debug('performDiscovery - pD :: %s', pD)
        # print('Type dID = ', type(dID))

        # with concurrent.futures.ProcessPoolExecutor() as executor:
        # results = executor.map(checkIPinInv, m,disID, disCom)

    return pD


# **************************    Update the discovery dashboard and Status of each IP table  **********************
def upDateDisDashandStatus(rDDS, importId):
    logger.info('inside upDateDisDashandStatus function :: ')
    mydb = Connections.create_connection()
    try:
        mycursor = mydb.cursor(buffered=True)

        disRowID = 0
        valDDs = []
        disStat = 'Completed'
        disUpdate = datetime.today().strftime('%Y-%m-%d %H:%M:%S')

        insSql = "INSERT INTO  c3p_t_discovery_status ( ds_ip_addr ,  ds_created_date ,  ds_created_by , ds_updated_date , ds_status ,  ds_comment ,  ds_device_id ,  ds_hostname , ds_device_flag , ds_discovery_id ) VALUES (%s, %s,%s,%s,%s,%s,%s,%s,%s,%s)"

        for dRe in rDDS:
            dReVal = (
            dRe[0], dRe[11], dRe[14], dRe[12], dRe[10], str(dRe[7]) + ' : ' + str(dRe[8]) + ' : ' + str(dRe[9]), dRe[3],
            dRe[13], dRe[4], dRe[2])
            disRowID = dRe[2]
            mycursor.execute(insSql, dReVal)
            mydb.commit()
            logger.debug("upDateDisDashandStatus :: record inserted %s", mycursor.rowcount)

            valDDs.append(dReVal)
            logger.debug('*************Preparing discoverystatus records***** %s', valDDs)

        # try:
        #     # if mydb.is_connected():
        #     #    print('************************ DB still connected :: ')
        #     # else:
        #     #     print('*********************** DB reconnection :: ')
        #     #     mydb = Connections.create_connection()
        #     #     mycursor = mydb.cursor(buffered=True)
        #     logger.debug('************************ Here :: %s', insSql)
        #     #mycursor.executemany(insSql, valDDs)
        #     #mydb.commit()
        #     #print(mycursor.rowcount, "record inserted.")
        #     #myUDDS.close()
        #     # return f'{myUDDS.rowcount} record inserted.'
        # except mysql.connector.errors.ProgrammingError as e:
        #     logger.error('upDateDisDashandStatus - Insert Error in processing - %s',e)
        #     #mycursor.close()
        #     return('Error')

        updSql = "UPDATE c3p_t_discovery_dashboard SET dis_status ='" + disStat + "', dis_updated_date = '" + disUpdate + "' WHERE dis_row_id = '" + str(
            disRowID) + "'"

        try:
            mycursor.execute(updSql)
            mydb.commit()
            logger.debug("upDateDisDashandStatus :: %s record(s) Updated", mycursor.rowcount)
            if importId is not None:
                import_id = importId.split("_")
                mycursor.execute(
                    "UPDATE c3p_t_ds_import_staging SET is_row_status =%s WHERE is_import_id =%s"\
                    "AND is_seq_id =%s", (disStat, import_id[0], import_id[1],))
                mydb.commit()
                logger.debug("upDateDisDashandStatus :: %s record(s) Updated in staging", mycursor.rowcount)

        except mysql.connector.errors.ProgrammingError as err:
            logger.error('upDateDisDashandStatus :: Update Error in processing - %s', err)
            return ('C3P-DR-502', disUpdate)

    except Exception as err:
        logger.error("Exception in upDateDisDashandStatus: %s", err)
    finally:
        mydb.close
    return (disStat, disUpdate)


def extDiscovery(rfo_id):
    sIP = []
    eIP = []
    ipAddrList = []
    disReturn = []
    reOut = []
    importId = []
    mydb = Connections.create_connection()

    try:
        mycursor = mydb.cursor(buffered=True)
        mycursor.execute("SELECT dis_row_id FROM c3p_t_discovery_dashboard  where dis_dash_id=%s", (rfo_id,))
        myresult = mycursor.fetchone()
        dis_row_id = myresult[0]
        # dis_row_id=''.join(myresult)

        mycursor.execute("SELECT rfo_apibody FROM c3p_rf_orders where rfo_id=%s", (rfo_id,))
        myresult = mycursor.fetchone()
        logger.debug("extDiscovery :: myresults ::: %s", myresult)
        rfo_apibody = ''.join(myresult)

        body_dict = json.loads(rfo_apibody).keys()

        if (rfo_id[0:3] == 'SDS'):
            for dbd in body_dict:
                if dbd == "startIp":
                    logger.debug('extDiscovery :: Start IP : %s', json.loads(rfo_apibody)[dbd])
                    sIP.append(str(json.loads(rfo_apibody)[dbd]))
                    logger.debug('sIP ::: %s', sIP)
                if dbd == "community":
                    community = json.loads(rfo_apibody)[dbd]
                if dbd == "createdBy":
                    createdBy = json.loads(rfo_apibody)[dbd]
                if dbd == "sourcesystem":
                    sourcesystem = json.loads(rfo_apibody)[dbd]

            dID = performDiscovery(sIP, dis_row_id, community, createdBy, sourcesystem)
            logger.debug('extDiscovery :: dID :: %s', dID)

        elif (rfo_id[0:3] == 'SDR'):
            for dbd in body_dict:
                if dbd == "startIp":
                    sIP = json.loads(rfo_apibody)[dbd]
                if dbd == "community":
                    community = json.loads(rfo_apibody)[dbd]
                if dbd == "createdBy":
                    createdBy = json.loads(rfo_apibody)[dbd]
                if dbd == "netMask":
                    netMask = json.loads(rfo_apibody)[dbd]
                if dbd == "endIp":
                    eIP = json.loads(rfo_apibody)[dbd]
                if dbd == "sourcesystem":
                    sourcesystem = json.loads(rfo_apibody)[dbd]

            ipAddrList = c3p_lib.getAllIPsForDiscovery(sIP, netMask, eIP)

            dID = performDiscovery(ipAddrList, dis_row_id, community, createdBy, sourcesystem)
            logger.debug('extDiscovery :: dID :: %s', dID)

        with concurrent.futures.ProcessPoolExecutor() as executor:
            reOut = executor.map(c3pDiscovery, dID)
        logger.debug("extDiscovery :: results after threading ::: %s", reOut)

        for result in reOut:
            disReturn.append(result)
        logger.debug("extDiscovery :: results after threading ::disReturn: %s", disReturn)
        uDDS = upDateDisDashandStatus(disReturn, importId)
        logger.debug('extDiscovery :: discovery uDDS :: %s', uDDS)
    except Exception as err:
        logger.error("Exception in extDiscovery: %s", err)
    finally:
        mydb.close
    return False

# *********************** Functionals from c3p_lib for discovery END

# ************************ extract_discoveryValue ******************************
def extract_discoveryValue(displayName, disValue, disVendor):
    logger.debug("extract_discoveryValue - displayName:: %s", displayName)
    logger.debug("extract_discoveryValue - disValue:: %s", disValue)
    logger.debug("extract_discoveryValue - disVendor:: %s", disVendor)
    extractDiscoveredValue = ''
    if ((disValue == ' ') or (disValue is None) or (len(str(disValue)) == 0)):
        extractDiscoveredValue = 'Not Available'
    elif disVendor.upper() == 'CISCO':
        if (displayName == 'Vendor'):
            # print('Display value = ', disValue)
            extractDiscoveredValue = str(disValue).split(' ', 2)[0]
            extractDiscoveredValue = ''.join(extractDiscoveredValue).upper()
        elif (displayName == 'Family'):
            if (len(str(disValue).split('(')) > 0):
                extractDiscoveredValue = str(disValue).split('(')[0].split(' ')[1]  # for telstra logic
                # extractDiscoveredValue = str(disValue).split('(')[0].split(' ')[1]
                extractDiscoveredValue = ''.join(extractDiscoveredValue).upper().strip()
            else:
                extractDiscoveredValue = str(disValue).split(' ', 2)[1]
        elif (displayName == 'Hostname'):
            extractDiscoveredValue = str(disValue).split('.', 2)[0]
            extractDiscoveredValue = ''.join(extractDiscoveredValue).upper().strip()
        elif (displayName == 'Model'):
            if (len(str(disValue).split('(')) > 0):
                # extractDiscoveredValue = str(disValue).split('(', 2)[1].split(' ')[1] # for telstra logic
                extractDiscoveredValue = str(disValue).split('(', 2)[0].split(' ')[0]
                extractDiscoveredValue = ''.join(extractDiscoveredValue).upper().strip()
            else:
                extractDiscoveredValue = str(disValue).split(' ', 2)[1]  # for telstra logic
                # extractDiscoveredValue = str(disValue).split(' ',2)[0]
        elif (
                displayName == 'OS Version'):  # e.g.1  = STRING: "JUNOS Base OS Software Suite [20.4R2.7]"/e.g.2 STRING: [16.09.01]
            extractDiscoveredValue = str(disValue).upper()
            extractDiscoveredValue = extractDiscoveredValue.replace('(', '').replace(')', '').replace('[', ' ').replace(
                ']', '').replace(',', '').split(' ')
            # x = extractDiscoveredValue.index('VERSION')
            # extractDiscoveredValue = ''.join(extractDiscoveredValue[x + 1]).strip()
            extractDiscoveredValue = ''.join(extractDiscoveredValue[0]).strip()
        elif (displayName == 'OSPNF'):
            # print('inside os =',disValue)
            extractDiscoveredValue = str(disValue).upper()
            extractDiscoveredValue = extractDiscoveredValue.split('(')[0].split(' ')[1:]

            if 'X' in extractDiscoveredValue[1] and len(extractDiscoveredValue[1]) == 2:
                extractDiscoveredValue = ' '.join(extractDiscoveredValue[0:2]).upper()
            else:
                extractDiscoveredValue = ''.join(extractDiscoveredValue[0:1]).upper()
            # extractDiscoveredValue = str(disValue).split(' ', 4)
            # logger.debug("Extract Value :: %s", extractDiscoveredValue, "\n Extracted Value [3]:: %s", extractDiscoveredValue[3], "\n")
        elif (displayName == 'OSVNF'):
            # print('inside os detail =',disValue)
            extractDiscoveredValue = str(disValue).replace('\r', '').replace('\n', '')
            extractDiscoveredValue = str(extractDiscoveredValue).split(' ', 2)[0]
        elif (displayName == 'Software Image'):
            # print('Inside SOftware Image', disValue)
            extractDiscoveredValue = str(disValue).split('/', 2)[2]
            # print('Inside SOftware Image Out', extractDiscoveredValue)
        else:
            extractDiscoveredValue = disValue.prettyPrint()
    elif disVendor.upper() == 'JUNIPER':
        if (displayName == 'Vendor'):
            # print('Display value = ', disValue)
            extractDiscoveredValue = str(disValue).split(' ', 2)[0].upper()
        elif (displayName == 'Family'):  # e.g. = STRING: "Juniper Networks,Inc.vsrx firewall Junos: 20.4R2.7,kernel"
            extractDiscoveredValue = str(disValue).lower().replace("juniper", "")
            extractDiscoveredValue = extractDiscoveredValue.lower().replace("networks,", "")
            extractDiscoveredValue = extractDiscoveredValue.lower().replace("inc.", "").lstrip()
            extractDiscoveredValue = extractDiscoveredValue.split(' ', 2)[0].strip().upper()
        elif (displayName == 'Hostname'):
            extractDiscoveredValue = str(disValue).split('.', 2)[0]
        elif (displayName == 'Model'):  # e.g.  = STRING: "Juniper VSRX Internet Router"
            extractDiscoveredValue = str(disValue).split(' ')[1]
            extractDiscoveredValue = ''.join(extractDiscoveredValue).upper().strip()
        elif (displayName == 'OS Version'):  # e.g.  = STRING: "JUNOS Base OS Software Suite [20.4R2.7]"
            extractDiscoveredValue = str(disValue).split(' ')[-1:]
            extractDiscoveredValue = ''.join(extractDiscoveredValue)[1:-1]
        elif (displayName == 'OSPNF'):  # e.g.  = STRING: "JUNOS Base OS Software Suite [20.4R2.7]"
            extractDiscoveredValue = str(disValue).split(' ')[0]
            extractDiscoveredValue = ''.join(extractDiscoveredValue).upper()
        elif (displayName == 'OSVNF'):
            # print('inside os detail =',disValue)
            extractDiscoveredValue = str(disValue).replace('\r', '').replace('\n', '')
            extractDiscoveredValue = str(extractDiscoveredValue).split(' ', 2)[0]
        elif (displayName == 'Software Image'):
            # print('Inside SOftware Image', disValue)
            extractDiscoveredValue = str(disValue).split('/', 2)[2]
            # print('Inside SOftware Image Out', extractDiscoveredValue)
        else:
            extractDiscoveredValue = disValue.prettyPrint()

    elif disVendor == '#' or disVendor == '':
        if (displayName == 'Vendor'):
            if "Nokia" in str(disValue):
                extractDiscoveredValue = "NOKIA"
                logger.debug("extract_discoveryValue - disVendor is #:: %s", extractDiscoveredValue)
            else:
                extractDiscoveredValue = str(disValue).split(' ', 2)[0]
                # print('Display value = ', disValue)
        elif (displayName == 'Family'):
            extractDiscoveredValue = str(disValue).split(' ', 2)[1]
        elif (displayName == 'Hostname'):
            extractDiscoveredValue = str(disValue).split('.', 2)[0]
        elif (displayName == 'OSPNF'):
            # print('inside os =',disValue)
            extractDiscoveredValue = str(disValue).replace(',', ' ', 2)
            extractDiscoveredValue = str(extractDiscoveredValue).split(' ', 2)[1]
        elif (displayName == 'OSVNF'):
            # print('inside os detail =',disValue)
            extractDiscoveredValue = str(disValue).replace('\r', '').replace('\n', '')
            extractDiscoveredValue = str(extractDiscoveredValue).split(' ', 2)[0]
        elif (displayName == 'Software Image'):
            # print('Inside SOftware Image', disValue)
            extractDiscoveredValue = str(disValue).split('/', 2)[2]
            # print('Inside SOftware Image Out', extractDiscoveredValue)
        else:
            extractDiscoveredValue = disValue.prettyPrint()

    elif disVendor.upper() == 'FSP' or disVendor.upper() == 'ADVA':
        logger.debug("extractDiscoveredValue:ADVA::Type disValue: %s", type(disValue))
        logger.debug("extractDiscoveredValue:ADVA::disValue: %s", disValue)
        if (displayName == 'Vendor'):
            # print('Display value = ', disValue)
            extractDiscoveredValue = str(disValue).split(' ')[0].upper()
        elif (displayName == 'Family'):
            if '-' in str(disValue):
                extractDiscoveredValue = str(disValue).split('-')[0].strip().upper()
            elif ' ' in str(disValue):
                extractDiscoveredValue = str(disValue).split(' ')[0].strip().upper()
            else:
                extractDiscoveredValue = str(disValue)
            extractDiscoveredValue = ''.join(extractDiscoveredValue).upper().strip()
        elif (displayName == 'Hostname'):
            extractDiscoveredValue = str(disValue)
            extractDiscoveredValue = ''.join(extractDiscoveredValue).upper().strip()
        elif (displayName == 'Model'):  # e.g.  = STRING: "Juniper VSRX Internet Router"
            if '-' in str(disValue):
                extractDiscoveredValue = str(disValue).split('-')[1].strip().upper()
            elif ' ' in str(disValue):
                extractDiscoveredValue = str(disValue).split(' ')[1].strip().upper()
            else:
                extractDiscoveredValue = str(disValue)
            extractDiscoveredValue = ''.join(extractDiscoveredValue).upper().strip()
        elif (displayName == 'OS Version'):  # e.g.  = STRING: "JUNOS Base OS Software Suite [20.4R2.7]"
            extractDiscoveredValue = str(disValue)
            extractDiscoveredValue = ''.join(extractDiscoveredValue).upper().strip()
        elif (displayName == 'OSPNF'):  # e.g.  = STRING: "JUNOS Base OS Software Suite [20.4R2.7]"
            extractDiscoveredValue = str(disValue).split(' ')[0]
            extractDiscoveredValue = ''.join(extractDiscoveredValue).upper().strip()
        elif (displayName == 'OSVNF'):
            # print('inside os detail =',disValue)
            extractDiscoveredValue = str(disValue).replace('\r', '').replace('\n', '')
            extractDiscoveredValue = str(extractDiscoveredValue).split(' ', 2)[0]
            extractDiscoveredValue = ''.join(extractDiscoveredValue).upper().strip()
        elif (displayName == 'Software Image'):
            # print('Inside SOftware Image', disValue)
            extractDiscoveredValue = str(disValue).split('/', 2)[2]
            extractDiscoveredValue = ''.join(extractDiscoveredValue).upper().strip()
            # print('Inside SOftware Image Out', extractDiscoveredValue)
        else:
            extractDiscoveredValue = disValue.prettyPrint()

    elif disVendor.upper() == 'VYOS':
        logger.debug("extractDiscoveredValue:vyos::disValue: %s", disValue)
        extractDiscoveredValue = str(disValue)
    
    elif disVendor.upper() == 'Nokia':

        logger.debug("extractDiscoveredValue:Nokia::Type disValue: %s", type(disValue))
        logger.debug("extractDiscoveredValue:Nokia::disValue: %s", disValue)
        if (displayName == 'Vendor'):
            # print('Display value = ', disValue)
            extractDiscoveredValue = str(disValue).split(' ')[2].upper()

        elif (displayName == 'Family'):
            if '-' in str(disValue):
                extractDiscoveredValue = str(disValue).split(' ')[3].strip().upper()
                print(extractDiscoveredValue)
                print(extractDiscoveredValue)
            elif ' ' in str(disValue):
                extractDiscoveredValue = str(disValue).split(' ')[0].strip().upper()
            else:
                extractDiscoveredValue = str(disValue)
            extractDiscoveredValue = ''.join(extractDiscoveredValue).upper().strip()
        elif (displayName == 'Hostname'):
            extractDiscoveredValue = str(disValue)
            extractDiscoveredValue = ''.join(extractDiscoveredValue).upper().strip()
            print(extractDiscoveredValue)
        elif (displayName == 'Model'):  # e.g.  = STRING: "Juniper VSRX Internet Router"
            if '-' in str(disValue):
                extractDiscoveredValue = str(disValue).split(' ')[1].strip().upper()
            elif ' ' in str(disValue):
                extractDiscoveredValue = str(disValue).split(' ')[1].strip().upper()
            else:
                extractDiscoveredValue = str(disValue)
            extractDiscoveredValue = ''.join(extractDiscoveredValue).upper().strip()
        elif (displayName == 'OS Version'):  # e.g.  = STRING: "JUNOS Base OS Software Suite [20.4R2.7]"
            extractDiscoveredValue = str(disValue)
            extractDiscoveredValue = str(disValue).split(' ')[0].upper()
        elif (displayName == 'OSPNF'):  # e.g.  = STRING: "JUNOS Base OS Software Suite [20.4R2.7]"
            # extractDiscoveredValue = str(disValue).split(' ')[0]
            # extractDiscoveredValue = str(disValue).split(' ')[0].upper()
            extractDiscoveredValue = "SROS"
        elif (displayName == 'OSVNF'):
            # print('inside os detail =',disValue)
            extractDiscoveredValue = str(disValue).replace('\r', '').replace('\n', '')
            extractDiscoveredValue = str(extractDiscoveredValue).split(' ', 2)[0]
            extractDiscoveredValue = ''.join(extractDiscoveredValue).upper().strip()
        elif (displayName == 'Software Image'):
            # print('Inside SOftware Image', disValue)
            extractDiscoveredValue = str(disValue).split('/', 2)[2]
            extractDiscoveredValue = ''.join(extractDiscoveredValue).upper().strip()
            # print('Inside SOftware Image Out', extractDiscoveredValue)
        else:
            extractDiscoveredValue = disValue.prettyPrint()

            # Orginal Code is as Below 01/Sept/2021 - Sujit
    # if ((disValue == ' ') or (disValue is None) or (len(str(disValue)) == 0)):
    #     extractDiscoveredValue='Not Available'
    # else:
    #     if (displayName == 'Vendor'):
    #         #print('Display value = ', disValue)
    #         extractDiscoveredValue = str(disValue).split(' ',2)[0]
    #     elif(displayName == 'Family'):
    #         extractDiscoveredValue = str(disValue).split(' ',2)[1]
    #     elif(displayName == 'Hostname'):
    #         extractDiscoveredValue = str(disValue).split('.',2)[0]
    #     elif(displayName == 'OSPNF'):
    #         #print('inside os =',disValue)
    #         extractDiscoveredValue = str(disValue).replace(',',' ', 2)
    #         extractDiscoveredValue = str(extractDiscoveredValue).split(' ',2)[1]
    #     elif(displayName == 'OSVNF'):
    #         #print('inside os detail =',disValue)
    #         extractDiscoveredValue = str(disValue).replace('\r','').replace('\n','')
    #         extractDiscoveredValue = str(extractDiscoveredValue).split(' ',2)[0]
    #     elif(displayName == 'Software Image'):
    #         #print('Inside SOftware Image', disValue)
    #         extractDiscoveredValue = str(disValue).split('/',2)[2]
    #         #print('Inside SOftware Image Out', extractDiscoveredValue)
    #     else:
    #         extractDiscoveredValue = disValue.prettyPrint()

    return extractDiscoveredValue


# ************************ Perform Inv is exist or not before SNMPGET  ******************************

# ************************ Main  ******************************
def c3pDiscovery(inArgv):
    statusGet = 'N'
    statusWalk = 'N'
    statusResStep1 = 'N'
    statusDiscovery = 'N'
    newDevice = ''
    sDT = datetime.today().strftime('%Y-%m-%d %H:%M:%S')
    res = []
    in_argv = []
    in_argv = list(inArgv)
    logger.debug('c3pDiscovery :: argv :: %s', in_argv)

    logger.debug('c3pDiscovery :: No of arguments : %s', len(sys.argv))

    arg_mgmtIP = in_argv[0]
    arg_community = str.lower(in_argv[2])
    arg_discoveryID = in_argv[1]
    arg_deviceID = in_argv[3]
    arg_vendor = in_argv[4]
    arg_NetworkType = in_argv[5]
    arg_hostname = in_argv[6]
    arg_createdBy = in_argv[7]
    arg_sourceSystem = in_argv[8]

    # print('discovery Type   :: ', arg_discoveryType)
    # print('ipType   :: ', arg_ipType)

    logger.debug('c3pDiscovery :: MgmtIP        :: %s', arg_mgmtIP)
    logger.debug('c3pDiscovery :: Community     :: %s', arg_community)
    logger.debug('c3pDiscovery :: dis ID        :: %s', arg_discoveryID)
    logger.debug('c3pDiscovery :: device ID     :: %s', arg_deviceID)
    logger.debug('c3pDiscovery :: Vendor        :: %s', arg_vendor)
    logger.debug('c3pDiscovery :: N/W Type      :: %s', arg_NetworkType)
    logger.debug('c3pDiscovery :: hostname      :: %s', arg_hostname)
    logger.debug('c3pDiscovery :: Cretead By    :: %s', arg_createdBy)
    logger.debug('c3pDiscovery :: SourceSystem  :: %s', arg_sourceSystem)

    # arg_discoveryType= in_argv["discoveryType"],
    # arg_ipType      = in_argv["ipType"],
    # arg_mgmtIP      = in_argv["mgmtip"]
    # arg_community   = str.lower(in_argv["community"])
    # arg_discoveryID = in_argv["discoveryID"]
    # arg_deviceID    = in_argv["deviceID"]
    # arg_vendor      = in_argv["vendor"]
    # arg_NetworkType = in_argv["networktype"]

    # print('arg_community = ', arg_community)

    # ********************************************************

    if (arg_deviceID == '#'):
        logger.debug('c3pDiscovery :: Serach for Vendor and Hostname')
        # Generic OIDs to get Vendor and Hostname of the new resource
        oid_hostname = '1.3.6.1.2.1.1.5.0'
        oid_vendor = '1.3.6.1.2.1.47.1.1.1.1.2.1'  # OID to get Device's vendor and network type information
        # oid_vendor = '.1.3.6.1.2.1.1.1.0'

        vendorVal = SnmpDRN2.search_Value(arg_mgmtIP, arg_community, 'Vendor', oid_vendor)
        # print(' Value : ', vendorVal)

        if vendorVal is not None:
            # print('Alternative OID for Vendor ....')
            oid_vendor = '1.3.6.1.2.1.1.1.0'
            # oid_vendor= '.1.3.6.1.2.1.1.1.0'
            vendorVal = SnmpDRN2.search_Value(arg_mgmtIP, arg_community, 'Vendor', oid_vendor)

        # print('Vendor = ', vendorVal)

        hostName = SnmpDRN2.search_Value(arg_mgmtIP, arg_community, 'Hostname', oid_hostname)
        arg_hostname = hostName
        # print('Hostname = ', hostName)

        # networktype = 'PNF'                     # Assumption

        if (vendorVal != 'C3P-DR-504'):
            validVendor = SnmpDRN2.check_VendorValidity(vendorVal)
        else:
            validVendor = 'N'
        logger.debug('c3pDiscovery :: Valid Vendor %s', validVendor)
        if (validVendor == 'Y'):
            if (arg_sourceSystem == 'c3p-ui'):
                device_id = SnmpDRN2.create_new_resource(arg_mgmtIP, hostName, vendorVal)
            else:
                device_id = int(str('9') + ''.join(random.choices(string.digits, k=2)) + str(datetime.today().strftime(
                    '%H%M%S')))  # Format 9NNHHMMSS Generate the dummy device id for external system

            logger.debug('c3pDiscovery :: New resource Id .....device_id-%s hostName-%s vendorVal-%s', device_id,
                         hostName, vendorVal)

            arg_deviceID = device_id
            newDevice = 'New'
            arg_vendor = vendorVal
            # arg_NetworkType = 'PNF'             # Check for Hard coded value
            if arg_NetworkType == '#':
                arg_NetworkType = 'PNF'

            statusGet = SnmpDRN2.c3psnmpGet(arg_mgmtIP, arg_community, arg_discoveryID, device_id, vendorVal, arg_NetworkType,
                                   arg_sourceSystem)

            if (statusGet == '0'):
                logger.debug('c3pDiscovery :: Get : Completed ')
                statusWalk = SnmpDRN2.c3psnmpWalk(arg_mgmtIP, arg_community, arg_discoveryID, device_id, vendorVal,
                                         arg_NetworkType, arg_sourceSystem)

                if (statusWalk == '0' and arg_sourceSystem == "c3p-ui"):
                    logger.debug('c3pDiscovery :: ##0 1 ## c3pDiscovery Walk :: Completed')

                    statusResStep1 = SnmpDRN2.c3pInterfaceReconcilationStep1(arg_mgmtIP, arg_community, arg_discoveryID,
                                                                    device_id, vendorVal, arg_NetworkType, newDevice)

                    if (statusResStep1 == '0'):
                        logger.debug('c3pDiscovery :: ## 1 ## Interface Reconcialtion Step 1 : Completed')

                        reqData = {
                            "mgmtip": arg_mgmtIP,
                            "hostname": "",
                            "device_id": arg_deviceID,
                            "topology": "ALL",
                            "operation": "RLT",
                            "sourcesystem": arg_sourceSystem
                        }
                        cltRes = CLT.create_logical_topology(reqData)
                        logger.debug('c3pDiscovery :: ## Topology Build ## For C3P-UI Application :: %s', cltRes)
                        if (cltRes == 'C3P-DR-201'):  # and respF.status_code == C3P-DR-201
                            # finalResult='Topology :: Send :: Ok'
                            logger.debug('c3pDiscovery :: Discovery : Completed')
                            statusDiscovery = 'C3P-DR-200'
                        else:
                            statusDiscovery = 'C3P-DR-500'
                            # finalResult='Topology :: Send :: Error'
                        logger.debug('c3pDiscovery :: Topology For C3P-UI Application :: statusDiscovery : %s',
                                     statusDiscovery)

                        """ Topology Builder """

                        logger.debug('c3pDiscovery :: Discovery : Completed')
                        statusDiscovery = 'C3P-DR-200'
                    else:
                        logger.debug('c3pDiscovery :: ## 1 ## Interface Reconcialtion Step 1 : Error')
                        logger.debug('c3pDiscovery :: Discovery : Error')
                        statusDiscovery = 'C3P-DR-530'
                elif (statusWalk == '0' and arg_sourceSystem != "c3p-ui"):
                    logger.debug(
                        'c3pDiscovery ::  ## 1 ## c3pDiscovery Walk :: Completed, Interface Reconcialtion Not required')
                    # date 23/05/2021 : Logic to prepre Topology view for external application
                    # storing interface data into in a table ( replica of c3p_t_fork_inv_discrepancy ) for an external application
                    #
                    c3pInterfaceDataforExtSystem(arg_mgmtIP, arg_community, arg_discoveryID, arg_deviceID, arg_vendor,
                                                 arg_NetworkType, newDevice)
                    #
                    # Logic End
                    res = sendRecToExt(arg_deviceID, arg_mgmtIP, arg_discoveryID, arg_vendor, arg_NetworkType,
                                       arg_hostname, newDevice)
                    logger.debug('c3pDiscovery :: ## 1 ## For External Application :: %s', res)

                    reqData = {
                        "mgmtip": arg_mgmtIP,
                        "hostname": "",
                        "device_id": arg_deviceID,
                        "topology": "ALL",
                        "operation": "RLT",
                        "sourcesystem": arg_sourceSystem
                    }
                    # logger.debug('c3pDiscovery :: ## 1 ## For External Application :: %s', cltRes)
                    cltRes = CLT.create_logical_topology(reqData)
                    if (cltRes == 'C3P-DR-201'):  # and respF.status_code == C3P-DR-201
                        # finalResult='Topology :: Send :: Ok'
                        statusDiscovery = 'C3P-DR-200'
                    else:
                        statusDiscovery = 'C3P-DR-500'
                        # finalResult='Topology :: Send :: Error'
                    logger.debug('c3pDiscovery :: Topology to External Application :: statusDiscovery : %s',
                                 statusDiscovery)

                    # print('CLT :: Final Result ::%s',statusDiscovery)
                else:
                    logger.debug('c3pDiscovery :: Walk      : Error')
                    logger.debug('c3pDiscovery :: Discovery : Error')
                    statusDiscovery = 'C3P-DR-520'
            else:
                logger.debug('c3pDiscovery :: Get       : Error')
                logger.debug('c3pDiscovery :: Discovery : Error')
                statusDiscovery = 'C3P-DR-510'
        else:
            if (vendorVal != 'C3P-DR-504'):
                logger.debug('c3pDiscovery :: Please follow the onboarding process for a new vendor : %s', vendorVal)
                arg_vendor = vendorVal
                arg_deviceID = 0
                statusDiscovery = 'C3P-DR-401'
            else:
                logger.debug('c3pDiscovery :: No connection with Resource : %s', arg_mgmtIP)
                arg_vendor = vendorVal
                arg_deviceID = 0
                statusDiscovery = 'C3P-DR-504'
    else:
        # print(' c3pDiscovery :: All arguments are provided *************')
        statusGet = SnmpDRN2.c3psnmpGet(arg_mgmtIP, arg_community, arg_discoveryID, arg_deviceID, arg_vendor, arg_NetworkType,
                               arg_sourceSystem)
        # SnmpDRN2.update_ResourceInfo(in_arg[1], in_arg[4], in_arg[5],in_arg[6])
        if (statusGet == '0'):
            logger.debug('c3pDiscovery ::  Get : Completed ')
            statusWalk = SnmpDRN2.c3psnmpWalk(arg_mgmtIP, arg_community, arg_discoveryID, arg_deviceID, arg_vendor,
                                     arg_NetworkType, arg_sourceSystem)

            if (statusWalk == '0' and arg_sourceSystem == "c3p-ui"):
                logger.debug('c3pDiscovery :: ## 2 ## c3pDiscovery Walk :: Completed')
                statusResStep1 = SnmpDRN2.c3pInterfaceReconcilationStep1(arg_mgmtIP, arg_community, arg_discoveryID,
                                                                arg_deviceID, arg_vendor, arg_NetworkType, newDevice)
                if (statusResStep1 == '0'):
                    """ Topology Builder """
                    logger.debug('c3pDiscovery :: ## 2 ## Interface Reconcialtion Step 1 : Completed')
                    reqData = {
                        "mgmtip": arg_mgmtIP,
                        "hostname": "",
                        "device_id": arg_deviceID,
                        "topology": "ALL",
                        "operation": "RLT",
                        "sourcesystem": arg_sourceSystem
                    }
                    cltRes = CLT.create_logical_topology(reqData)
                    logger.debug('c3pDiscovery :: ## Topology Build ## For C3P-UI Application :: %s', cltRes)
                    if (cltRes == 'C3P-DR-201'):  # and respF.status_code == C3P-DR-201
                        # finalResult='Topology :: Send :: Ok'
                        logger.debug('c3pDiscovery :: Discovery : Completed')
                        statusDiscovery = 'C3P-DR-200'
                    else:
                        statusDiscovery = 'C3P-DR-500'
                        # finalResult='Topology :: Send :: Error'
                    logger.debug('c3pDiscovery :: Topology For C3P-UI Application :: statusDiscovery : %s',
                                 statusDiscovery)

                    """ Topology Builder """
                else:
                    logger.debug('c3pDiscovery :: ## 2 ## Interface Reconcialtion Step 1 : Error')
                    logger.debug('c3pDiscovery :: ## 3 ## Topology View is not build : Error')
                    logger.debug('c3pDiscovery :: Discovery : Error')
                    statusDiscovery = 'C3P-DR-530'
            elif (statusWalk == '0' and arg_sourceSystem != "c3p-ui"):
                logger.debug(
                    'c3pDiscovery :: ## 2 ##  c3pDiscovery Walk :: Completed, Interface Reconcialtion Not required')
                # date 23/05/2021 : Logic to prepre Topology view for external application
                # storing interface data into in a table ( replica of c3p_t_fork_inv_discrepancy ) for an external application
                #
                c3pInterfaceDataforExtSystem(arg_mgmtIP, arg_community, arg_discoveryID, arg_deviceID, arg_vendor,
                                             arg_NetworkType, newDevice)
                #
                # Logic End
                res = sendRecToExt(arg_deviceID, arg_mgmtIP, arg_discoveryID, arg_vendor, arg_NetworkType, arg_hostname,
                                   newDevice)
                logger.debug('c3pDiscovery :: ## 2 ## For External Application :: %s ??? Device ?? %s', res, newDevice)

                reqData = {
                    "mgmtip": arg_mgmtIP,
                    "hostname": "",
                    "device_id": arg_deviceID,
                    "topology": "ALL",
                    "operation": "RLT",
                    "sourcesystem": arg_sourceSystem
                }
                cltRes = CLT.create_logical_topology(reqData)
                logger.debug('c3pDiscovery :: ## 1 ## For External Application :: %s', cltRes)
                if (cltRes == 'C3P-DR-201') or (cltRes == 200):  # and respF.status_code == C3P-DR-201
                    # finalResult='Topology :: Send :: Ok'
                    statusDiscovery = 'C3P-DR-200'
                else:
                    statusDiscovery = 'C3P-DR-500'
                    # finalResult='Topology :: Send :: Error'
                logger.debug('c3pDiscovery :: Topology to External Application :: statusDiscovery : %s',
                             statusDiscovery)

                logger.debug('CLT :: Final Result ::%s', statusDiscovery)


            else:
                logger.debug('c3pDiscovery :: Walk : Error')
                logger.debug('c3pDiscovery :: Discovery : Error')
                statusDiscovery = 'C3P-DR-520'
        else:
            logger.debug('c3pDiscovery :: Get : Error')
            logger.debug('c3pDiscovery :: Discovery : Error')
            statusDiscovery = 'C3P-DR-510'
    # else:
    # print('Incorrect list of arguments ' )
    # print('Discovery : Error' )
    # disResult = 'Pass'

    disResult = (arg_mgmtIP, arg_community, arg_discoveryID,
                 arg_deviceID, newDevice, arg_vendor, arg_NetworkType, statusGet, statusWalk,
                 statusResStep1, statusDiscovery, sDT, datetime.today().strftime('%Y-%m-%d %H:%M:%S'), arg_hostname,
                 arg_createdBy, arg_sourceSystem, res)
    logger.debug('c3pDiscovery :: disResult %s', disResult)
    return disResult


def sendRecToExt(seDId, seMgmtId, seDisId, seVendor, seDType, seHost, seNewD):
    sehOid = []
    foids = []
    disId = ''
    result = {}
    newHeaders = {"Content-type": "application/json", "Accept": "application/json"}
    url = configs.get("SNow_C3P_Imp_Inventory")
    finalResult = ''
    mydb = Connections.create_connection()
    try:
        mycursor = mydb.cursor(buffered=True)
        sql = "SELECT hdr_ip_address, device_id, hdr_oid_no, hdr_discovered_value, hdr_discovery_id, dis_dash_id, dis_name, hdr_display_name FROM c3p_t_host_discovery_result, c3p_t_discovery_dashboard WHERE device_id = '" + str(
            seDId) + "' AND hdr_discovery_id = '" + str(seDisId) + "' AND hdr_discovery_id = dis_row_id"

        try:
            mycursor.execute(sql)
            myresult = mycursor.fetchall()
        except mysql.connector.errors.ProgrammingError as e:
            logger.error('sendRecToExt :: Exception %s', e)
            return ('1')

        for t in myresult:
            disId = t[5]  # dis_dash_id
            sehOid.append({configs.get("Imp_Inventory_OId"): t[2], configs.get("Imp_Inventory_Value"): t[3],
                           configs.get("Imp_Inventory_DisplayName"): t[7]})  # hdr_oid_no, hdr_discovered_value

        # print("sendRecToExt Host data :: ", sehOid)

        if (seNewD == 'New'):
            vDId = ''  # send blank value in case its newly discovered device
        else:
            vDId = seDId  # for existing device id in DB
        result = {
                     configs.get("Imp_Inventory_Id"): vDId,
                     configs.get("Imp_Inventory_Host_Name"): seHost,
                     configs.get("Imp_Inventory_Mgmt_Ip"): seMgmtId,
                     configs.get("Imp_Inventory_Discovery_Id"): disId,
                     configs.get("Imp_Inventory_OId_Name_Value"): sehOid,
                     configs.get("Imp_Inventory_Source"): "C3P",
                     configs.get("Imp_Inventory_Vendor"): seVendor,
                     configs.get("Imp_Inventory_Device_Type"): seDType
                 },

        # call service now api here for discovery push in JSON format

        data_json = json.dumps(result)
        # print('data_json', data_json)
        logger.debug('data_json :: %s', data_json)

        respH = requests.post(url, data=data_json, headers=newHeaders,
                              auth=HTTPBasicAuth(configs.get("SNow_C3P_User"),
                                                 configs.get("SNow_C3P_Password")))
        # logger.debug('sendRecToExt Host resp ::  %s', respH.json())
        logger.debug('sendRecToExt :: External System Status Code respH :: %s', respH.status_code)

        """ 
        ******************** For Folk *********************
        """
        sqlFork = "SELECT fdr_ip_address, device_id, fdr_oid_no, fdr_child_oid_no, fdr_discovered_value, fdr_discovery_id, dis_dash_id, dis_name FROM c3p_t_fork_discovery_result, c3p_t_discovery_dashboard WHERE device_id = '" + str(
            seDId) + "' AND fdr_discovery_id = '" + str(seDisId) + "' AND fdr_discovery_id = dis_row_id"
        keyHead = ["u_management_ip", "u_id", "u_oid_name_value", "u_oid_child_name_value", "u_discovered_value",
                   "u_discovery_id", "u_dis_id", "u_dis_name"]
        # keyHead = ["u_oid_name_value", "u_oid_child_name_value", "u_discovered_value"]

        # mycursor=mydb.cursor(buffered=True)
        # print("sendRecToEx SQL = ", sqlFork)

        try:
            mycursor.execute(sqlFork)
            myresult = mycursor.fetchall()
        except mysql.connector.errors.ProgrammingError as err:
            logger.error('sendRecToExt :: Exception : %s', err)
            # return('1')

        for m in myresult:
            disId = m[6]  # dis_dash_id
            foids.append({configs.get("Imp_Inventory_OId_Name"): m[2],
                          configs.get("Imp_Inventory_OId_Child_Name"): m[3],
                          configs.get("Imp_Inventory_OId_Value"): m[4]})

            # print("sendRecToExt Fork data :: ", foids)

        if (seNewD == 'New'):
            vDId = ''  # send blank value in case its newly discovered device
        else:
            vDId = seDId  # for existing device id in DB

        resultFork = {
                         configs.get("Imp_Inventory_Id"): vDId,
                         configs.get("Imp_Inventory_Host_Name"): seHost,
                         configs.get("Imp_Inventory_Mgmt_Ip"): seMgmtId,
                         configs.get("Imp_Inventory_Discovery_Id"): disId,
                         configs.get("Imp_Inventory_OId_Name_Value"): foids,
                         configs.get("Imp_Inventory_Source"): "C3P",
                         configs.get("Imp_Inventory_Vendor"): seVendor,
                         configs.get("Imp_Inventory_Device_Type"): seDType
                     },

        # print('sendRecToExt Fork result :: ', resultFork)

        data_json = json.dumps(resultFork)
        respF = requests.post(url, data=data_json, headers=newHeaders,
                              auth=HTTPBasicAuth(configs.get("SNow_C3P_User"),
                                                 configs.get("SNow_C3P_Password")))
        # logger.debug('sendRecToExt Fork resp :: %s', respF.json())
        logger.debug('sendRecToExt External System Status Code respF :: %s', respF.status_code)
        # mycursor.close()
        if (respH.status_code == 201 and respF.status_code == 201):
            finalResult = 'Ok'
        else:
            finalResult = 'Error'
        logger.debug('sendRecToExt :: Exception Final Result : %s', finalResult)
    except Exception as err:
        logger.error("Exception in sendRecToExt: %s", err)
    finally:
        mydb.close
    return finalResult


def updateCountDiscrypancy():
    mydb = Connections.create_connection()
    try:
        mycursor = mydb.cursor(buffered=True)
        sql = ""
        try:
            mycursor.execute(sql)
            logger.debug('updateCountDiscrypancy :: Discripancy %s Count updated #1', mycursor.rowcount())
        except mysql.connector.errors.ProgrammingError as err:
            logger.error('updateCountDiscrypancy :: Exception #1 - %s', err)
            # return('1')
    except Exception as err:
        logger.error("updateCountDiscrypancy :: Exception #2 : %s", err)
    finally:
        mydb.close
    return True


""" Function to Perform for CARD and SLOT Interfaces """


def updateForkResultCardSlot(oList, vList):
    # def updateForkResultCardSlot():
    # # List = [['OID=.1.3.6.1.2.1.47.1.1.1.1.7.2', '', ' I/O and CPU Slot 0'], ['OID=.1.3.6.1.2.1.47.1.1.1.1.7.3', '', ' PA Slot 1'], ['OID=.1.3.6.1.2.1.47.1.1.1.1.7.4', '', ' PA Slot 2'], ['OID=.1.3.6.1.2.1.47.1.1.1.1.7.5', '', ' PA Slot 3'], ['OID=.1.3.6.1.2.1.47.1.1.1.1.7.6', '', ' PA Slot 4']]
    # oList = []
    nList = []
    nOID = '0'
    nVAL = ''
    mList4 = []
    mList5 = []
    mList6 = []
    mList7 = []
    mList13 = []
    mListI = []
    res = []
    x = []
    z = []
    kList = []
    entRelPos = {"1": "Other", "2": "Unknown", "3": "Chassis", "4": "Black Plane", "5": "Container",
                 "6": "Power Supply", "7": "Fan", "8": "Sensor", "9": "Module", "10": "Port", "11": "Stack",
                 "11": "CPU"}
    ''' below code is for offline testing purpose only. .csv holds the oid output '''
    # with open('D:/c3papp/000000000035913-c3p-python/c3papplication/discovery/Book2.csv',encoding='utf-8-sig') as f:
    #     r = csv.reader(f)
    #     #logger.debug('File Read :: %s',r)
    #     for row in r:
    #         try:
    #             rData = row[0].lstrip().replace(' = STRING: ', ',').replace('INTEGER: ',',').replace(' = ', ',').replace('"','').split(',')
    #             #logger.debug('rData ::%s', rData)
    #             oList.append(rData)
    #         except IndexError:
    #             pass
    #         #else:
    #             #print("Thanks")
    # print(oList)
    # kList = Olist

    for y in oList:
        x.append(y)

    for y in vList:
        z.append(y)

    kList = list(zip(x, z))
    # print('klist ::', kList)
    logger.debug('klist :: Generated %s')

    for y in kList:
        # print('y:::', y)
        if y[0].split('.')[-2] == '4':
            # print('y[0] ::',y[0], '<< y[0].split ::', y[0].split('.')[-1],'<< y[1] ::', y[1], '\n')
            out = [y[0], y[0].split('.')[-1], y[1]]
            mList4.append(out)
        elif y[0].split('.')[-2] == '5':
            # print('y[0] ::',y[0], '<< y[0].split ::', y[0].split('.')[-1],'<< y[1] ::', y[1], '\n')
            out = [y[0], y[0].split('.')[-1], y[1]]
            mList5.append(out)
        elif y[0].split('.')[-2] == '6':
            # print('y[0] ::',y[0], '<< y[0].split ::', y[0].split('.')[-1],'<< y[1] ::', y[1], '\n')
            out = [y[0], y[0].split('.')[-1], y[1]]
            mList6.append(out)
        elif y[0].split('.')[-2] == '7':
            # print('y[0] ::',y[0], '<< y[0].split ::', y[0].split('.')[-1],'<< y[1] ::', y[1], '\n')
            out = [y[0], y[0].split('.')[-1], y[1]]
            mList7.append(out)
        elif y[0].split('.')[-2] == '13':
            # print('13 #### y[0] ::',y[0], '<< y[0].split ::', y[0].split('.')[-1],'<< y[1] ::', y[1], '\n')
            out = [y[0], y[0].split('.')[-1], y[1]]
            mList13.append(out)
            # print('mlist13 ::', mList13)
        else:
            mListI.append(out)

    df4 = pd.DataFrame(mList4, columns=['OID4', 'indexID4', 'parentID4']).set_index('indexID4')  # , implace=True)
    # print('mList4 ::\n', df4)
    df5 = pd.DataFrame(mList5, columns=['OID5', 'indexID5', 'value5']).set_index('indexID5')  # , implace=True)
    # print('mList5 ::\n', df5)
    df6 = pd.DataFrame(mList6, columns=['OID6', 'indexID6', 'value6']).set_index('indexID6')  # , implace=True)
    # print('mList6 ::\n', df6)
    df7 = pd.DataFrame(mList7, columns=['OID7', 'indexID7', 'value7']).set_index('indexID7')  # , implace=True)
    # print('mList7 ::\n', df7)
    df13 = pd.DataFrame(mList13, columns=['OID13', 'indexID13', 'value13']).set_index('indexID13')  # , implace=True)
    # print('mList13 ::\n', df13)
    result = pd.concat([df4, df5, df6, df7, df13], axis=1, join="outer")
    # result = result.drop(result['value5'] == '8', axis=1, inplace=True)
    result = result.drop(result[(result['value5'] != '5') & (result['value5'] != '10') & (result['value5'] != '3') & (
            result['value5'] != '6') & (result['value5'] != '9')].index)
    # print('result ::', result)
    logger.debug('CARDSLOT :: result ::', result)
    for m in result.index:
        if (result['value5'][m] == '5') and ('mau' not in result['value7'][m]):
            res.append(processVal(m, result['value7'][m], 'ST'))
            # print(res)
        elif result['value5'][m] == '10':  # process as PORT
            res.append(processVal(m, result['value7'][m], 'PT'))
        elif (result['value5'][m] == '9') and ('mau' not in result['value7'][m]) and (
                result['value6'][m] != '1'):  # process as Module
            res.append(processVal(m, result['value7'][m], 'RE'))
        elif (result['value5'][m] == '3') and (result['value6'][m] == '0'):  # process as Chassis
            res.append(processVal(m, result['value7'][m], 'CH'))
        # print(res)

    dfres = pd.DataFrame(res, columns=['ires', 'nid']).set_index('ires')  # , implace=True)
    df = pd.concat([result, dfres], axis=1, join="inner")
    df = df.fillna('#')
    logger.debug('CARDSLOT :: DF Generated %s', df)
    # for n in df.index:
    #     nrOID = df['OID4'][n]
    #     #print('nrOID ::', nrOID)
    #     nOID = nrOID.replace(nrOID.split('.')[-1], df['nid'][n])
    #     nList.append([nOID, df['parentID4'][n]])
    # for n in df.index:
    #     nrOID = df['OID5'][n]
    #     #print('nrOID ::', nrOID)
    #     nOID = nrOID.replace(nrOID.split('.')[-1], df['nid'][n])
    #     nList.append([nOID, df['value5'][n]])
    # for n in df.index:
    #     nrOID = df['OID6'][n]
    #     #print('nrOID ::', nrOID)
    #     nOID = nrOID.replace(nrOID.split('.')[-1], df['nid'][n])
    #     nList.append([nOID, df['value6'][n]])
    for n in df.index:
        nrOID = str(df['OID7'][n])
        if df['nid'][n][0:2] != 'CH':
            nOID = nrOID.replace(nrOID.split('.')[-1], df['nid'][n])
            nList.append([nOID, df['value7'][n]])

    for n in df.index:
        nrOID = str(df['OID13'][n])
        if df['nid'][n][0:2] == 'CH':
            nOID = nrOID.replace(nrOID.split('.')[-1], df['nid'][n])
            nList.append([nOID, df['value13'][n]])

        if df['value13'][n] != "" and df['nid'][n][0:2] == 'RE' and df['value13'][n] is not None and df['value13'][
            n] != '#':
            val13 = df['nid'][n].replace(df['nid'][n][0:2], 'CT')
            nOID = nrOID.replace(nrOID.split('.')[-1], val13)
            # print("OID13 >>", nrOID, '<< nOID >>', nOID, '<< nid >>',df['nid'][n],'<< Value >>', df['value13'][n])
            nList.append([nOID, df['value13'][n]])

    # print('nList :: Completed %s', nList)
    # logger.debug('nList :: Completed %s', nList)
    ''' below code is offline testing purpose only. Generated the .csv file inside a .zip file as an output '''
    # pd.set_option('display.max_rows', None, 'display.max_rows', None)
    # compression_opts = dict(method='zip', archive_name='out2.csv')
    # df.to_csv('out2.zip', index=True, compression=compression_opts)
    return (nList)


""" CARD and SLOT Logic End """
"""
S : slot        : Holding a Slot Value which is Module 0
SS : Sub Slot   : 
P : Port
SN : Slot Name 
3/0/0 : S / SS / P 

S1P1
S1SS2P1

SLSSPO01XX01
SLPO11
SL1

1.3.6.1.2.1.47.1.1.1.1.7.SN5    PA SLOT 5        : Put in slot table 
1.3.6.1.2.1.47.1.1.1.1.7.CN5     module 5        : for reference only   RESL01SSXXPOXX  
1.3.6.1.2.1.47.1.1.1.1.13.CN5    PA-4T+=         : Put in Card Table

1.3.6.1.2.1.47.1.1.1.1.7.S1SS0P2 Serial1/0/2     : Entry in PORT Table  PTSL01SS00PO02   TableName+Slot+SubSlot+Port
1.3.6.1.2.1.47.1.1.1.1.7.S0P2    Serial0/2       : Entry in PORT Table  PTSL00SSXXPO02   TableName+Slot+SubSlot+Port
1.3.6.1.2.1.47.1.1.1.1.7.SN0     PA SLOT 0       : Entry in SLOT Table  STSL00SSXXPOXX   TableName+Slot+SubSlot+Port
1.3.6.1.2.1.47.1.1.1.1.13.CN0    PA-4T+=         : Entry in CARD Table  CTSL00SSXXPOXX   TableName+Slot+SubSlot+Port

SLOT / CARD : SUB SLOT : PORT
SN


"""


def processContainer(idx, value):
    # print('idx >>', idx, '<< value >>',value)
    nid = value
    return (idx, nid)


def processVal(idx, val, cT):
    cOID = ''
    # cT = tab
    cSL = ['X', 'X']
    cSS = ['X', 'X']
    cPO = ['X', 'X']
    # print('idx >>', idx, '<< value >>',val)

    valSplit = ''.join(val).split('/')
    # print('valSplit::', valSplit)
    # print('valSplit::<<', valSplit[-3],'>><<',valSplit[-2],'>><<', [-1],'>>')

    if ('/' in val and val.count('/') > 3 and cT == 'PT'):
        cSL = codeFormat(valSplit[-4])
        cSS = codeFormat(valSplit[-2])
        cPO = codeFormat(valSplit[-1])
    elif ('/' in val and val.count('/') >= 2 and val.count('/') <= 3 and cT == 'PT'):
        cSL = codeFormat(valSplit[-3])
        cSS = codeFormat(valSplit[-2])
        cPO = codeFormat(valSplit[-1])
        # print('cSL >>', cSL[1],cSL[0], 'cSS >>', cSS[1],cSS[0], 'cPO >>', cPO[1],cPO[0])
    elif ('/' in val and val.count('/') > 1 and cT == 'ST'):
        cSL = codeFormat(valSplit[-2])
        cSS = codeFormat(valSplit[-1])
    elif ('/' in val and val.count('/') >= 0 and val.count('/') <= 1 and cT == 'ST'):
        cSL = codeFormat(valSplit[-1])
    elif ('/' in val and val.count('/') >= 2 and val.count('/') < 3 and cT == 'RE'):
        cSL = codeFormat(valSplit[-2])
        cSS = codeFormat(valSplit[-1])
    elif (cT == 'CH' and 'chassis' in val):
        cT = 'CH'
    else:
        print('Error :: processVal :: Processing Error Idx >>', idx, '<< Val >>', val, '<< CT >>', cT)

    cOID = cT + 'SL' + str(cSL[1]) + str(cSL[0]) + 'SS' + str(cSS[1]) + str(cSS[0]) + 'PO' + str(cPO[1]) + str(cPO[0])
    #         print('updateForkResultCardSlot :: PORT Only ------%s', cOID)
    #         # +'SS'+str(cSS[1])+str(cSS[0])+'PO'+str(cPO[1])+str(cPO[0])
    # else:
    #     print('Port Table Error : Port Number is not a number')

    nid = cOID
    return (idx, nid)


''' 
    A code formatter Check the input code isdigit() process 
    else throws an error  
    also transfer code in tow digit format 
'''


def codeFormat(inc):
    outc = ['X', 'X']
    # print('inC>>', inc)
    if inc.isdigit():
        if int(inc) < 10:
            outc[0] = str(inc)
            outc[1] = str('0')
        else:
            outc[0] = str(inc[-1])
            outc[1] = str(inc[-2])
    else:
        # print('inc ::', inc[-2:])
        outc[0] = str(inc[-1])
        outc[1] = str(inc[-2])
    return (outc)


# """ CARD and SLOT Logic End """

""" date 23/05/2021 : Logic to prepre Topology view for external application
    storing interface data into in a table ( replica of c3p_t_fork_inv_discrepancy table ) for an external application
"""


def c3pInterfaceDataforExtSystem(irMgmtIP, irCommunity, irDiscoveryID, device_id, irVendor, irNetworkType, irNewDevice):
    invIntRec = []

    resolved_by = ''
    irDiscrepancyFlag = ''
    resolved_flag = ''
    myIntResult = []
    myIntRec = []
    irDate = datetime.today().strftime('%Y-%m-%d %H:%M:%S')
    mydb = Connections.create_connection()
    try:
        mycursor = mydb.cursor(buffered=True)
        sqlRes = "select fdr_oid_no, fdr_child_oid_no, fdr_discovery_id, fdr_discovered_value, fdr_href, c3p_m_oid_master_info.oid_m_compare_req_flag from c3p_t_fork_discovery_result, c3p_m_oid_master_info where fdr_ip_address='" + irMgmtIP + "' and device_id ='" + str(
            device_id) + "' and fdr_discovery_id='" + str(
            irDiscoveryID) + "' and fdr_oid_no = oid_m_no and oid_m_for_vendor = '" + irVendor + "'"
        try:
            mycursor.execute(sqlRes)
            myIntResult = mycursor.fetchall()  # Change
        except mysql.connector.errors.ProgrammingError as e:
            logger.error('c3pInterfaceDataforExtSystem :: Exception #1 : %s', e)
            return ('1')

        for t in myIntResult:
            # t[0]          : fdr_oid_no
            # t[1]          : fdr_child_oid_no

            irDiscoveredValue = t[3]
            irComparisonFlag = t[5]
            sql = "select fid_inv_existing_value from c3p_t_ext_fork_inv_discrepancy where fid_ip_address = '" + irMgmtIP + "' and device_id = '" + str(
                device_id) + "' and fid_oid_no = '" + t[0] + "' and fid_child_oid_no = '" + t[1] + "'"

            try:
                mycursor.execute(sql)
                myIntRec = mycursor.fetchall()  # change
            except mysql.connector.errors.ProgrammingError as e:
                logger.error('c3pInterfaceDataforExtSystem :: Exception #2 : %s', e)
                return ('1')
            print('Rowcount ################# = ', mycursor.rowcount)
            logger.debug('c3pInterfaceDataforExtSystem :: Rowcount : %s', mycursor.rowcount)

            if (mycursor.rowcount == 1):

                for m in myIntRec:

                    irExistingInvVal = m[0]
                    # irExistingDiscoveredVal = m[1]
                    logger.debug('c3pInterfaceDataforExtSystem :: OID                 : %s', t[0])
                    logger.debug('c3pInterfaceDataforExtSystem :: Child OID           : %s', t[1])
                    logger.debug('c3pInterfaceDataforExtSystem :: irExistingInvVal    : %s', irExistingInvVal)
                    logger.debug('c3pInterfaceDataforExtSystem :: irComparisonFlag    : %s', irComparisonFlag)
                    logger.debug('c3pInterfaceDataforExtSystem :: irDiscoveredValue   : %s', irDiscoveredValue)

                    irDiscrepancyFlag = '8'  # for external application
                    resolved_flag = 'Y'  # for external application
                    resolved_by = 'system'  # for external application

                    # if (irComparisonFlag == 'Y'):
                    #     if (( irDiscoveredValue is not None) and (irExistingInvVal is not None) and (irExistingInvVal == irDiscoveredValue)):
                    #         irDiscrepancyFlag = '0'
                    #     elif (irDiscoveredValue is None):
                    #         irDiscrepancyFlag = '1'
                    #     elif ((irDiscoveredValue is not None) and (irExistingInvVal is not None) and (irExistingInvVal is not irDiscoveredValue)):
                    #         irDiscrepancyFlag = '2'
                    #     elif ((irDiscoveredValue is not None) and (irExistingInvVal is None)):
                    #         irDiscrepancyFlag = '3'
                    # else:
                    #     irDiscrepancyFlag = '9'

                    # if ((irComparisonFlag == 'Y') and (irDiscrepancyFlag == '0')):
                    #     resolved_flag = 'Y'
                    # elif((irComparisonFlag == 'Y') and (irDiscrepancyFlag == '1')):
                    #     resolved_flag = 'N'
                    # elif((irComparisonFlag == 'Y') and (irDiscrepancyFlag == '2')):
                    #     resolved_flag ='N'
                    # elif((irComparisonFlag == 'Y') and (irDiscrepancyFlag == '3')):
                    #     resolved_flag ='N'
                    # elif (irComparisonFlag == 'N'):
                    #     resolved_flag = 'Y'

                    # if ((irComparisonFlag == 'Y') and (irDiscrepancyFlag == '0')):
                    #     resolved_by = 'system'
                    # elif((irComparisonFlag == 'N')):
                    #     resolved_by = 'system'

                    # sqlUpd="UPDATE c3p_t_fork_inv_discrepancy SET  fid_inv_prev_value = '"+str(irExistingInvVal)+"', fid_inv_existing_value = '"+str(irExistingDiscoveredVal)+"', fid_discovered_value = '"+irDiscoveredValue+"', fid_discrepancy_flag = '"+irDiscrepancyFlag+"', fid_updated_by = 'system', fid_updated_date = '"+datetime.today().strftime('%Y-%m-%d %H:%M:%S')+"', fid_discovery_id = '"+str(t[2])+"', fid_resolved_flag = '"+resolved_flag+"', fid_resolved_by = '"+resolved_by+"', fid_in_scope = 'Y'  where fid_ip_address = '"+irMgmtIP+"' and device_id = '"+str(device_id) +"' and fid_oid_no = '"+t[0]+"' and fid_child_oid_no = '"+t[1]+"'"
                    sqlUpd = "UPDATE c3p_t_ext_fork_inv_discrepancy SET  fid_discovered_value = '" + irDiscoveredValue + "', fid_discrepancy_flag = '" + irDiscrepancyFlag + "', fid_updated_by = 'system', fid_updated_date = '" + irDate + "', fid_discovery_id = '" + str(
                        t[
                            2]) + "', fid_resolved_flag = '" + resolved_flag + "', fid_resolved_by = '" + resolved_by + "', fid_in_scope = 'Y'  where fid_ip_address = '" + irMgmtIP + "' and device_id = '" + str(
                        device_id) + "' and fid_oid_no = '" + t[0] + "' and fid_child_oid_no = '" + t[1] + "'"

                    try:
                        mycursor.execute(sqlUpd)
                        print('c3pInterfaceDataforExtSystem :: Updated rowcount #1: %s', mycursor.rowcount)
                        logger.debug('c3pInterfaceDataforExtSystem :: Updated rowcount #1: %s', mycursor.rowcount)
                    except mysql.connector.errors.ProgrammingError as e:
                        print('c3pInterfaceDataforExtSystem :: Exception #3 : %s', e)
                        logger.error('c3pInterfaceDataforExtSystem :: Exception #3 : %s', e)
                        return ('1')

                    mydb.commit()
                    """ 23/05/21 Commenting below code as result table is not required for an external application """
                    # sqlUpdResult="UPDATE c3p_t_fork_discovery_result SET fdr_inv_existing_value ='"+str(irExistingInvVal)+"', fdr_discrepancy_flag = '"+irDiscrepancyFlag+"', fdr_updated_by = 'system', fdr_updated_date = '"+irDate+"' where fdr_ip_address = '"+irMgmtIP+"' and device_id = '"+str(device_id)+"' and fdr_oid_no = '"+t[0]+"' and fdr_child_oid_no = '"+t[1]+"' and fdr_discovery_id = '"+str(t[2])+"'"

                    # try:
                    #     mycursor.execute(sqlUpdResult)
                    #     logger.debug('c3pInterfaceDataforExtSystem :: Updated rowcount #2: %s', mycursor.rowcount)
                    # except mysql.connector.errors.ProgrammingError as e:
                    #     logger.error('c3pInterfaceDataforExtSystem :: Exception #4 : %s', e)
                    #     return('1')

                    # mydb.commit()

            else:
                irDiscrepancyFlag = '8'  # for external application
                resolved_flag = 'Y'  # for external application
                resolved_by = 'system'  # for external application
                # irDiscrepancyFlag =''
                irExistingInvVal = ''
                irhref = '/api/interface/' + str(device_id)

                # if ((irComparisonFlag == 'Y') and (irDiscoveredValue is not None)):
                #     irDiscrepancyFlag = '3'
                #     resolved_flag = 'N'
                # elif(irComparisonFlag == 'N'):
                #     irDiscrepancyFlag = '0'
                #     resolved_flag = 'Y'
                #     resolved_by = 'system'

                invIntVal = (
                irMgmtIP, device_id, t[0], t[1], t[3], irDiscrepancyFlag, irDiscoveryID, 'Y', 'system', irDate, irhref)

                sqlIns = "INSERT INTO c3p_t_ext_fork_inv_discrepancy (fid_ip_address, device_id, fid_oid_no, fid_child_oid_no, fid_discovered_value, fid_discrepancy_flag, fid_discovery_id, fid_in_scope, fid_created_by, fid_created_date, fid_href) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"

                try:

                    mycursor.execute(sqlIns, invIntVal)
                    logger.debug('c3pInterfaceDataforExtSystem :: Insert rowcount #3: %s', mycursor.rowcount)
                    print('c3pInterfaceDataforExtSystem :: Insert rowcount #3: %s', mycursor.rowcount)
                except mysql.connector.errors.ProgrammingError as e:
                    print('c3pInterfaceDataforExtSystem :: Exception #5 : %s', e)
                    logger.debug('c3pInterfaceDataforExtSystem :: Exception #5 : %s', e)
                    return ('1')

                mydb.commit()
            # Updating fork table
        sqlUpd = "UPDATE c3p_t_ext_fork_inv_discrepancy SET  fid_discovered_value = '', fid_discrepancy_flag = '1', fid_updated_by = 'system', fid_updated_date = '" + irDate + "', fid_discovery_id = '" + str(
            t[2]) + "', fid_resolved_flag = 'N'  where fid_ip_address = '" + irMgmtIP + "' and device_id = '" + str(
            device_id) + "' and  fid_in_scope = 'Y' and fid_discovery_id <> '" + str(t[2]) + "'"
        try:
            # logger.debug('c3pInterfaceDataforExtSystem  Fork SQL Query is  :: %s', sqlUpd)
            mycursor.execute(sqlUpd)
            logger.debug('c3pInterfaceDataforExtSystem  Fork :: %s records updated ', mycursor.rowcount)
        except mysql.connector.errors.ProgrammingError as e:
            logger.debug('c3pInterfaceDataforExtSystem  :: Fork Exception #6 : %s', e)
            return ('1')
        mydb.commit()

        # Updating host table
        # sqlUpd="UPDATE c3p_t_host_inv_discrepancy SET  hid_discovered_value = '', hid_discrepancy_flag = '1', hid_updated_by = 'system', hid_updated_date = '"+irDate+"', hid_discovery_id = '"+str(t[2])+"', hid_resolved_flag = 'N'  where hid_ip_address = '"+irMgmtIP+"' and device_id = '"+str(device_id)+"' and  hid_in_scope = 'Y' and hid_discovery_id <> '"+str(t[2])+"'"

        # try:
        #     #logger.debug('c3pInterfaceDataforExtSystem  Host SQL Query is  :: %s', sqlUpd)
        #     mycursor.execute(sqlUpd)
        #     logger.debug('c3pInterfaceDataforExtSystem  Host :: %s records updated ', mycursor.rowcount)
        # except mysql.connector.errors.ProgrammingError as e:
        #     logger.debug('c3pInterfaceDataforExtSystem :: Host Exception #7 : %s', e)
        #     return('1')
        # mydb.commit()

        # logger.debug('Is a New Device ? :: %s', irNewDevice)
        # if (irNewDevice == 'New'):                                                  # in case of new device, update the device info table else ignore the update
        #     updateRI = SnmpDRN2.update_ResourceInfo(irMgmtIP, device_id, irVendor, irNetworkType)
        #     if (updateRI=='0'):
        #         logger.debug('c3pInterfaceDataforExtSystem :: UpdateRI : Successful ')
        #         #return('0')
        #     else:
        #         logger.debug('c3pInterfaceDataforExtSystem :: UpdateRI : Error ')
        #         #return('1')
        # else:

        #     """ Code added to update the Discripancy Count in DeviceInfo Table """

        #     sql="UPDATE c3p_deviceinfo SET d_discrepancy = (SELECT ((SELECT count(fid_row_id) FROM c3p_t_fork_inv_discrepancy WHERE  fid_discrepancy_flag IN ('1','2','3') AND fid_in_scope= 'Y' AND fid_resolved_flag = 'N' AND device_id = '"+str(device_id)+"')+ (SELECT count(hid_row_id) FROM c3p_t_host_inv_discrepancy WHERE  hid_discrepancy_flag in ('1','2','3') AND hid_in_scope= 'Y' AND hid_resolved_flag = 'N' AND device_id = '"+str(device_id)+"')) from dual ) WHERE d_id = '"+str(device_id)+"'"
        #     try:
        #         #logger.debug('c3pInterfaceDataforExtSystem  Host SQL Query is  :: %s', sqlUpd)
        #         mycursor.execute(sql)
        #         logger.debug('c3pInterfaceDataforExtSystem :: discripancyCount Updated %s', mycursor.rowcount)
        #     except mysql.connector.errors.ProgrammingError as e:
        #         logger.debug('c3pInterfaceDataforExtSystem :: Exception #8 : %s', e)
        #         return('1')

        #     mydb.commit()


    except Exception as err:
        logger.error("c3pInterfaceDataforExtSystem :: Exception #9 : %s", err)
    finally:
        mydb.close
    return ('0')


def setDeviceRole(hostName, ipAddress):
    deviceRole = "NA"
    if (hostName != None):
        if ("-SPE" in hostName):
            deviceRole = "SPE"
        elif ("-NTU" in hostName):
            deviceRole = "NTU"
        elif ("-UNTU" in hostName):
            deviceRole = "UNTU"
        elif ("-SNTU" in hostName):
            deviceRole = "ACDC NTU"
        elif ("-AS" in hostName):
            deviceRole = "AGG SWITCH"
        elif (("-b" in hostName) or ("-B" in hostName)):
            deviceRole = "POPSwitch"
        elif (("-r" in hostName) or ("-R" in hostName)):
            deviceRole = "NCS/CRS"
        elif (("-e" in hostName) or ("-E" in hostName)):
            deviceRole = "AAPR"
        else:
            deviceRole = "NA"
    return updateDeviceRole(deviceRole, hostName)


def updateDeviceRole(deviceRole, deviceHostName):
    mydb = Connections.create_connection()
    mycursor = mydb.cursor(buffered=True)
    msg = ""
    try:
        mycursor.execute("SET SQL_SAFE_UPDATES = 0")
        query = "UPDATE c3p_deviceinfo set d_role = %s where d_hostname = %s;"
        mycursor.execute(query, (deviceRole, deviceHostName,))
        mycursor.execute("SET SQL_SAFE_UPDATES = 1")
        mydb.commit()
        msg = "Data Updated"

    except Exception as err:
        mydb.rollback()
        msg = "Data Not Updated"
        logger.debug(err)
    finally:
        mydb.close()
        logger.info(msg)
    return msg

def smnpv3AuthProtocol(Auth):
    try:
        if Auth.lower() == "noauth":
            AuthProtocal=(1, 3, 6, 1, 6, 3, 10, 1, 1, 1)
        elif Auth.lower() == "md5":
            AuthProtocal= (1, 3, 6, 1, 6, 3, 10, 1, 1, 2)
        elif Auth.lower() == "sha":
            AuthProtocal= (1, 3, 6, 1, 6, 3, 10, 1, 1, 3)
        elif Auth.lower() == "sha224":
            AuthProtocal= (1, 3, 6, 1, 6, 3, 10, 1, 1, 4)
        elif Auth.lower() == "sha256":
            AuthProtocal= (1, 3, 6, 1, 6, 3, 10, 1, 1, 5) 
        elif Auth.lower() == "sha384":
            AuthProtocal= (1, 3, 6, 1, 6, 3, 10, 1, 1, 6)
        elif Auth.lower() == "sha512":
            AuthProtocal= (1, 3, 6, 1, 6, 3, 10, 1, 1, 7)                                   
    except Exception as err:
        AuthProtocal=(1, 3, 6, 1, 6, 3, 10, 1, 1, 1)
        logger.error('Discovery:smnpv3AuthProtocol:: %s', err)
    return  AuthProtocal  

def smnpv3PrivProtocol(priv):
    try:
        if priv.lower() == "nopriv":
            privProtocal=(1, 3, 6, 1, 6, 3, 10, 1, 2, 1)
        elif priv.lower() == "des":
            privProtocal= (1, 3, 6, 1, 6, 3, 10, 1, 2, 2)
        elif priv.lower() == "3des":
            privProtocal= (1, 3, 6, 1, 6, 3, 10, 1, 2, 3)
        elif priv.lower() == "aes128":
            privProtocal= (1, 3, 6, 1, 6, 3, 10, 1, 2, 4)
        elif priv.lower() == "aes192":
            privProtocal= (1, 3, 6, 1, 4, 1, 9, 12, 6, 1, 101)
        elif priv.lower() == "aes256":
            privProtocal= (1, 3, 6, 1, 4, 1, 9, 12, 6, 1, 102)                            
    except Exception as err:
        privProtocal= (1, 3, 6, 1, 6, 3, 10, 1, 2, 1)
        logger.error('Discovery:smnpv3PrivProtocol:: %s', err)
    return  privProtocal 