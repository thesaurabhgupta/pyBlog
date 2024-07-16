import random,string
import json,logging
from datetime import datetime
import json
from c3papplication.common import Connections
from c3papplication.conf.springConfig import springConfig
import mysql.connector
from jproperties import Properties
import ipaddress
from c3papplication.common import c3p_lib
from pythonping import ping
import requests
from flask import request, jsonify
from flask_api import status
import concurrent.futures
from threading import Thread
from netmiko import (ConnectHandler,NetmikoTimeoutException,NetmikoAuthenticationException,)
import time 

logger = logging.getLogger(__name__)

configs = springConfig().fetch_config()

def createPingRecord(pingInfo):
    dT  =''
    ipT =''    
    pingRowID=''
    pingID=''
    pingStart=''
    mydb = Connections.create_connection()
    try:
        mycursor = mydb.cursor(buffered=True)
        logger.debug("ipmanagement::c3p_ip_ping::createPingRecord-pingInfo:: %s", pingInfo)
        pingType= pingInfo['pingType']
        ipType  = pingInfo['ipType']
        pingName= pingInfo['pingName']
        sIP     = pingInfo['startIp']
        eIP     = pingInfo['endIp']
        netMask = pingInfo['netMask']
        pingCby  = pingInfo['createdBy']
        pingSrc  = pingInfo['sourcesystem']
        jumphost  = pingInfo['jumphost']
        pingStart= datetime.today().strftime('%Y-%m-%d %H:%M:%S')
        # logic to generate the ping id
        if ( pingType == 'ipSingle'):
            dT = 'S'
        elif(pingType == 'ipRange'):
            dT = 'R'
        elif(pingType == 'import'):
            dT = 'I'
        elif(pingType == 'ipList'):
            dT = 'L'
            # sIP = ','.join([str(elem) for i,elem in enumerate(sIP)])
        if (ipType == 'ipv4') :
            ipT = '4'
        elif(ipType == 'ipv6'):
            ipT ='6'
        # prepare the ping id
        pingStC =pingStart.replace("-","")
        pingStC =pingStC.replace(":","")
        pingStC =pingStC.replace(" ","")
       
        pingID = 'S'+'P'+dT+ipT+pingStC+''.join(random.choices(string.ascii_uppercase, k=2))
        logger.debug('ipmanagement::c3p_ip_ping::createPingRecord :: ping ID : %s ', pingID)

        sql = "INSERT INTO c3p_t_qt_dashboard (qt_id,qt_name,qt_status,qt_ip_type,qt_ops_type,qt_type,qt_start_ip,qt_end_ip,qt_mask,qt_schedule_id,qt_created_date,qt_created_by,qt_source_system,qt_jumphost) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
        insValue = (pingID , pingName ,'In Progress', ipType ,'ping',pingType , sIP , eIP , netMask ,'', pingStart, pingCby,pingSrc,jumphost)
        logger.debug('ipmanagement::c3p_ip_ping::createPingRecord :: sql %s', sql)
        logger.debug('ipmanagement::c3p_ip_ping::createPingRecord :: insValue %s', insValue)
        
        """ 
        Create Order Id as the ping request received from an external system e.g. ServiceNow (SNOW)
        If request is genereated internally it will not generate the Order Id
        """
        if not pingSrc == 'c3p-ui':
            """ Create a Order record in c3p_rf_order rfo_id = disID"""
            #logger.debug('createDiscoveryRecord - disInfo :: %s', json.dumps(disInfo))
            sqlOrder = "INSERT INTO c3p_rf_orders (rfo_id,rfo_apibody,rfo_apioperation,rfo_apiurl,rfo_sourcesystem,rfo_apiauth_status,rfo_status,rfo_created_date) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)"
            insValueOrder = ( pingID , json.dumps(pingInfo) ,'POST', '/C3P/api/pingflow/' , pingSrc , 'Pass' , 'In Progress' , pingStart)
            
            mycursor.execute(sqlOrder,insValueOrder)
            logger.debug("create pingRecord - Order record inserted. %s",mycursor.rowcount)
            
            pingRowID=mycursor.lastrowid
            logger.debug('create pingRecord - Order id :: %s', pingRowID)
            
            mydb.commit()
        try:
            mycursor.execute(sql,insValue)
            logger.debug("ipmanagement::c3p_ip_ping::createPingRecord - ping record inserted row: %s",mycursor.rowcount)
            pingRowID=mycursor.lastrowid
            mydb.commit()
        except mysql.connector.errors.ProgrammingError as err:
            logger.error('ipmanagement::c3p_ip_ping::createPingRecord - Error in ping inserting record :: %s',err)
            pingRowID=''
            pingID='Error C3P-PR-502'
    except Exception as err:
        logger.error("ipmanagement::c3p_ip_ping::createPingRecord: %s",err)
    finally:
        mydb.close
    return(pingRowID, pingID, pingStart)

