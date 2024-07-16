from jumpssh import SSHSession
import logging
import time
from c3papplication.common import Connections
from netmiko import (ConnectHandler,NetmikoTimeoutException,NetmikoAuthenticationException,)
logger = logging.getLogger(__name__)

def jumpCred(deviceId):
    try:
        mydb = Connections.create_connection()
        mycursor = mydb.cursor(buffered=True)
        sql = "select cr_info_id from c3p_device_credentials where device_id = %s"
        mycursor.execute(sql, (deviceId,))
        crInfoId = mycursor.fetchall()
        for crId in crInfoId:
            sql = "select cr_url,cr_password_write,cr_login_read,cr_port from c3p_m_credential_management where cr_info_id = %s and cr_profile_type = 'JUMPHOST'"
            mycursor.execute(sql, (crId[0],))
            JSSH = mycursor.fetchall()
            if not JSSH ==[]:
                jIp = JSSH[0][0]
                jPort = JSSH[0][3]
                jUsername = JSSH[0][2]
                jPassword = JSSH[0][1]
        cred = {"jumpIp":jIp,"jumpPort":jPort,"jumpUsername":jUsername,"jumpPassword":jPassword}
    except Exception as err:
       logger.error("ipmanagement::c3p_jumpssh::jumpCred: %s",err)
    return cred

def connectJumpHost(command,deviceId):  
  cred=jumpCred(deviceId)
  # command='ping -c 4 '+ ip
  try:
    jumphost = {
                'device_type': 'autodetect',
                'host': cred["jumpIp"],
                'username': cred["jumpUsername"],
                'password': cred["jumpPassword"],
                'port': cred["jumpPort"]
                }
    with ConnectHandler(**jumphost) as net_connect:
        res = net_connect.send_command(command)
        # logger.debug("JSSH res:",res)
  except (NetmikoTimeoutException, NetmikoAuthenticationException) as err:
    logger.error("ipmanagement::c3p_jumpssh:: connectJumphost: %s",err)
    res=[] 
  return res

def jumpPingTestParser(data):
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
        else:
            res= ["Request timed out"]
            min='0'
            avg='0'
            max='0'
        pRes = { "ipAddress":rIP,"pingReply":res, "min":min,"avg": avg, "max" : max} 
    except Exception as err:
      logger.error("ipmanagement::c3p_jumpssh::jumpPingParser :",err)
    return  pRes

def jumpLatencyParser(data):
    res=[]
    try:    
        rIP=data.partition('--- ')[2].partition(' ping statistics')[0]
        avg=data.partition('= ')[2].partition('/')[2].partition('/')[0]
        percentage=data.partition('received, ')[2].partition('% packet loss,')[0]
        response=data.partition('bytes of data.\n')[2].partition('\n---')[0]
        if percentage.strip() == '0':
            response=(response.splitlines())
            res= response
        else:
            res= ["Request timed out"]
            avg='0'
        pRes = { "ipAddress":rIP,"pingReply":res, "avg": avg+'ms'} 
    except Exception as err:
      logger.error("ipmanagement::c3p_jumpssh::jumpLatencyParser :",err)
    return  pRes

def jumpFramelossParser(data):
    res=[]
    try:    
        rIP=data.partition('--- ')[2].partition(' ping statistics')[0]
        percentage=data.partition('received, ')[2].partition('% packet loss,')[0]
        response=data.partition('bytes of data.\n')[2].partition('\n---')[0]
        if percentage.strip() == '0':
            response=(response.splitlines())
            res= response
        else:
            res= ["Request timed out"]
        pRes = {"ipAddress":rIP, "pingReply" : res, "frameloss": str(percentage) + "%"} 
    except Exception as err:
      logger.error("ipmanagement::c3p_jumpssh::jumpFramelossParser :",err)
    return  pRes

def jumpTracerouteParser(data,rIp): 
    res=[]
    try:   
        dat=data.partition('byte packets\n')[2]
        x=dat.splitlines()
        for x in x:
            dis=x.partition('  ')[0]
            ip=x.partition('  ')[2].partition('  ')[0]
            max=x.partition('  ')[2].partition('  ')[2].partition('  ')[0]
            avg=x.partition('  ')[2].partition('  ')[2].partition('  ')[2].partition('  ')[0]
            min=x.partition('  ')[2].partition('  ')[2].partition('  ')[2].partition('  ')[2].partition('  ')[0]
            res.append({"Distance(ttl)":dis,"IPaddress":ip,"Min":min,"Avg": avg,"Max":max})
            resTR = {"reqIP":rIp,"TraceRoute":res}
    except Exception as err:
      logger.error("ipmanagement::c3p_jumpssh::jumpTracerouteParser :",err)
      resTR=[]
    return resTR

