from markupsafe import escape
from c3papplication.common import Connections
from c3papplication.conf.springConfig import springConfig
import logging
from jproperties import Properties
import paramiko
from netmiko import ConnectHandler
import re

logger = logging.getLogger(__name__)

configs = springConfig().fetch_config()

filepath= (configs.get("backupfilepath")).strip()

def getRequestInfo(RequestId,version):
    reqVersion = float(version)
    mydb = Connections.create_connection()
    mycursor = mydb.cursor(buffered=True)
    data = []
    try:
        mycursor.execute("SELECT r_management_ip,r_hostname,r_template_id_used FROM c3p_t_request_info where r_alphanumeric_req_id = %s and r_request_version =%s ",(RequestId,reqVersion,))
        data = mycursor.fetchone()
    except Exception as err:
        logger.error("templatemanagement:networkAudit:getRequestInfo:: %s", err)
    finally:
        mydb.close()
    return data

def getDeviceInfo(managementip,hostname):
    mydb = Connections.create_connection()
    mycursor = mydb.cursor(buffered=True)
    data = []
    try:
        mycursor.execute("SELECT d_id,d_connect,d_os,d_vendor FROM c3p_deviceinfo where d_mgmtip = %s and d_hostname =%s ",(managementip,hostname,))
        data = mycursor.fetchone()
    except Exception as err:
        logger.error("templatemanagement:networkAudit:getDeviceInfo:: %s", err)
    finally:
        mydb.close()
    return data

def getCrInfoId(deviceid):
    mydb = Connections.create_connection()
    mycursor = mydb.cursor(buffered=True)
    data = []
    try:
        mycursor.execute("SELECT cr_info_id FROM c3p_device_credentials where device_id = %s ",(deviceid,))
        data = mycursor.fetchone()
    except Exception as err:
        logger.error("templatemanagement:networkAudit:getCrInfoId:: %s", err)
    finally:
        mydb.close()
    return data

def getDeviceCredentials(infoid):
    mydb = Connections.create_connection()
    mycursor = mydb.cursor(buffered=True)
    data = []
    try:
        mycursor.execute("SELECT cr_login_read,cr_password_write FROM c3p_m_credential_management where cr_info_id = %s ",(infoid,))
        data = mycursor.fetchone()
    except Exception as err:
        logger.error("templatemanagement:networkAudit:getDeviceCredentials:: %s", err)
    finally:
        mydb.close()
    return data   

def getVendorSpecificCommand(os,vendor,networktype):
    mydb = Connections.create_connection()
    mycursor = mydb.cursor(buffered=True)
    data = []
    try:
        mycursor.execute("SELECT vc_start FROM c3p_m_vendor_specific_command where vc_os = %s and vc_vendor_name =%s and vc_network_type = %s and vc_repetition =%s",(os,vendor,networktype,"FBCK"))
        data = mycursor.fetchone()
    except Exception as err:
        logger.error("templatemanagement:networkAudit:getVendorSpecificCommand:: %s", err)
    finally:
        mydb.close()
    return data

def backupCmdout(ip,username,password, command,output_file):
    try:
        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.RejectPolicy())
        client.connect(ip,username=username,password=password)
        (stdin, stdout, stderr) = client.exec_command(command)
        cmd_output = stdout.read().decode()
        logger.debug("templatemanagement:networkAudit:backupCmdout:: cmd_output %s",  cmd_output)
        with open(output_file, "w+") as file:
            file.write(str(cmd_output))
    except Exception as err:
        logger.error("templatemanagement:networkAudit:backupCmdout:: %s", err)
    finally:
        client.close()
    return output_file

def networkBackup(content):
    RequestId = content.get("requestId")
    version = content.get("version")
    filenames=[]
    try:
        requestinfo=getRequestInfo(RequestId,version)
        managementip1=requestinfo[0]
        hostname1=requestinfo[1]
        device2=requestinfo[2]
        devinfo=device2.split('::')
        managementip2=devinfo[1]
        hostname2=devinfo[0]
        data=[[managementip1,hostname1],[managementip2,hostname2]]
        logger.debug("templatemanagement:networkAudit:networkBackup:data :: %s",data)
        for ip,host in data:
            outputfile= escape(RequestId) + "_" + escape(host) +"_" + "PeerAudit.txt"
            file=filepath+outputfile
            logger.debug("templatemanagement:networkAudit:networkBackup:ip,host :: %s,%s",ip,host)
            deviceinfo=getDeviceInfo(ip,host)
            logger.debug("templatemanagement:networkAudit:networkBackup:deviceinfo :: %s",deviceinfo)
            crinfoid=getCrInfoId(deviceinfo[0])
            logger.debug("templatemanagement:networkAudit:networkBackup:crinfoid :: %s",crinfoid)
            cred=getDeviceCredentials(crinfoid[0])
            logger.debug("templatemanagement:networkAudit:networkBackup:cred :: %s",cred)
            userN=cred[0]
            passW=cred[1]
            devicinfo=getDeviceInfo(ip,host)
            logger.debug("templatemanagement:networkAudit:networkBackup:getDeviceInfo :: %s",devicinfo)
            dconnect=devicinfo[1]
            dos=devicinfo[2]
            dvendor=devicinfo[3]
            if dconnect == "SSH":
                networkType="PNF"
            commands=getVendorSpecificCommand(dos,dvendor,networkType)
            logger.debug("templatemanagement:networkAudit:networkBackup:commands :: %s",commands)
            command = commands[0].split("::")
            logger.debug("templatemanagement:networkAudit:networkBackup:commandsplit :: %s",command)
            logger.debug("templatemanagement:networkAudit:networkBackup :: %s,%s,%s,%s,%s",ip,userN,passW,command[0],file)
            if dvendor.lower()=="vyos":
                showcmd(ip,userN,passW,command[0],file)
            else:    
                backupCmdout(ip,userN,passW,command[0],file)
            filenames.append(outputfile)
        logger.debug("templatemanagement:networkAudit:networkBackup:filenames :: %s",filenames)
    except Exception as err:
        logger.error("templatemanagement:networkAudit:networkBackup:: %s", err)
        filenames={"error":"Error while fetching filenames"}
    return str(filenames)
    
def showcmd(ip,username,password,command,output_file):
    try:
        console_server = {
            'host': ip,
            'username':username,
            'password': password,
            'device_type': 'autodetect',
            'port': 22,
            'fast_cli': False
        }
        with ConnectHandler(**console_server) as net_connect:
            cmd_output=net_connect.send_command(command)
            # remove the ANSI escape sequences from a string using regular expression
            reaesc = re.compile(r'(?:\x1B[@-Z\\-_]|[\x80-\x9A\x9C-\x9F]|(?:\x1B\[|\x9B)[0-?]*[ -/]*[@-~])')
            cmd_output1 = reaesc.sub('', str(cmd_output))
            with open(output_file, "w+") as file:
                file.write(str(cmd_output1))  
            logger.debug("templatemanagement:networkAudit:showcmd:cmd_output:: %s", cmd_output1)
    except Exception as err:
        logger.error("templatemanagement:networkAudit:showcmd:: %s", err)
    return output_file