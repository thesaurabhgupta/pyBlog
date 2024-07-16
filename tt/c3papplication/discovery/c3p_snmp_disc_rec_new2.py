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
from c3papplication.discovery import c3p_card_slot_gen as physicalinventorypopulator, c3p_snmp_disc_rec_new as CSDRN
from c3papplication.discovery import c3p_topology as CLT

logger = logging.getLogger(__name__)
configs = springConfig().fetch_config()


# ************************ c3psnmpGet ******************************
def c3psnmpGet(mgmtip, community, discovery_id, device_id, vendor, networktype, sourceSystem):
    # Variable definations
    discrepancyFlag = ''  # discrepancy flag
    # inv_existing_value  =   ''          # existing inventory value
    discovery_result = []
    mOidExVal = []
    mydb = Connections.create_connection()
    mycursor = mydb.cursor(buffered=True)
    sql = "SELECT cr_version, cr_login_read, cr_password_write, cr_enable_password, cr_encryption, cr_genric FROM c3p_m_credential_management WHERE cr_profile_name = %s AND cr_profile_type = 'SNMP'"
    values = (community,)
    mycursor.execute(sql, values)
    cred = mycursor.fetchone()
    logger.debug('Discovery:c3psnmpGet:cred :: %s', cred)
    community=cred[0]
    snmpv3username = cred[1]
    snmpv3authKey = cred[2]
    snmpv3privKey = cred[3]
    authProtocol = cred[4]
    privProtocol = cred[5]
    snmpv3authProtocol=CSDRN.smnpv3AuthProtocol(authProtocol)
    snmpv3privProtocol=CSDRN.smnpv3PrivProtocol(privProtocol)
    # logger.debug('Discovery:c3psnmpGet:credentials:: %s,%s,%s,%s,%s,%s', community,snmpv3username,snmpv3authKey,snmpv3privKey,snmpv3authProtocol,snmpv3privProtocol)

    logger.debug('c3psnmpGet - deviceid .... : %s', device_id)
    logger.debug('c3psnmpGet - vendor....... : %s', vendor)
    logger.debug('c3psnmpGet - networktype...: %s', networktype)

    result = ''
    # Check Inv is available for this device id or not. In case of external system not need to check inventory flag
    try:
        mycursor = mydb.cursor(buffered=True)
        invExistCheck = check_invExist(mgmtip, device_id) if (sourceSystem == 'c3p-ui') else 'N'
        
        if (invExistCheck == 'Y'):
            sql = "SELECT c3p_m_oid_master_info.oid_m_no, oid_m_category, oid_m_display_name, hid_inv_existing_value, hid_ip_address, oid_m_compare_req_flag, oid_m_map_attrib FROM c3p_m_oid_master_info LEFT JOIN c3p_t_host_inv_discrepancy ON oid_m_no = hid_oid_no WHERE oid_m_scope_flag = 'Y' AND oid_m_for_vendor = %s AND oid_m_network_type = %s AND oid_m_fork_flag = 'N' AND oid_m_category IN ('Host', 'Generic') and hid_display_name = oid_m_display_name AND c3p_t_host_inv_discrepancy.device_id = %s AND c3p_t_host_inv_discrepancy.hid_ip_address = %s"
            values = (vendor, networktype, str(device_id), mgmtip)
        else:
            sql = "SELECT d_vendor,d_device_family,d_model,d_os,d_os_version,d_hostname,d_macaddress,d_serial_number from c3p_deviceinfo WHERE d_id = %s"
            values = (str(device_id),)
            try:
                mycursor.execute(sql, values)
                if (mycursor.rowcount > 0):
                    data_dInfo = pd.DataFrame(mycursor.fetchall())
                    data_dInfo.columns = mycursor.column_names
                    logger.debug('****** ResourceInfo :: data Resource info Columns : Output::%s', data_dInfo)
            except Exception as e:
                logger.error("c3psnmpGet :: Device Info Exception : %s", e)
                result = '1'

            sql = "SELECT oid_m_no, oid_m_category, oid_m_display_name,'-@-', %s, oid_m_compare_req_flag, oid_m_map_attrib FROM c3p_m_oid_master_info where oid_m_scope_flag = 'Y' and oid_m_for_vendor = %s and oid_m_network_type = %s and oid_m_fork_flag ='N' and oid_m_category in ('Host', 'Generic')"
            values = (mgmtip, vendor, networktype)

        try:
            mycursor.execute(sql, values)
            mOidExVal = mycursor.fetchall()

        except Exception as e:
            logger.error("c3psnmpGet :: Exception : %s", e)
            result = '1'
        logger.debug("c3psnmpGet :: mOidExVal : %s", mOidExVal)
        for x in mOidExVal:
            value = x[0]
            existResInvValue = x[3]
            existFlag = ''
            if community.lower() != 'snmpv3':
                security_model = cmdgen.CommunityData('server', snmpv3username, 1)  # For SNMP security model  V2
                logger.debug("security_model snmpv2: %s", community.lower())
            elif community.lower() == 'snmpv3':
                security_model = cmdgen.UsmUserData(snmpv3username, snmpv3authKey, snmpv3privKey, snmpv3authProtocol,
                                                    snmpv3privProtocol)  # For SNMP security model  V3
                logger.debug("security_model is snmpv3: %s", community.lower())

            generator = cmdgen.CommandGenerator()
            security_model
            transport = cmdgen.UdpTransportTarget((mgmtip, 161))

            real_fun = getattr(generator, 'getCmd')
            res = (errorIndication, errorStatus, errorIndex, varBinds) \
                = real_fun(security_model, transport, x[0])

            logger.debug('c3psnmpget :: res :: %s', res)
            logger.debug('c3psnmpget :: varBinds :: %s', varBinds)

            if not errorIndication is None or errorStatus is True:
                logger.debug('c3psnmpget - 2 errorIndication- %s', errorIndication)
                # logger.error("c3psnmpGet :: %s at %s"  (errorStatus, errorIndex and varBinds[int(errorIndex) - 1][0] or '?'))
                print('c3psnmpGet :: %s at %s' % (errorStatus, errorIndex and varBinds[int(errorIndex) - 1][0] or '?'))
                # snmpGet_Status       = 'Error'
                # snmpGet_Status_Code  = errorStatus
                # raise snmpError(errorStatus)
                result = '1'
                break
            else:
                for varBind in varBinds:  # varBind has type ObjectType
                    # logger.debug('OID :: %s', x[0], '   Display Name :: %s', x[2], '    Value received :: %s', varBind[1])
                    # print('OID :: %s', x[0], '   Display Name :: %s', x[2], '    Value received :: %s', varBind[1])
                    if (x[2] == 'OS'):
                        reqOSDis = x[2] + networktype
                        discoveredValue = CSDRN.extract_discoveryValue(reqOSDis, varBind[1],
                                                                 vendor)  # 01-Sept-21 Added Parameter Vendor
                        logger.debug('#### OS :: %s', reqOSDis)
                    else:
                        discoveredValue = CSDRN.extract_discoveryValue(x[2], varBind[1],
                                                                 vendor)  # 01-Sept-21 Added Parameter Vendor

                    logger.debug('GET OID                   ::%s', x[0])
                    logger.debug('GET Display Name          ::%s', x[2])
                    logger.debug('GET Post Extraction       ::%s', discoveredValue)
                    logger.debug('GET Existing value        ::%s', existResInvValue)  # x[3]
                    logger.debug('GET Comparison Flag value ::%s', x[5])
                    logger.debug('GET attrib map value      ::%s', x[6])

                    if (sourceSystem == 'c3p-ui'):
                        logger.debug('c3psnmpGet ::  sourceSystem      ::%s', sourceSystem)
                        if existResInvValue == '-@-':
                            # print('x[6] >>>>', x[6], '<<Test>>','>>>>',''.join(x[6]))
                            logger.debug('c3psnmpGet ::  inside existResInvValue      ::')
                            # logger.debug('x[6] >>>>%s', x[6], '<<Test>>','>>>>%s',''.join(x[6]))
                            if ((len(x[6]) > 0) and (x[6] != 'None')):
                                logger.debug('c3psnmpGet ::  length existResInvValue      ::')
                                existResInvValue = ''.join(data_dInfo[x[6]].values)
                                logger.debug('c3psnmpGet ::  existResInvValue      ::%s', existResInvValue)
                            else:
                                logger.debug('c3psnmpGet ::  iam here      ::%s', existResInvValue)
                        else:
                            logger.debug('c3psnmpGet ::  existResInvValue >>>> %s', existResInvValue)

                        if (x[5] == 'Y'):  # x[5] is comparison flag
                            logger.debug('c3psnmpGet ::  Comparison Flag value      ::')
                            if existResInvValue == '-@-':
                                if discoveredValue is not None:
                                    discrepancyFlag = '3'
                            elif existResInvValue is not None:
                                if discoveredValue is not None:
                                    if existResInvValue == discoveredValue:
                                        discrepancyFlag = '0'
                                    else:
                                        discrepancyFlag = '2'
                                else:
                                    discrepancyFlag = '1'
                            else:
                                if discoveredValue is not None:  # Existing value is Blank / Null
                                    discrepancyFlag = '3'
                            logger.debug(
                                'c3psnmpGet :: discoveredValue >>>> %s <<existResInvValue>> %s <<<discrepancyFlag>> %s',
                                discoveredValue, existResInvValue, discrepancyFlag)

                            # #if (( discoveredValue is not None) and (x[3] is not None) and (x[3] == discoveredValue) ):
                            # if (( discoveredValue is not None and existResInvValue == discoveredValue ) and (existResInvValue is not None and existResInvValue != '-@-'  )):
                            #     discrepancyFlag = '0'
                            # elif (discoveredValue is None):
                            #     discrepancyFlag = '1'
                            # #elif ((discoveredValue is not None) and (x[3] is not None) and (x[3] is not discoveredValue)):
                            # elif ((discoveredValue is not None) and (existResInvValue is not None) and existResInvValue != '-@-' and (existResInvValue is not discoveredValue)):
                            #     discrepancyFlag = '2'
                            # #elif ((discoveredValue is not None) and (x[3] is None)):
                            # elif ((discoveredValue is not None) and existResInvValue is None and existResInvValue != '-@-' ):
                            #     # if (x[6] is not None):
                            #     #     existResInvValue = data_dInfo[x[6]].values
                            #     discrepancyFlag = '3'
                            # print('discoveredValue >>>>', discoveredValue, '<<existResInvValue>>',existResInvValue,'<<<discrepancyFlag>>', discrepancyFlag)
                        else:
                            discrepancyFlag = '9'  # Flag set to 9 as request is from C3P UI but does not required to compare
                            logger.debug("sourceSystem %s", sourceSystem)
                    else:
                        discrepancyFlag = '8'  # Flag set to 8 as request is from an external application
                        logger.debug("sourceSystem %s", sourceSystem)

                    if (existResInvValue == '-@-'):
                        # print('inside ::', existResInvValue)
                        existResInvValue = ''  # not add -@- values in tables
                        # print('Post ::', existResInvValue)

                    discoveryVal = (
                    mgmtip, device_id, x[0], discoveredValue, discovery_id, discrepancyFlag, existResInvValue,
                    datetime.today().strftime('%Y-%m-%d %H:%M:%S'), x[2])
                    logger.debug('c3psnmpGet :: discoveryVal :: %s ', discoveryVal)
                    # Update inv table with discovered value, discovery id, discrepancy flag
                    if (invExistCheck == 'Y' and sourceSystem == 'c3p-ui'):
                        update_inv_discovery_table(mgmtip, device_id, x[0], discoveredValue, discovery_id,
                                                   discrepancyFlag, x[5], x[2], existResInvValue)  # function call
                    elif (invExistCheck == 'N' and sourceSystem == 'c3p-ui'):
                        sqlIns = "INSERT INTO  c3p_t_host_inv_discrepancy ( hid_ip_address ,  device_id ,  hid_oid_no , hid_inv_existing_value, hid_discovered_value , hid_discrepancy_flag , hid_discovery_id ,  hid_resolved_flag , hid_resolved_by , hid_in_scope , hid_created_by ,  hid_created_date , hid_href , hid_resolved_timestamp, hid_display_name ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
                        insValue = (
                        mgmtip, str(device_id), x[0], existResInvValue, discoveredValue, discrepancyFlag, discovery_id,
                        'Y', 'system', 'Y', 'system', datetime.today().strftime('%Y-%m-%d %H:%M:%S'),
                        'api/resource/' + str(device_id), datetime.today().strftime('%Y-%m-%d %H:%M:%S'), x[2])
                        logger.debug('c3psnmpGet :: sqlIns :: %s \n insValue %s', sqlIns, insValue)
                        try:
                            mycursor.execute(sqlIns, insValue)
                            mydb.commit()
                            logger.debug('c3psnmpGet :: c3p_t_host_inv_discrepancy :: record inserted %s',
                                         mycursor.rowcount())
                        except Exception as e:
                            logger.error("c3psnmpGet :: c3p_t_host_inv_discrepancy :: Exception : %s", e)
                            # print("c3psnmpGet :: c3p_t_host_inv_discrepancy :: Exception : %s",e)
                            result = '1'

                            # invInscursor.execute(sqlIns, insValue)

                    else:
                        logger.debug(
                            'External System request, update or insert into HOST INV Discrpancy is not required')

                    discovery_result.append(discoveryVal)
        logger.debug("c3psnmpGet :: discovery_result 00-> %s", discovery_result)
        # Add discovery result in host_discovery_result table

        sql = "INSERT INTO c3p_t_host_discovery_result (hdr_ip_address, device_id, hdr_oid_no, hdr_discovered_value, hdr_discovery_id, hdr_discrepancy_flag, hdr_inv_existing_value, hdr_created_date, hdr_display_name) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"

        try:
            # hostcursor.executemany(sql, discovery_result)
            # print('HOST ****************::', discovery_result)
            logger.debug("c3psnmpGet :: discovery_result 11-> %s", discovery_result)
            mycursor.executemany(sql, discovery_result)
            mydb.commit()
            logger.debug("c3psnmpGet :: record inserted. %s", mycursor.rowcount)

            result = '0'
        except mysql.connector.errors.ProgrammingError as err:
            logger.error('c3psnmpGet :: Error in processing %s', err)
            result = '1'


    except Exception as err:
        logger.error("c3psnmpGet :: Main Exception : %s", err)
        # print("c3psnmpGet :: Exception : %s", err)
    finally:
        mydb.close
    return (result)