def generateQueueId():
    QueueID=''
    pingStart=''
    try:
        pingStart= datetime.today().strftime('%Y-%m-%d %H:%M:%S')
        pingStC =pingStart.replace("-","").replace(":","").replace(" ","")   
        QueueID = 'QDID'+pingStC+''.join(random.choices(string.ascii_uppercase, k=2))
    except Exception as err:
        logger.error("ipmanagement::c3p_ip_ping:: generateQueueId: %s",err)    
    return( QueueID, pingStart)

def getAllIPsForPing(sIP, netMask, eIP):
    rsIP = sIP
    seIP =[]
    masks = {'255':1, '254':2, '252':4, '248':8, '240':16, '224':32, '192':64, '128':128, '0':255}
    ipAddrRange=[]
    # prepare the subnets request
    try:
        while (ipaddress.ip_address(sIP) <= ipaddress.ip_address(eIP)):
            subnets=[str(sIP)+"/"+str(netMask)]
            ipList= c3p_lib.calculate_subnets(subnets)
            for m in range(len(ipList['ipaddrs'])):
                sIP = ipaddress.ip_address(ipList['ipaddrs'][0])
                ipAddrRange.append(ipList['ipaddrs'][m])

            sIP = ipaddress.ip_address(sIP)+masks[netMask.split(".")[3]]

        for m in range(len(ipAddrRange)):
            cIP = ipAddrRange[m]
            #print('cIP : ', cIP)
            if((ipaddress.ip_address(cIP) >= ipaddress.ip_address(rsIP)) and (ipaddress.ip_address(cIP) <= ipaddress.ip_address(eIP))):
                #print('selected ip : ', cIP)
                seIP.append(cIP)
            else:
                print('getAllIPsForDiscovery - reject ip : %s', cIP)
        #print('seIP Type:', type(seIP))
    except Exception as err:
        logger.error("ipmanagement::c3p_ip_ping:: getAllIPsForPing: %s",err)
    return seIP


def createPingDetalis(pingInfo, pingID):
    pingType= pingInfo['pingType']
    ipType  = pingInfo['ipType']
    pingName= pingInfo['pingName']
    sIP     = pingInfo['startIp']
    eIP     = pingInfo['endIp']
    netMask = pingInfo['netMask']
    pingCby  = pingInfo['createdBy']
    pingSrc  = pingInfo['sourcesystem']
    ips=[]
    mydb = Connections.create_connection()
    try:
        mycursor = mydb.cursor(buffered=True)
        if (pingType == 'ipSingle'):
            ips = sIP.split(",")
            for ip in ips:
                QueueID, pingStart = generateQueueId()
                sql = "INSERT INTO c3p_t_qt_details(qd_id,qd_qt_id,qd_ip,qd_status,qd_stat,qd_created_by,qd_created_date) VALUES (%s,%s,%s,%s,%s,%s,%s)"
                insValue = (QueueID,pingID ,ip,'InProgress', '',pingCby, pingStart)
                mycursor.execute(sql,insValue)
                mydb.commit()    
        elif(pingType == 'ipList'):
            ips = sIP.split(",")
            for ip in ips:
                QueueID, pingStart = generateQueueId()
                sql = "INSERT INTO c3p_t_qt_details(qd_id,qd_qt_id,qd_ip,qd_status,qd_stat,qd_created_by,qd_created_date) VALUES (%s,%s,%s,%s,%s,%s,%s)"
                insValue = (QueueID,pingID ,ip,'InProgress', '',pingCby, pingStart)
                mycursor.execute(sql,insValue)
                mydb.commit() 
        elif (pingType == 'ipRange'):
            sIP=getAllIPsForPing(sIP, netMask, eIP)
            for ip in sIP:
                QueueID, pingStart = generateQueueId()
                sql = "INSERT INTO c3p_t_qt_details(qd_id,qd_qt_id,qd_ip,qd_status,qd_stat,qd_created_by,qd_created_date) VALUES (%s,%s,%s,%s,%s,%s,%s)"
                insValue = (QueueID,pingID ,ip,'InProgress', '',pingCby, pingStart)
                mycursor.execute(sql,insValue)
                mydb.commit()            
    except Exception as err:
        logger.error("ipmanagement::c3p_ip_ping::createPingDetalis: %s",err)
    finally:
        mydb.close
        