def jumpDeviceCred(deviceId):
    cred ={}
    mydb = Connections.create_connection()
    try:
        mycursor = mydb.cursor(buffered=True)
        sql = "select d_mgmtip from c3p_deviceinfo where d_id=%s"
        mycursor.execute(sql, (deviceId,))
        ip = mycursor.fetchall()
        rIp=ip[0][0]
        sql = "select cr_info_id from c3p_device_credentials where device_id=%s"
        logger.debug("common::c3p_jumpssh::jumpDeviceCred ::SQL:: %s", sql)
        mycursor.execute(sql, (deviceId,))
        crInfoId = mycursor.fetchall()
        for crId in crInfoId:
            sql = "select cr_url,cr_password_write,cr_login_read,cr_port from c3p_m_credential_management where cr_info_id = %s and cr_profile_type = 'JUMPHOST'"
            mycursor.execute(sql, (crId[0],))
            JSSH = mycursor.fetchall()
            if JSSH:
                jIp = JSSH[0][0]
                jPort = JSSH[0][3]
                jUsername = JSSH[0][2]
                jPassword = JSSH[0][1]
            sql = "select cr_password_write,cr_login_read from c3p_m_credential_management where cr_info_id = %s and cr_profile_type = 'SSH'"
            mycursor.execute(sql, (crId[0],))
            SSH = mycursor.fetchall()
            if SSH:
                rUsername = SSH[0][1]
                rPassword = SSH[0][0] 
        cred = {"jumpIp":jIp,"jumpPort":jPort,"jumpUsername":jUsername,"jumpPassword":jPassword,"remoteIp":rIp,"remoteUsername":rUsername,"remotePassword":rPassword}
    except Exception as err:
        logger.debug(f"common::c3p_jumpssh::jumpDeviceCred : {err}")
    finally:
        mydb.close
    return cred

def connectjumpssh(command,deviceId):  
    output=""
    print('common::c3p_jumpssh::connectjumpssh:deviceId :: %s',deviceId)
    cred=jumpDeviceCred(deviceId)
    try: 
        # establish ssh connection between your local machine and the jump server 
      with SSHSession(cred["jumpIp"],cred["jumpUsername"],port=cred["jumpPort"], password=cred["jumpPassword"]) as gatewaysess:
          gatewaysess.open()
        #   print(gatewaysess.is_active())
          print('common::c3p_jumpssh::connectjumpssh::: connection is True :: %s', gatewaysess.is_active())
          # establish ssh connection between jump server and the remote Device 
          with gatewaysess.get_remote_session(cred["remoteIp"],username=cred["remoteUsername"],password=cred["remotePassword"], look_for_keys=False) as remotesess:
              output= remotesess.get_cmd_output(command)
    except Exception as err:
       print("common::c3p_jumpssh::connectjumpssh :",err)
    return output

def jumpThroughputParser(data): 
  try:
    MTU=data.partition('MTU ')[2].partition('bytes')[0]
    RX=data.partition('output rate')[2].partition('packets/sec')[2].partition(' packets input')[0]
    TX=data.partition('pause input')[2].partition(' packets output')[0]
  except Exception as err:
    print("common::c3p_jumpssh::jumpThroughputParser :",err)
  return MTU,RX.strip(),TX.strip()

def throughputCalculation(deviceid): 
  try:
    port="gigabitEthernet 1"
    command="sh int " + port
    x=connectjumpssh(command,deviceid)
    MTU,RX1,TX1=jumpThroughputParser(x)
    print(MTU,RX1,TX1)
    time.sleep(55)
    x2=connectjumpssh(command,deviceid)
    MTU,RX2,TX2=jumpThroughputParser(x2)
    print(MTU,RX2,TX2)
    # Number of packet received/transmitted  in 1 min = Packet count after 1 min - Packet count during 1st time command execution 
    RX=int(RX2)-int(RX1)
    TX=int(TX2)-int(TX1)
    print(MTU,RX,TX)
    # Number of pakets per second = No packets received in 1 Min/60
    RXPackets=RX/60
    TXPackets=TX/60
    print(RXPackets)
    #Throughput (Bits/sec) = Number of packets per second*(MTU Size+20)*8
    RXTHRbs=RXPackets*(int(MTU)+20)*8
    TXTHRbs=TXPackets*(int(MTU)+20)*8
    print(RXTHRbs)
    # Throughput in KB/Sec = Throughput (Bits/sec) *0.000125
    RXTHRKBs=RXTHRbs * 0.000125
    TXTHRKBs=TXTHRbs * 0.000125
    print(RXTHRKBs)
    # Thoughput in MB/sec =  Throughput (Kbyte/sec)/1024
    RXTHRMBs=RXTHRKBs/1024
    TXTHRMBs=TXTHRKBs/1024
    RXTH=str(round(RXTHRMBs,6))
    TXTH=str(round(TXTHRMBs,6))
    print(RXTH,TXTH)
    response = {"throughput":"RX- "+RXTH +" TX- "+TXTH,'unit':"MBps"}
  except Exception as err:
      print("common::c3p_jumpssh::throughputCalculation :",err)
      response = {"error":"error during throughput calculation"}
  return response