# ************************ snmpwalk for Interface ******************************
def c3psnmpWalk(intMgmtIP, intCommunity, intDiscoveryID, device_id, intVendor, intNetworkType,sourceSystem):  # tuple parameter
    invListPre = []
    invList = []
    nL = []
    myWalkResult = []
    list = []
    upList = []
    myresult = []
    invCardChOid = []
    invCardChOidVal = []
    invListCardSlot = []
    result = '0'
    created_date = datetime.today().strftime('%Y-%m-%d %H:%M:%S')

    mydb = Connections.create_connection()
    mycursor = mydb.cursor(buffered=True)
    sql = "SELECT cr_version, cr_login_read, cr_password_write, cr_enable_password, cr_encryption, cr_genric FROM c3p_m_credential_management where cr_profile_name=%s and cr_profile_type='SNMP'"
    values = (intCommunity,)

    mycursor.execute(sql, values)
    cred = mycursor.fetchone()
    logger.debug('Discovery:c3psnmpWalk:cred :: %s', cred)
    intCommunity=cred[0]
    snmpv3username = cred[1]
    snmpv3authKey = cred[2]
    snmpv3privKey = cred[3]
    authProtocol = cred[4]
    privProtocol = cred[5]
    snmpv3authProtocol=CSDRN.smnpv3AuthProtocol(authProtocol)
    snmpv3privProtocol=CSDRN.smnpv3PrivProtocol(privProtocol)
    # logger.debug('Discovery:c3psnmpWalk:credentials:: %s,%s,%s,%s,%s,%s', intCommunity,snmpv3username,snmpv3authKey,snmpv3privKey,snmpv3authProtocol,snmpv3privProtocol)

    try:
        mycursor = mydb.cursor(buffered=True)
        sql = "SELECT oid_m_no, oid_m_category, oid_m_display_name, oid_m_compare_req_flag, oid_m_fork_flag FROM c3p_m_oid_master_info where oid_m_category like 'Interface%' and oid_m_for_vendor=%s and oid_m_scope_flag='Y' and oid_m_network_type=%s and oid_m_fork_flag='Y'"
        values = (intVendor, intNetworkType)

        try:
            mycursor.execute(sql, values)
            myWalkResult = mycursor.fetchall()
        except mysql.connector.errors.ProgrammingError as e:
            logger.debug('c3psnmpWalk - myWalkResult Error - %s', e)
            result = '1'

        for n in myWalkResult:
            oidlist = ObjectType(ObjectIdentity(n[0]))
            logger.debug('c3psnmpWalk OID - %s', n[0])
            # oidlist=n[0]
            # print("Interface OID List :: ", oidlist)

            invOid = n[0]
            logger.debug('c3psnmpwalk :: intCommunity ::%s', intCommunity.lower())
            if intCommunity.lower() != 'snmpv3':
                security_model = CommunityData(snmpv3username, mpModel=0)  # For SNMP security model  V2

            elif intCommunity.lower() == 'snmpv3':
                security_model = UsmUserData(snmpv3username, snmpv3authKey, snmpv3privKey, snmpv3authProtocol,
                                             snmpv3privProtocol)  # For SNMP security model  V3

            for (errorIndication,
                 errorStatus,
                 errorIndex,
                 varBinds) in nextCmd(SnmpEngine(),
                                      security_model,
                                      UdpTransportTarget((intMgmtIP, 161)),
                                      ContextData(),
                                      oidlist,  # how to call nextCmd() with tuple parameter
                                      # ObjectType(ObjectIdentity(oidlist)),
                                      lexicographicMode=False, maxCalls=0):

                # logger.debug('c3psnmpwalk :: Inside snmpwalk for loop')
                if errorIndication:
                    logger.debug('c3psnmpWalk - 2 errorIndication- %s', errorIndication)
                    result = '1'
                    break
                elif errorStatus:
                    logger.debug('%s at %s' % (errorStatus, errorIndex and varBinds[int(errorIndex) - 1][0] or '?'))
                    break
                else:
                    # logger.debug('c3psnmpwalk :: Inside Else - 1')
                    for varBind in varBinds:  # varBind has type ObjectType
                        xf = str(varBind[1]).find("Null")
                        logger.debug('c3psnmpwalk :: XF :::%s', xf, "string value  >>>%s", str(varBind[1]), ' :::%s',
                                     str(varBind[0]))
                        if xf >= 0:
                            logger.debug('c3psnmpwalk :: Step - 1')
                            # print("Null value found in interface name - record ignored @index = ", xf)
                            nL.append(varBind[0].prettyPrint())

                        else:
                            logger.debug('c3psnmpwalk :: Step - 2')
                            invChOid = varBind[0].prettyPrint()
                            invChildoid = invChOid.replace('SNMPv2-SMI::mib-2.',
                                                           '1.3.6.1.2.1.')  # oid should have type ObjectIdentity
                            # Logic to correct the Admin or Operational Status as 1=Up or 2=Down
                            ''' Add new list of OID used for Card and Slot for Cisco Router ( example ASR9K ) '''
                            if (
                                    invOid == '1.3.6.1.2.1.47.1.1.1.1.4' or invOid == '1.3.6.1.2.1.47.1.1.1.1.5' or invOid == '1.3.6.1.2.1.47.1.1.1.1.6' or invOid == '1.3.6.1.2.1.47.1.1.1.1.7' or invOid == '1.3.6.1.2.1.47.1.1.1.1.13'):
                                logger.debug('c3psnmpwalk :: Step - 3')
                                invCardChOid.append(invChildoid)
                                invCardChOidVal.append(varBind[1].prettyPrint())
                            else:
                                logger.debug('c3psnmpwalk :: Step - 3')
                                if (
                                        invOid == '1.3.6.1.2.1.2.2.1.7' or invOid == '1.3.6.1.2.1.2.2.1.8' or invOid == '1.3.6.1.2.1.15.3.1.3'):
                                    if (varBind[1] == 1):
                                        logger.debug('c3psnmpwalk :: Step - 4')
                                        invChildoidVal = 'Up'
                                    elif (varBind[1] == 2):
                                        logger.debug('c3psnmpwalk :: Step - 5')
                                        invChildoidVal = 'Down'
                                elif (invOid == '1.3.6.1.2.1.14.10.1.6'):
                                    logger.debug('c3psnmpwalk :: Step - 6')
                                    if (varBind[1] == 1):
                                        logger.debug('c3psnmpwalk :: Step - 7')
                                        invChildoidVal = 'Down'
                                    elif (varBind[1] == 2):
                                        logger.debug('c3psnmpwalk :: Step - 8')
                                        invChildoidVal = 'Up'
                                # elif (invOid == '1.3.6.1.2.1.47.1.1.1.1.7' or invOid == '1.3.6.1.2.1.47.1.1.1.1.13'):
                                #     t = (invChildoid,varBind[1].prettyPrint())
                                #     invCardChOid.append(invChildoid)
                                #     invChildoidVal.append(varBind[1].prettyPrint())
                                # print('t :************* ::: ', t)
                                # updatedCardSlotOid = updateForkResultCardSlot(invChildoid,varBind[1].prettyPrint())
                                # print('t :************* ::: ', updatedCardSlotOid )
                                # invChildoid = updatedCardSlotOid
                                # invChildoidVal = varBind[1].prettyPrint()
                                # print('New :::: ********** :: ',invChildoid, ' >>',invChildoidVal )
                                else:
                                    logger.debug('c3psnmpwalk :: Step - 9')
                                    invChildoidVal = varBind[
                                        1].prettyPrint()  # val should have an appropriate value type
                                # print('Card Slot :: ', invCardChOid, ' :: ', invCardChOidVal)
                                # print('invOid :: ', invOid )
                                # print('Child Oid ::', invChildoid)
                                # print('Child Oid Value :: ', invChildoidVal, ' >> ', varBind[0].prettyPrint())

                                if (
                                        sourceSystem.lower() == 'c3p-ui'):  # setting discrpancy flag to 8 for external system request else 'N' for C3P UI request
                                    intDiscrepancyFlag = 'N'
                                    logger.debug('c3psnmpwalk :: Step - 10')
                                else:
                                    logger.debug('c3psnmpwalk :: Step - 11')
                                    intDiscrepancyFlag = '8'

                                intInvExitingVal = ''
                                inthref = 'api/interface/' + str(device_id)

                                discoveryVal = (
                                intMgmtIP, device_id, invOid, invChildoid, invChildoidVal, intDiscoveryID,
                                intDiscrepancyFlag, intInvExitingVal, 'system', created_date, inthref)

                                invListPre.append(discoveryVal)
                                logger.debug('c3psnmpwalk :: discoveryVale ::%s', discoveryVal)
        ###### Logic to eleminate the Null valued interfaces ###########

        for m in invListPre:
            # print('Main M[3] :: << ', m[3], ' >>')
            kf = 'N'
            logger.debug('c3psnmpwalk :: Step - 12')
            for k in nL:
                logger.debug('c3psnmpwalk :: Step - 13')
                # print('Inside M[3] :: <<<< ', m[3], ' >>>>')
                if (k.rsplit('.', 1)[1] == m[3].rsplit('.', 1)[1]):
                    # print ('IF Pass m[3] == ', m[3])
                    logger.debug('c3psnmpwalk :: Step - 14')
                    kf = 'Y'
                    # print ('Split value :: << ', k.rsplit('.',1)[1], ' >> << ', m[3].rsplit('.',1)[1] )
                else:
                    logger.debug('c3psnmpwalk :: Step - 15')
                    # print('Inside Else M[3] :: ?? <<<< ', m[3], ' >>>> kf ??', kf)
                    if kf != 'Y':
                        logger.debug('c3psnmpwalk :: Step - 16')
                        # print (' Else m[3] == ', m[3])
                        kf = 'N'
            if kf == 'N':
                logger.debug('c3psnmpwalk :: Step - 17')
                # print('Outside M[3] :: ??  ', m[3], ' ??')
                invList.append(m)
                # kf = ''

        logger.debug("c3psnmpwalk :: invList List >>> %s", invList)

        invListCardSlot = CSDRN.updateForkResultCardSlot(invCardChOid, invCardChOidVal)
        logger.debug('c3psnmpwalk :: invListCardSlot::%s', invListCardSlot)
        for m in invListCardSlot:
            invChildoid = m[0]
            invChildoidVal = m[1]
            discoveryVal = (
            intMgmtIP, device_id, invOid, invChildoid, invChildoidVal, intDiscoveryID, intDiscrepancyFlag,
            intInvExitingVal, 'system', created_date, inthref)
            logger.debug('c3psnmpwalk :: discoveryVal ::************ ::%s', discoveryVal)
            invList.append(discoveryVal)
            # updateCardSlotTable

        # print("invList ::", invList)

        # discoveryVal=(intMgmtIP, device_id, invOid, invChildoid, invChildoidVal, intDiscoveryID, intDiscrepancyFlag, intInvExitingVal, 'system', created_date,inthref)

        sql = "INSERT INTO c3p_t_fork_discovery_result (fdr_ip_address, device_id, fdr_oid_no, fdr_child_oid_no, fdr_discovered_value, fdr_discovery_id, fdr_discrepancy_flag, fdr_inv_existing_value, fdr_created_by, fdr_created_date, fdr_href) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"

        try:
            logger.debug('c3psnmpwalk :: Step - 18 ::%s %s', sql, invList)
            mycursor.executemany(sql, invList)
            logger.debug('c3psnmpwalk :: Step - 18 ::%s %s', sql, invList)
        except mysql.connector.errors.ProgrammingError as e:
            logger.debug('c3psnmpWalk - 3 MySQL Error - %s', e)
            result = '1'

        logger.debug("c3psnmpWalk :: interface discovery result records inserted. %s", mycursor.rowcount)

        mydb.commit()

        """
        Update the inventory fork table to create the  Interface IP address and Subnet Mask mapping with the Interface name
        """

        sql = "SELECT oid_m_no, fdr_child_oid_no, fdr_discovered_value FROM c3p_m_oid_master_info, c3p_t_fork_discovery_result WHERE oid_m_category = 'Interface' AND oid_m_for_vendor = %s AND oid_m_display_name = 'System' AND oid_m_network_type = %s AND oid_m_no = fdr_oid_no AND device_id = %s AND fdr_ip_address = %s AND fdr_discovery_id = %s"
        values = (intVendor, intNetworkType, str(device_id), intMgmtIP, str(intDiscoveryID))

        logger.debug("c3psnmpWalk :: IPSubnet Correction SQL :: %s", sql)

        try:
            mycursor.execute(sql, values)
            myresult = mycursor.fetchall()

        except mysql.connector.errors.ProgrammingError as err:
            logger.debug('c3psnmpWalk :: 4 - MySQL Error - %s', err)
            # logger.error('Error - %s',err)
            result = '1'
        sOid = ''
        for m in myresult:
            logger.debug('c3psnmpwalk :: Step - 19')
            sOid = m[0].rsplit('.', 1)[0] + '.%'
            list.append([m[0],
                         m[1].rsplit('.', 4)[1] + '.' + m[1].rsplit('.', 4)[2] + '.' + m[1].rsplit('.', 4)[3] + '.' +
                         m[1].rsplit('.', 4)[4], m[2]])
            # print('extraction :: ', m[1].rsplit('.',4)[1])

        logger.debug('c3psnmpwalk :: List :: %s', list)
        logger.debug('c3psnmpwalk :: sOid :: %s', sOid)

        sql = "SELECT id, fdr_oid_no, fdr_child_oid_no, fdr_discovered_value FROM c3p_t_fork_discovery_result WHERE fdr_oid_no LIKE %s AND device_id = %s AND fdr_ip_address = %s AND fdr_discovery_id = %s"
        values = (sOid, str(device_id), intMgmtIP, str(intDiscoveryID))

        try:
            mycursor.execute(sql, values)
            myresult = mycursor.fetchall()

        except mysql.connector.errors.ProgrammingError as err:
            logger.error('c3psnmpWalk :: Error - %s', err)
            logger.debug('c3psnmpWalk :: 5 MySQL Error - %s', err)
            result = '1'
            # return('1')

        for n in myresult:
            logger.debug('c3psnmpwalk :: n :: >> %s', n[1])
            for k in list:
                ncoid = n[2].rsplit('.', 4)[1] + '.' + n[2].rsplit('.', 4)[2] + '.' + n[2].rsplit('.', 4)[3] + '.' + \
                        n[2].rsplit('.', 4)[4]
                logger.debug('c3psnmpwalk :: OIDs %s >> %s', k[0], n[1])
                if (k[0] == n[1]):
                    logger.debug('c3psnmpWalk :: matched ::')
                    tcoid = n[2]
                else:
                    logger.debug('c3psnmpwalk :: Not Matched :: >> %s  >> %s', ncoid, k[1])
                    if (ncoid == k[1]):
                        # print()
                        tcoid = n[2].rsplit('.', 4)[0] + '.' + k[2]
                        logger.debug('c3psnmpwalk :: ncoid :: %s  >> tcoid :: << %s  >> %s', ncoid, n[2], tcoid)
                    else:
                        logger.debug('Failed 1 :: << %s  >> %s', n[2], ncoid)

            sql = "UPDATE c3p_t_fork_discovery_result SET fdr_child_oid_no = %s WHERE id = %s"
            values = (tcoid, str(n[0]))

            try:
                mycursor.execute(sql, values)
                logger.debug("c3psnmpWalk :: record updated. %s", mycursor.rowcount)

            except mysql.connector.errors.ProgrammingError as err:
                logger.error('c3psnmpwalk :: Error - err %s', err)
                logger.debug('c3psnmpWalk :: 6 MySQL Error - %s', err)
                result = '1'

            upList.append([n[0], n[1], tcoid, n[3]])
        # mycursor.close()                          # for reading oid from master table
        mydb.commit()
        logger.debug('c3psnmpWalk Completed %s ', result)
    except Exception as err:
        logger.error("c3psnmpWalk :: Exception %s", err)
    finally:
        logger.debug(' c3psnmpWalk :: DB Close ')
        mydb.close
    return (result)

    # datetime.today().strftime('%Y-%m-%d %H:%M:%S')