def jumpPingParser(data):
    res=[]
    try:    
        rIP=data.partition('--- ')[2].partition(' ping statistics')[0]
        min=data.partition('= ')[2].partition('/')[0]
        avg=data.partition('= ')[2].partition('/')[2].partition('/')[0]
        max=data.partition('= ')[2].partition('/')[2].partition('/')[2].partition('/')[0]
        mdev=data.partition('= ')[2].partition('/')[2].partition('/')[2].partition('/')[2].partition(' ')[0]
        sent=data.partition('ping statistics ---\n')[2].partition(' packets transmitted')[0]
        received=data.partition('packets transmitted, ')[2].partition(' received,')[0]
        percentage=data.partition('received, ')[2].partition('% packet loss,')[0]
        loss=int(sent)-int(received)
        packets={"Sent":str(sent),"Received" :str(received) ,"Lost" :str(loss)+" ("+str(percentage)+"%)Loss"} 
        response=data.partition('bytes of data.\n')[2].partition('\n---')[0]
        if percentage.strip() == '0':
            response=(response.splitlines())
            res= response
            status="Pass"
        else:
            res= "Request timed out"
            status="Fail"
            min='0'
            avg='0'
            max='0'
            mdev='0'
        stats=min +"/"+ avg +"/"+ max +"/"+ mdev +"/"+ sent +"/"+ received +"/"+ str(loss)+"("+ percentage +"%)"+"Loss"
        pRes = {"pingReply":res,"Packets": packets,"Minimum":min,"Average": avg, "Maximum" : max}
        res=[pRes,status,rIP,stats]
    except Exception as err:
      logger.error("ipmanagement::c3p_ip_ping::jumpPingParser :",err)
    return res

def pingfromjumphost(ip,hostname):
    try:
        mydb = Connections.create_connection()
        mycursor = mydb.cursor(buffered=True)
        sql = "select cr_login_read,cr_password_write,cr_port,cr_url from c3p_m_credential_management where cr_profile_name = %s"
        logger.debug("c3p_m_credential_management - sql here :: %s", sql)
        mycursor.execute(sql, (hostname,))
        jumpinfo = mycursor.fetchall()
        # print(jumpinfo[0][0])
        logger.debug('ipmanagement::c3p_ip_ping::pingfromjumphost -jumpinfo :: %s',jumpinfo[0][0])
        try:
            jumphost  =  {
                        'device_type': 'autodetect',
                        'host': jumpinfo[0][3],
                        'username': jumpinfo[0][0],
                        'password': jumpinfo[0][1],
                        'port': jumpinfo[0][2]
                        }
            command='ping -c 4 '+ ip
            with ConnectHandler(**jumphost) as net_connect:
                res = net_connect.send_command(command)
                logger.debug('ipmanagement::c3p_ip_ping::pingfromjumphost -res :: %s',res)
                res=jumpPingParser(res)
                logger.debug('ipmanagement::c3p_ip_ping::pingfromjumphost -res parser :: %s',res)
        except (NetmikoTimeoutException, NetmikoAuthenticationException) as err:
            logger.error("ipmanagement::c3p_ip_ping::pingfromjumphost: %s",err)
            res=[]
    except Exception as e:
        logger.error("ipmanagement::c3p_ip_ping::pingfromjumphost: %s",e)
    finally:
        mydb.close
    return res  