# ************************ create_new_resource ******************************
def create_new_resource(newMgmtIP, newHostName, newVendor):
    # newResCursor = mydb.cursor(buffered=True)
    newInv_result = []
    mydb = Connections.create_connection()
    newDevice_id = ''
    try:
        mycursor = mydb.cursor(buffered=True)
        sql = """
            INSERT INTO c3p_deviceinfo(
                d_auto_status, 
                d_autorun_date, 
                d_connect, 
                d_hostname, 
                d_mgmtip, 
                d_vnf_support, 
                d_vendor, 
                d_new_device, 
                c_site_id, 
                d_decomm
            ) VALUES ('Y', %s, 'SSH', %s, %s, 'PNF', %s, 0, 1, '0')
        """

        values = (
            datetime.today().strftime('%Y-%m-%d %H:%M:%S'),
            newHostName,
            newMgmtIP,
            newVendor
        )

        try:
            mycursor.execute(sql, values)

        except Exception as e:
            return ('1')

        logger.debug('create_new_resource :: last inserted row id : %s', mycursor.lastrowid)

        mydb.commit()

        CSDRN.setDeviceRole(newHostName, newMgmtIP)

        newDevice_id = mycursor.lastrowid

        sql = """
                SELECT 
                    oid_m_no, 
                    oid_m_display_name 
                FROM 
                    c3p_m_oid_master_info 
                WHERE 
                    oid_m_scope_flag = 'Y' 
                    AND oid_m_for_vendor = %s 
                    AND oid_m_network_type = 'PNF' 
                    AND oid_m_fork_flag = 'N' 
                    AND oid_m_category <> 'Interface'
            """
        values = (newVendor,)
        try:
            mycursor.execute(sql, values)
            newResCursor = mycursor.fetchall()
        except Exception as e:
            return ('1')

        for newRes in newResCursor:
            newResInvDescripacyVal = (
            newMgmtIP, newDevice_id, newRes[0], 'Y', 'system', datetime.today().strftime('%Y-%m-%d %H:%M:%S'),
            '/api/discovery/1234', newRes[1])
            newInv_result.append(newResInvDescripacyVal)

        # print('New Inv Result ....', newInv_result)

        sql = "INSERT INTO c3p_t_host_inv_discrepancy (hid_ip_address, device_id, hid_oid_no, hid_in_scope, hid_created_by, hid_created_date, hid_href, hid_display_name) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)"

        try:
            mycursor.executemany(sql, newInv_result)
        except mysql.connector.errors.ProgrammingError as e:
            return ('1')
        mydb.commit()
    except Exception as err:
        logger.error("create_new_resource :: Exception : %s", err)
    finally:
        mydb.close
    return (newDevice_id)

# ************************ search_Value ******************************
def search_Value(searchMgmtIP, searchCommunity, displayName, searchOid):
    searchValue = '0'
    # print('Inside : get_device_info_using_ip', searchMgmtIP, searchCommunity,displayName, searchOid)
    # oid_systeminfo = '1.3.6.1.2.1.1.5.0'
    # oid_systeminfo = '1.3.6.1.2.1.47.1.1.1.1.2.1'            # OID to get Device's vendor and network type information
    mydb = Connections.create_connection()
    mycursor = mydb.cursor(buffered=True)
    sql = """
        SELECT 
            cr_version, 
            cr_login_read, 
            cr_password_write, 
            cr_enable_password, 
            cr_encryption, 
            cr_genric 
        FROM 
            c3p_m_credential_management 
        WHERE 
            cr_profile_name = %s 
            AND cr_profile_type = 'SNMP'
    """

    values = (searchCommunity,)

    mycursor.execute(sql, values)
    cred = mycursor.fetchone()
    logger.debug('Discovery:search_Value:cred :: %s', cred)
    searchCommunity=cred[0]
    snmpv3username = cred[1]
    snmpv3authKey = cred[2]
    snmpv3privKey = cred[3]
    authProtocol = cred[4]
    privProtocol = cred[5]
    snmpv3authProtocol=CSDRN.smnpv3AuthProtocol(authProtocol)
    snmpv3privProtocol=CSDRN.smnpv3PrivProtocol(privProtocol)

    # logger.debug('Discovery:search_Value:credentials:: %s,%s,%s,%s,%s,%s', searchCommunity,snmpv3username,snmpv3authKey,snmpv3privKey,snmpv3authProtocol,snmpv3privProtocol)

    if searchCommunity.lower() != 'snmpv3':
        security_model = cmdgen.CommunityData('server', snmpv3username,
                                              1)  # 1 means version SNMP v2c  #For SNMP security model  V2
        logger.debug("security_model snmpv2: %s", snmpv3username)
    elif searchCommunity.lower() == 'snmpv3':
        security_model = cmdgen.UsmUserData(snmpv3username, snmpv3authKey, snmpv3privKey, snmpv3authProtocol,
                                            snmpv3privProtocol)  # For SNMP security model  V3
        logger.debug("security_model is snmpv3: %s", searchCommunity.lower())

    generator = cmdgen.CommandGenerator()
    security_model
    transport = cmdgen.UdpTransportTarget((searchMgmtIP, 161))

    real_fun = getattr(generator, 'getCmd')
    res = (errorIndication, errorStatus, errorIndex, varBinds) \
        = real_fun(security_model, transport, searchOid)

    if not errorIndication is None or errorStatus is True:
        # print ("Error: %s %s %s %s" )
        print('%s at %s' % (errorStatus, errorIndex and varBinds[int(errorIndex) - 1][0] or '?'))
        searchValue = 'C3P-DR-504'
    else:
        for varBind in varBinds:  # varBind has type ObjectType
            searchValue = CSDRN.extract_discoveryValue(displayName, varBind[1], '#')
            # print('Return value = ', varBind[1])
            # print('Vendor Value : ', searchValue)
            if (searchValue is None):
                # print('Error : Vendor not found for ip address : ', searchMgmtIP)
                searchValue('C3P-DR-501')
    return (searchValue)