def pingIp(rIP):
    res = []
    status=""
    sent=0
    received=0
    try:
        pResponse = ping(rIP)  
        for m in pResponse:
            res.append(str(m).replace(',',' ',2))
            sent+=1
            if str(m) != 'Request timed out':
                received+=1
                
        if res[3] =="Request timed out":
            status='Fail'
        else:
            status='Pass'
        loss=sent-received
        percentage=((sent-received)/sent)*100   
        stats=str(pResponse.rtt_min_ms) +"/"+ str(pResponse.rtt_avg_ms )+"/"+ str(pResponse.rtt_max_ms)+"/0.00"+"/"+str(sent)+"/"+str(received)+"/"+str(loss)+" ("+str(percentage)+"%)Loss"
        packets={"Sent":str(sent),"Received" :str(received) ,"Lost" :str(loss)+" ("+str(percentage)+"%)Loss"} 
        pRes = {"pingReply":res,"Packets": packets,"Minimum":pResponse.rtt_min_ms,"Average": pResponse.rtt_avg_ms, "Maximum" : pResponse.rtt_max_ms}
        res=[pRes,status,rIP,stats]
    except Exception as err:
        logger.error("ipmanagement::c3p_ip_ping:: pingIp: %s",err)
    return res


def decomposeStart(pingID):
    try: 
        """ perform the ping for each IP and Save the resultant """
        url=configs.get("Camunda_Engine")+"/decompWorkflow/start"
        inp = {}
        inp['businessKey']=pingID           
        inp['variables']= {"version":{"value":"1.0"}}
        data_json = json.dumps(inp)
        logger.debug("ipmanagement::c3p_ip_ping::decomposeStart JSON :: %s", data_json)
        newHeaders={"Content-type":"application/json","Accept":"application/json"}
        f =requests.post(url,data=data_json, headers=newHeaders)
        logger.debug('ipmanagement::c3p_ip_ping::decomposeStart - Response :: %s', f.json())
    except Exception as err:
        logger.error("ipmanagement::c3p_ip_ping::decomposeStart: %s",err)


def pingTestflow(pingInfo):
    res=[]
    try:
        pingRowID, pingID, pingStart=createPingRecord(pingInfo)
        createPingDetalis(pingInfo, pingID)
        logger.debug("ipmanagement::c3p_ip_ping::pingTestflow - pingID = %s",pingID)
        thread = Thread(target = decomposeStart, args = (pingID,)).start()
        rhref =configs.get("Python_Application")+'/c3p-p-core/api/ResourceFunction/v4/monitor/?id='+pingID
        res = jsonify({"content":request.json,"href":rhref}),status.HTTP_202_ACCEPTED
        logger.debug("ipmanagement::c3p_ip_ping::pingTestflow- response JSON :: %s", res)
    except Exception as err:
        logger.error("ipmanagement::c3p_ip_ping::   pingTestflow: %s",err)
    return res

def performPingIps(pingid):
    ips=[]
    pingReturn=[]
    mydb = Connections.create_connection()
    logger.info('ipmanagement::c3p_ip_ping:: performPingIps function start ')
    try:
        mycursor = mydb.cursor(buffered=True)
        mycursor.execute("SELECT qt_type,qt_start_ip,qt_end_ip,qt_mask,qt_jumphost FROM c3p_t_qt_dashboard  where qt_id = %s", (pingid,))
        myresult    =   mycursor.fetchall()
        # Iptype =   myresult[0]
        logger.debug('"ipmanagement::c3p_ip_ping::performPingIps  - myresult :: %s', myresult)  
        if myresult[0][0]=='ipSingle':
            ip= myresult[0][1]
            ips.append(ip)
        elif myresult[0][0]=='ipList':
            ips= myresult[0][1]
            ips = ips.split(",")
        elif myresult[0][0]=='ipRange':
            sIP=myresult[0][1]
            eIP=myresult[0][2]
            netMask=myresult[0][3]
            ips=getAllIPsForPing(sIP, netMask, eIP)
        logger.debug('"ipmanagement::c3p_ip_ping::performPingIps  - ips :: %s', ips)
        if myresult[0][4] != "NA":
            hostname=myresult[0][4]
            with concurrent.futures.ProcessPoolExecutor() as executor:
                reOut = {executor.submit(pingfromjumphost, ip, hostname): ip for ip in ips}
                for future in concurrent.futures.as_completed(reOut):
                    reOut = [future.result()]
                    logger.debug('ipmanagement::c3p_ip_ping::performPingIps  - reOut :: %s', reOut)
                    updatePingDetailStatus(reOut,pingid)
        else:   
            with concurrent.futures.ProcessPoolExecutor() as executor:
                reOut = executor.map(pingIp,ips)
                logger.debug('ipmanagement::c3p_ip_ping::performPingIps  - reOut :: %s', reOut)
                updatePingDetailStatus(reOut,pingid)  
    except Exception as err:
        logger.error("ipmanagement::c3p_ip_ping::performPingIps: %s",err)
    return False    