# ************************ update_inv_discovery_table ******************************
def update_inv_discovery_table(invMgmtip, invDevice_id, invOid, invDiscoveredValue, invDiscoveryId, invDiscrepancyFlag,
                               invComparisonFlag, invDisplayName, invExistInvValue):
    resolved_by = ''
    resolved_flag = ''

    if ((invComparisonFlag == 'Y') and (invDiscrepancyFlag == '0')):
        resolved_flag = 'Y'
    elif ((invComparisonFlag == 'Y') and (invDiscrepancyFlag == '1')):
        resolved_flag = 'N'
    elif ((invComparisonFlag == 'Y') and (invDiscrepancyFlag == '2')):
        resolved_flag = 'N'
    elif ((invComparisonFlag == 'Y') and (invDiscrepancyFlag == '3')):
        resolved_flag = 'N'
    elif (invComparisonFlag == 'N'):
        resolved_flag = 'N'

    if ((invComparisonFlag == 'Y') and (invDiscrepancyFlag == '0')):
        resolved_by = 'system'
    elif ((invComparisonFlag == 'N')):
        resolved_by = 'system'

    logger.debug('update_inv_discovery_table :: invComparisonFlag    = %s', invComparisonFlag)
    logger.debug('update_inv_discovery_table :: invDiscrepancyFlag   = %s', invDiscrepancyFlag)
    logger.debug('update_inv_discovery_table :: resolved_flag        = %s', resolved_flag)
    logger.debug('update_inv_discovery_table :: resolved_by          = %s', resolved_by)

    mydb = Connections.create_connection()
    try:
        mycursor = mydb.cursor(buffered=True)
        # sql="UPDATE c3p_t_host_inv_discrepancy SET hid_inv_prev_value= '"+str(existInvExistingValue)+"', hid_inv_existing_value= '"+str(existDiscoveredValue)+"', hid_discrepancy_flag = '"+invDiscrepancyFlag+"', hid_discovered_value = '" + invDiscoveredValue + "', hid_discovery_id  = '" + str(invDiscoveryId) + "', hid_resolved_flag = '"+resolved_flag+"', hid_resolved_by = '"+resolved_by+"', hid_in_scope = 'Y', hid_updated_date = '" + datetime.today().strftime('%Y-%m-%d %H:%M:%S') + "' WHERE hid_ip_address = '" + invMgmtip + "' and hid_oid_no = '" + invOid + "' and device_id = '" + str(invDevice_id) + "' and hid_display_name ='" +invDisplayName+'"
        sql = """
            UPDATE c3p_t_host_inv_discrepancy 
            SET 
                hid_discrepancy_flag = %s,
                hid_discovered_value = %s,
                hid_discovery_id = %s,
                hid_resolved_flag = %s,
                hid_resolved_by = %s,
                hid_in_scope = 'Y',
                hid_updated_date = %s
            WHERE 
                hid_ip_address = %s 
                AND hid_oid_no = %s 
                AND device_id = %s 
                AND hid_display_name = %s
        """

        values = (
            invDiscrepancyFlag,
            invDiscoveredValue,
            str(invDiscoveryId),
            resolved_flag,
            resolved_by,
            datetime.today().strftime('%Y-%m-%d %H:%M:%S'),
            invMgmtip,
            invOid,
            str(invDevice_id),
            invDisplayName
        )

        mycursor.execute(sql, values)
        logger.debug("update_inv_discovery_table :: record updated. %s", mycursor.rowcount)
        if mycursor.rowcount == 0:
            sqlIns = "INSERT INTO  c3p_t_host_inv_discrepancy ( hid_ip_address ,  device_id ,  hid_oid_no , hid_inv_existing_value, hid_discovered_value , hid_discrepancy_flag , hid_discovery_id ,  hid_resolved_flag , hid_resolved_by , hid_in_scope , hid_created_by ,  hid_created_date , hid_href , hid_resolved_timestamp, hid_display_name ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
            insValue = (invMgmtip, str(invDevice_id), invOid, invExistInvValue, invDiscoveredValue, invDiscrepancyFlag,
                        str(invDiscoveryId), resolved_flag, resolved_by, 'Y', 'system',
                        datetime.today().strftime('%Y-%m-%d %H:%M:%S'), 'api/resource/' + str(invDevice_id),
                        datetime.today().strftime('%Y-%m-%d %H:%M:%S'), invDisplayName)
            mycursor.execute(sqlIns, insValue)
            logger.debug("update_inv_discovery_table :: New OID record Inserted. %s", mycursor.rowcount)
        mydb.commit()

    except Exception as err:
        logger.error("update_inv_discovery_table :: Exception : %s", err)
        return ('1')
    finally:
        mydb.close
    # invcursor.close()
    return ('0')

    # mgmtip          =   sys.argv[1]   =   '10.62.0.27'
    # community       =   sys.argv[2]   =   'public'
    # discovery_id    =   sys.argv[3]   =   '123'
    # device_id       =   sys.argv[4]   =   '10'
    # vendor          =   sys.argv[5]   =   'Cisco'
    # networktype    =    sys.argv[6]   =   'PNF'