def updatePingDetailStatus(pingReturn,pingid):
    logger.info('ipmanagement::c3p_ip_ping:: updatePingDetailStatus function start ')
    mydb = Connections.create_connection()
    try:
        mycursor = mydb.cursor(buffered=True)
        pingStat     = 'Completed'
        pingUpdate   = datetime.today().strftime('%Y-%m-%d %H:%M:%S')
        for PRe in pingReturn:
            logger.debug('"ipmanagement::c3p_ip_ping::performPingIps  - status,stat,ip :: %s',  PRe)
            status=PRe[1]
            statJson=PRe[0]
            statJson=json.dumps(statJson, indent = 4) 
            stat=PRe[3]
            ip=PRe[2]
            logger.debug('"ipmanagement::c3p_ip_ping::performPingIps  - status,stat,ip :: %s,%s,%s', status,stat,ip)
            insSql = "UPDATE c3p_t_qt_details SET qd_status= %s, qd_stat= %s, qd_stat_json= %s WHERE qd_ip = %s AND qd_qt_id = %s"
            mycursor.execute(insSql, (status,stat,statJson,ip,pingid,))
            mydb.commit()
            logger.debug("ipmanagement::c3p_ip_ping:: updatePingDetailStatus :: record inserted %s", mycursor.rowcount)

        updSql = "UPDATE c3p_t_qt_dashboard SET qt_status = %s WHERE qt_id = %s"
        mycursor.execute(updSql, (pingStat,pingid,))
        mydb.commit()
    except Exception as err:
        logger.error("ipmanagement::c3p_ip_ping:: updatePingDetailStatus: %s",err)
    finally:
        mydb.close
        
        
def PingDetailReport(qtId):
    logger.info('ipmanagement::c3p_ip_ping:: PingDetailReport function start ')
    output_resp=[]
    try:
        mydb = Connections.create_connection()
        mycursor = mydb.cursor(buffered=True)
        mycursor.execute("SELECT qt_status FROM c3p_t_qt_dashboard  where qt_id = %s", (qtId,))
        qtStatus    =   mycursor.fetchone()
        while qtStatus[0] == "InProgress":
            mycursor.execute("SELECT qt_status FROM c3p_t_qt_dashboard  where qt_id = %s", (qtId,))
            qtStatus    =   mycursor.fetchone()
            logger.debug("ipmanagement::c3p_ip_ping:: PingDetailReport status: %s", qtStatus[0])
            time.sleep(5)
            
        mycursor.execute("SELECT qd_id,qd_qt_id,qd_ip,qd_status,qd_created_date,qd_stat_json FROM c3p_t_qt_details  where qd_qt_id = %s", (qtId,))
        qtdata    =   mycursor.fetchall()  
        for qt_details in qtdata:
            resp = {
                    'pingID': qt_details[0],
                    'SPID': qt_details[1],
                    'Ip': qt_details[2],
                    'status': qt_details[3],
                    'createdDate':(json.dumps(str(qt_details[4])).replace('"','')),
                    'stat_Response':(json.loads(qt_details[5]))
                    }
            output_resp.append(resp)
        output_resp=json.dumps(output_resp) 
            
    except Exception as err:
        logger.error("ipmanagement::c3p_ip_ping:: PingDetailReport: %s",err)
    finally:
        mydb.close   
    return output_resp 