# ************************ update_inv_discovery_table ******************************

def c3pInterfaceReconcilationStep1(irMgmtIP, irCommunity, irDiscoveryID, device_id, irVendor, irNetworkType,
                                   irNewDevice):
    invIntRec = []

    resolved_by = ''
    irDiscrepancyFlag = ''
    resolved_flag = ''
    myIntResult = []
    myIntRec = []

    mydb = Connections.create_connection()
    try:
        mycursor = mydb.cursor(buffered=True)
        sqlRes = """
            SELECT fdr_oid_no, fdr_child_oid_no, fdr_discovery_id, fdr_discovered_value, fdr_href, c3p_m_oid_master_info.oid_m_compare_req_flag 
            FROM c3p_t_fork_discovery_result, c3p_m_oid_master_info 
            WHERE fdr_ip_address = %s 
                AND device_id = %s 
                AND fdr_discovery_id = %s 
                AND fdr_oid_no = oid_m_no 
                AND oid_m_for_vendor = %s
        """

        values = (
            irMgmtIP,
            str(device_id),
            str(irDiscoveryID),
            irVendor
        )

        try:
            mycursor.execute(sqlRes, values)
            myIntResult = mycursor.fetchall()  # Change
            logger.debug('c3psnmpwalk :: Step - 20:: myIntResult::%s', myIntResult)
        except mysql.connector.errors.ProgrammingError as e:
            logger.error('c3pInterfaceReconcilationStep1 :: Exception #1 : %s', e)
            return ('1')

        for t in myIntResult:
            irDiscoveredValue = t[3]
            irComparisonFlag = t[5]
            sql = """
                SELECT fid_inv_existing_value 
                FROM c3p_t_fork_inv_discrepancy 
                WHERE fid_ip_address = %s 
                    AND device_id = %s 
                    AND fid_oid_no = %s 
                    AND fid_child_oid_no = %s
            """

            values = (
                irMgmtIP,
                str(device_id),
                t[0],
                t[1]
            )

            try:
                mycursor.execute(sql, values)
                myIntRec = mycursor.fetchall()  # change
                logger.debug('c3psnmpwalk :: Step - 21 :: myIntRec::%s', myIntRec)
            except mysql.connector.errors.ProgrammingError as e:
                logger.error('c3pInterfaceReconcilationStep1 :: Exception #2 : %s', e)
                return ('1')
            # print('Rowcount ################# = ', mycursor.rowcount)
            logger.debug('c3pInterfaceReconcilationStep1 :: Rowcount : %s', mycursor.rowcount)

            if (mycursor.rowcount == 1):

                for m in myIntRec:

                    irExistingInvVal = m[0]
                    # irExistingDiscoveredVal = m[1]
                    logger.debug('c3pInterfaceReconcilationStep1 :: OID                 : %s', t[0])
                    logger.debug('c3pInterfaceReconcilationStep1 :: Child OID           : %s', t[1])
                    logger.debug('c3pInterfaceReconcilationStep1 :: irExistingInvVal    : %s', irExistingInvVal)
                    logger.debug('c3pInterfaceReconcilationStep1 :: irComparisonFlag    : %s', irComparisonFlag)
                    logger.debug('c3pInterfaceReconcilationStep1 :: irDiscoveredValue   : %s', irDiscoveredValue)

                    if (irComparisonFlag == 'Y'):
                        if ((irDiscoveredValue is not None) and (irExistingInvVal is not None) and (
                                irExistingInvVal == irDiscoveredValue)):
                            irDiscrepancyFlag = '0'
                        elif (irDiscoveredValue is None):
                            irDiscrepancyFlag = '1'
                        elif ((irDiscoveredValue is not None) and (irExistingInvVal is not None) and (
                                irExistingInvVal is not irDiscoveredValue)):
                            irDiscrepancyFlag = '2'
                        elif ((irDiscoveredValue is not None) and (irExistingInvVal is None)):
                            irDiscrepancyFlag = '3'
                    else:
                        irDiscrepancyFlag = '9'

                    if ((irComparisonFlag == 'Y') and (irDiscrepancyFlag == '0')):
                        resolved_flag = 'Y'
                    elif ((irComparisonFlag == 'Y') and (irDiscrepancyFlag == '1')):
                        resolved_flag = 'N'
                    elif ((irComparisonFlag == 'Y') and (irDiscrepancyFlag == '2')):
                        resolved_flag = 'N'
                    elif ((irComparisonFlag == 'Y') and (irDiscrepancyFlag == '3')):
                        resolved_flag = 'N'
                    elif (irComparisonFlag == 'N'):
                        resolved_flag = 'Y'

                    if ((irComparisonFlag == 'Y') and (irDiscrepancyFlag == '0')):
                        resolved_by = 'system'
                    elif ((irComparisonFlag == 'N')):
                        resolved_by = 'system'

                        # sqlUpd="UPDATE c3p_t_fork_inv_discrepancy SET  fid_inv_prev_value = '"+str(irExistingInvVal)+"', fid_inv_existing_value = '"+str(irExistingDiscoveredVal)+"', fid_discovered_value = '"+irDiscoveredValue+"', fid_discrepancy_flag = '"+irDiscrepancyFlag+"', fid_updated_by = 'system', fid_updated_date = '"+datetime.today().strftime('%Y-%m-%d %H:%M:%S')+"', fid_discovery_id = '"+str(t[2])+"', fid_resolved_flag = '"+resolved_flag+"', fid_resolved_by = '"+resolved_by+"', fid_in_scope = 'Y'  where fid_ip_address = '"+irMgmtIP+"' and device_id = '"+str(device_id) +"' and fid_oid_no = '"+t[0]+"' and fid_child_oid_no = '"+t[1]+"'"
                    sqlUpd = """
                        UPDATE c3p_t_fork_inv_discrepancy 
                        SET fid_discovered_value = %s, 
                            fid_discrepancy_flag = %s, 
                            fid_updated_by = 'system', 
                            fid_updated_date = %s, 
                            fid_discovery_id = %s, 
                            fid_resolved_flag = %s, 
                            fid_resolved_by = %s, 
                            fid_in_scope = 'Y'  
                        WHERE fid_ip_address = %s 
                            AND device_id = %s 
                            AND fid_oid_no = %s 
                            AND fid_child_oid_no = %s
                    """

                    values = (
                        irDiscoveredValue,
                        irDiscrepancyFlag,
                        datetime.today().strftime('%Y-%m-%d %H:%M:%S'),
                        str(t[2]),
                        resolved_flag,
                        resolved_by,
                        irMgmtIP,
                        str(device_id),
                        t[0],
                        t[1]
                    )

                    try:
                        mycursor.execute(sqlUpd, values)
                        logger.debug('c3pInterfaceReconcilationStep1 :: Updated rowcount #1: %s', mycursor.rowcount)
                    except mysql.connector.errors.ProgrammingError as e:
                        logger.error('c3pInterfaceReconcilationStep1 :: Exception #3 : %s', e)
                        return ('1')

                    mydb.commit()

                    sqlUpdResult = """
                        UPDATE c3p_t_fork_discovery_result 
                        SET fdr_inv_existing_value = %s, 
                            fdr_discrepancy_flag = %s, 
                            fdr_updated_by = 'system', 
                            fdr_updated_date = %s 
                        WHERE fdr_ip_address = %s 
                            AND device_id = %s 
                            AND fdr_oid_no = %s 
                            AND fdr_child_oid_no = %s 
                            AND fdr_discovery_id = %s
                    """

                    values = (
                        str(irExistingInvVal),
                        irDiscrepancyFlag,
                        datetime.today().strftime('%Y-%m-%d %H:%M:%S'),
                        irMgmtIP,
                        str(device_id),
                        t[0],
                        t[1],
                        str(t[2])
                    )

                    try:
                        mycursor.execute(sqlUpdResult, values)
                        logger.debug('c3pInterfaceReconcilationStep1 :: Updated rowcount #2: %s', mycursor.rowcount)
                    except mysql.connector.errors.ProgrammingError as e:
                        logger.error('c3pInterfaceReconcilationStep1 :: Exception #4 : %s', e)
                        return ('1')

                    mydb.commit()

            else:

                irDiscrepancyFlag = ''
                irExistingInvVal = ''
                irhref = '/api/interface/' + str(device_id)

                if ((irComparisonFlag == 'Y') and (irDiscoveredValue is not None)):
                    irExistingInvVal = irDiscoveredValue
                    irDiscrepancyFlag = '0'
                    resolved_flag = 'Y'
                    resolved_by = 'system'
                elif (irComparisonFlag == 'N'):
                    irExistingInvVal = irDiscoveredValue
                    irDiscrepancyFlag = '0'
                    resolved_flag = 'Y'
                    resolved_by = 'system'

                invIntVal = (irMgmtIP, device_id, t[0], t[1], t[3], irDiscrepancyFlag, irDiscoveryID, 'Y', 'system',
                             datetime.today().strftime('%Y-%m-%d %H:%M:%S'), irhref, irExistingInvVal)

                sqlIns = "INSERT INTO c3p_t_fork_inv_discrepancy (fid_ip_address, device_id, fid_oid_no, fid_child_oid_no, fid_discovered_value, fid_discrepancy_flag, fid_discovery_id, fid_in_scope, fid_created_by, fid_created_date, fid_href, fid_inv_existing_value) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"

                try:

                    mycursor.execute(sqlIns, invIntVal)
                    logger.debug('c3pInterfaceReconcilationStep1 :: Updated rowcount #3: %s', mycursor.rowcount)
                    # print(myInvInsert.rowcount, 'interface inventory record inserted')
                except mysql.connector.errors.ProgrammingError as e:
                    logger.debug('c3pInterfaceReconcilationStep1 :: Exception #5 : %s', e)
                    return ('1')

                mydb.commit()
            # Updating fork table
        sqlUpd = """
            UPDATE c3p_t_fork_inv_discrepancy 
            SET fid_discovered_value = '', 
                fid_discrepancy_flag = '1', 
                fid_updated_by = 'system', 
                fid_updated_date = %s, 
                fid_discovery_id = %s, 
                fid_resolved_flag = 'N'  
            WHERE fid_ip_address = %s 
                AND device_id = %s 
                AND fid_in_scope = 'Y' 
                AND fid_discovery_id <> %s
        """

        values = (
            datetime.today().strftime('%Y-%m-%d %H:%M:%S'),
            str(t[2]),
            irMgmtIP,
            str(device_id),
            str(t[2])
        )

        try:
            mycursor.execute(sqlUpd, values)
            logger.debug('c3pInterfaceReconcilationStep1  Fork :: %s records updated ', mycursor.rowcount)
        except mysql.connector.errors.ProgrammingError as e:
            logger.debug('c3pInterfaceReconcilationStep1  :: Fork Exception #6 : %s', e)
            return ('1')
        mydb.commit()

        # Updating host table - Handles the scenario of OID de-scoping
        sqlUpd = """
            UPDATE c3p_t_host_inv_discrepancy 
            SET hid_discovered_value = '', 
                hid_discrepancy_flag = '1', 
                hid_updated_by = 'system', 
                hid_updated_date = %s, 
                hid_discovery_id = %s, 
                hid_resolved_flag = 'N'  
            WHERE hid_ip_address = %s 
                AND device_id = %s 
                AND hid_in_scope = 'Y' 
                AND hid_discovery_id <> %s
        """

        values = (
            datetime.today().strftime('%Y-%m-%d %H:%M:%S'),
            str(t[2]),
            irMgmtIP,
            str(device_id),
            str(t[2])
        )

        try:
            mycursor.execute(sqlUpd, values)
            logger.debug('c3pInterfaceReconcilationStep1  Host :: %s records updated ', mycursor.rowcount)
        except mysql.connector.errors.ProgrammingError as e:
            logger.debug('c3pInterfaceReconcilationStep1 :: Host Exception #7 : %s', e)
            return ('1')
        mydb.commit()

        logger.debug('Is a New Device ? :: %s', irNewDevice)
        if (irNewDevice == 'New'):  # in case of new device, update the device info table else ignore the update
            updateRI = update_ResourceInfo(irMgmtIP, device_id, irVendor, irNetworkType)
            if (updateRI == '0'):
                logger.debug('c3pInterfaceReconcilationStep1 :: UpdateRI : Successful ')
                # return('0')
            else:
                logger.debug('c3pInterfaceReconcilationStep1 :: UpdateRI : Error ')
                # return('1')
        else:

            """ Code added to update the Discrepancy Count in DeviceInfo Table """
            logger.debug('c3pInterfaceReconcilationStep1 :: old device :')

        sql = """
            UPDATE c3p_deviceinfo 
            SET d_discrepancy = (
                SELECT (
                    (SELECT COUNT(fid_row_id) FROM c3p_t_fork_inv_discrepancy WHERE fid_discrepancy_flag IN ('1','2','3') AND fid_in_scope= 'Y' AND fid_resolved_flag = 'N' AND device_id = %s) + 
                    (SELECT COUNT(hid_row_id) FROM c3p_t_host_inv_discrepancy WHERE hid_discrepancy_flag IN ('1','2','3') AND hid_in_scope= 'Y' AND hid_resolved_flag = 'N' AND device_id = %s)
                ) FROM dual
            ) 
            WHERE d_id = %s
        """

        values = (str(device_id), str(device_id), str(device_id))

        try:
            mycursor.execute(sql, values)
            logger.debug('c3pInterfaceReconcilationStep1 :: discripancyCount Updated %s', mycursor.rowcount)
        except mysql.connector.errors.ProgrammingError as e:
            logger.debug('c3pInterfaceReconcilationStep1 :: Exception #8 : %s', e)
            return ('1')

        mydb.commit()

        data = {}
        data['device_id'] = device_id
        data['discovery_id'] = irDiscoveryID
        physicalinventorypopulator.setCardSlotInformation(data)
    except Exception as err:
        logger.error("c3pInterfaceReconcilationStep1 :: Exception #9 : %s", err)
    finally:
        mydb.close
    return ('0')

def check_invExist(chMgmtIP, chDevice_id):
    invExist = 'N'
    mydb = Connections.create_connection()
    try:
        mycursor = mydb.cursor(buffered=True)
        sql = "SELECT * FROM c3p_t_host_inv_discrepancy WHERE hid_ip_address = %s AND device_id = %s"
        values = (chMgmtIP, str(chDevice_id))

        mycursor.execute(sql, values)

        if (mycursor.rowcount >= 1):
            invExist = 'Y'
        else:
            invExist = 'N'
    except Exception as err:
        logger.error("check_invExist :: Exception #1: %s", err)
    finally:
        mydb.close
    # myInvCheck.close()
    return (invExist)

# ************************ check_VendorValidity  ******************************
def check_VendorValidity(vendorVal):
    result = 'N'
    mydb = Connections.create_connection()
    try:
        mycursor = mydb.cursor(buffered=True)
        sql = "SELECT * FROM c3p_t_glblist_m_vendor WHERE UPPER(vendor) = UPPER(%s)"
        values = (vendorVal,)

        mycursor.execute(sql, values)

        if mycursor.rowcount == 1:
            result = 'Y'
    except Exception as err:
        logger.error("check_VendorValidity :: Exception #1 : %s", err)
    finally:
        mydb.close()
    return result


def update_ResourceInfo(riMgmtIP, riDeviceID, riVendor, riNetworkType):
    mydb = Connections.create_connection()
    try:
        logger.debug("update_ResourceInfo riMgmtIP:: %s", riMgmtIP)
        logger.debug("update_ResourceInfo riDeviceID:: %s", riDeviceID)
        logger.debug("update_ResourceInfo riVendor:: %s", riVendor)
        logger.debug("update_ResourceInfo riNetworkType:: %s", riNetworkType)
        mycursor = mydb.cursor(buffered=True)
        logger.debug("after mycursor ")

        sqlUpd = """SELECT oid_m_no, oid_m_map_attrib, c3p_t_host_inv_discrepancy.hid_discovered_value, device_id
                    FROM c3p_m_oid_master_info, c3p_t_host_inv_discrepancy
                    WHERE oid_m_category = 'Host' AND oid_m_for_vendor = %s
                          AND oid_m_map_attrib <> '' AND oid_m_no = hid_oid_no AND oid_m_display_name = hid_display_name
                          AND hid_ip_address = %s AND device_id = %s AND oid_m_network_type = %s"""

        values = (riVendor, riMgmtIP, riDeviceID, riNetworkType)

        logger.debug("sqlUpd = %s", sqlUpd)
        try:
            mycursor.execute(sqlUpd, values)
        except mysql.connector.errors.ProgrammingError as e:
            return '1'

        if mycursor.rowcount > 0:
            data_device_info = pd.DataFrame(mycursor.fetchall())
            logger.debug('update_ResourceInfo :: data device info :  %s', data_device_info)
            data_device_info.columns = mycursor.column_names
            logger.debug('update_ResourceInfo :: data_device_info.columns :  %s', data_device_info.columns)
        else:
            logger.debug("update_ResourceInfo :: No value to return")
            return '1'

        # update the data into device info table
        for find, replace, cond in zip(data_device_info["oid_m_map_attrib"], data_device_info["hid_discovered_value"],
                                       data_device_info["device_id"]):
            logger.debug("update_ResourceInfo :: data_device_info  %s %s %s", find, replace, cond)
            try:
                sql = "UPDATE c3p_deviceinfo SET {} = %s WHERE d_id = %s".format(find)
                values = (replace, cond)
                logger.debug("update_ResourceInfo :: sql  %s", sql)
                mycursor.execute(sql, values)
            except mysql.connector.errors.ProgrammingError as err:
                logger.error('update_ResourceInfo :: Error #1: %s', err)
                return '1'

            mydb.commit()
    except Exception as err:
        logger.error("update_ResourceInfo :: Exception #2 : %s", err)
    finally:
        mydb.close()
    return '0'
