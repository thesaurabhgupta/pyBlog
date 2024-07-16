import json,logging
from datetime import datetime
from flask import jsonify,escape
#import Connections
from c3papplication.common import Connections
from c3papplication.conf.springConfig import springConfig
import requests 
from requests.auth import HTTPBasicAuth
from jproperties import Properties
import mysql.connector

from netmiko import ConnectHandler
import sys
import time
import select
import paramiko
import re
import os, string
from pymongo import MongoClient
from pprint import pprint
from gridfs import GridFS
from c3papplication.yang import yangExtractor

import xlrd
import xlwt
import pandas.io.sql as sql
from configparser import ConfigParser
#from markupsafe import escape
from c3papplication.discovery.TopologyEntityET import TopologyEntityET


logger = logging.getLogger(__name__)

configs = springConfig().fetch_config()

def triggerPhysicalTopology(content):
    s_mgmtip    = content['mgmtip']
    s_hostname  = content['hostname']
    s_device_id = content['device_id']
    sSystem     = content['sourcesystem']
    filename= ''
    mydb = Connections.create_connection()
    try:
        mycursor = mydb.cursor(buffered=True)
        commands = configs.get("PHY_SHOW_CMMDS")
        
        #Logic to generate file name
        dt = datetime.today().strftime('%Y%m%d%H%M%S')
        # fileToSave = open(configs.get("XLS_PHY_TOPO_FILE_BASE_PATH")+"\\"+s_hostname+"_"+dt+".txt",'w') 
        # filename = escape(configs.get("XLS_PHY_TOPO_FILE_BASE_PATH")) + f"{s_hostname}_{dt}.txt"
        old_stdout = sys.stdout   
        # sys.stdout = fileToSave 
        name = os.path.normpath(os.path.join(configs.get("XLS_PHY_TOPO_FILE_BASE_PATH"), f"{s_hostname}_{dt}.txt"))
        base_path = '/tmp/'

        if not name.startswith(base_path):
            logger.error(f"Invalid file path: {name}")
            return jsonify({"error": f"Invalid file path: {name}"})

        fileToSave = open(name, 'w')
        filename = escape(configs.get("XLS_PHY_TOPO_FILE_BASE_PATH")) + f"{s_hostname}_{dt}.txt"
        platform = 'cisco_ios'
        username = '' # edit to reflect
        password = '' # edit to reflect
    
        #Logic to get credentials from credential management 

        #1. Find profile associated with device from device info using management ip
        sql = "SELECT d_ssh_cred_profile, d_vendor FROM c3p_deviceinfo where d_mgmtip=%s"

        mycursor.execute(sql, (s_mgmtip,))
        result = mycursor.fetchall()
        if result:
            for row in result:
                profile= row[0]
                vendor= row[1]
                logger.info("vendor ::: %s",vendor)

        #profile = ''.join(result)
        logger.info("profile name ::: %s",profile)
        sql = "SELECT cr_login_read , cr_password_write FROM c3p_m_credential_management where cr_profile_name=%s"
        mycursor.execute(sql, (profile,))
        resultArray = mycursor.fetchall()
        if resultArray: 
            for row in resultArray:
                username= row[0]
                password= row[1]
            logger.info("username ::: %s",username)
            # logger.info("password ::: %s",password)
        y = []
        host = s_mgmtip.strip()
        comandarr = []
        if vendor == 'Cisco':
            sql = "SELECT vc_start FROM c3p_m_vendor_specific_command where vc_repetition= 'PHTO' and vc_vendor_name = 'Cisco'"
            logger.info("sql ::: %s",sql)
            mycursor.execute(sql)
            resultArray = mycursor.fetchall()
            for row in resultArray:
                comandarr.append(row[0])
            logger.info("comandarr ::: %s",comandarr)
            device = ConnectHandler(device_type=platform, ip=host, username=username, password=password)
            device.enable()
        elif vendor == 'Juniper':
            sql = "SELECT vc_start FROM c3p_m_vendor_specific_command where vc_repetition= 'PHTO' and vc_vendor_name = 'Juniper'"
            mycursor.execute(sql)
            resultArray = mycursor.fetchall()
            for row in resultArray:
                comandarr.append(row[0])
            logger.info("comandarr ::: %s",comandarr)
            platform = 'juniper'
            device = ConnectHandler(device_type=platform, ip=host, username=username, password=password)
            device.enable()
        if comandarr is not None:
            for cmd in comandarr:
                if vendor == 'Cisco':
                    output = device.send_command('terminal length 0')
                output = device.send_command(cmd)
                if vendor == 'Cisco':
                    y.append("RP/0/RSP0/CPU0:s3cw-e-707#"+cmd)
                    y.append(dt)
                    if "show version" in cmd:
                        y.append(" ")
                y.append(output)
                if vendor == 'Cisco':
                    y.append(" ")
                    y.append("RP/0/RSP0/CPU0:s3cw-e-707#")
                    if "show platform" in cmd:
                        y.append("RP/0/RSP0/CPU0:s3cw-e-707#exit")
        for x in y:
            print(x)
        fileToSave.close()
    
        
    except Exception as err:
        logger.error("Exception in triggerPhysicalTopology: %s",err)
    finally:
        mydb.close
        #if device:
            # device.close()

    logger.debug("FILENAME::: %s",filename)
    return(filename)

def createCSV(content):
    inValue = []
    filenameargs = ''
    entityList = []
    s_device_id = content['s_device_id']
    s_mgmt_ip= content['s_mgmtip']
    created_by = content['created_by']
    logger.debug('c3p_physical_topology:createCSV:Input for createCSV')
    mydb = Connections.create_connection()
    try:
        mycursor = mydb.cursor(buffered=True)
        logger.debug('Files:::%s',content['files'])
        for item in content['files']:
            filenameargs += item+"\t"
        logger.debug('Before reading perl')
        #logic to get script from mongo
        content['filename'] = "parse_all_data_all_nodes_python.pl"
        #scriptcontent= yangExtractor.getScript(content)
        sql = "SELECT d_vendor FROM c3p_deviceinfo where d_mgmtip=%s"
        vendor = ''
        mycursor.execute(sql, (s_mgmt_ip,))
        result = mycursor.fetchall()
        for row in result:
            vendor= row[0]
            logger.info("vendor ::: %s",vendor)
        #write this to temp file for execution
        #ScriptFolder = os.path.dirname(os.path.abspath(__file__), temp.pl)
        #tempFilePath = os.path.join(ScriptFolder,"temp.pl")
        if vendor == 'Cisco':
            filename='temp.pl'
        elif vendor == 'Juniper':
            filename ='tempJuniper.pl'
        else:
            filename='temp.pl'
        tempFilePath = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
        
        logger.info("Script path:::%s",tempFilePath)
      

        logger.debug("Before command")
        
        command = "python "+configs.get("PERL_SCRIPT_RUN")+" "+ filenameargs +" "+ vendor
        logger.debug("Command ::: %s",command)
      
        my_cmd_output = os.system(escape(command))
        time.sleep(5)
        logger.debug("After pop open")
       
        createdDateTime =datetime.today().strftime('%Y-%m-%d %H:%M:%S')
        #Logic to load xlsx file in c3p DB
        xmlFileBasePath = configs.get("XLS_PHY_TOPO_FILE_BASE_PATH")
        xslsfile = xmlFileBasePath + str(content['s_device_id']) + ".xlsx"
        logger.debug("Before open workbook")
        #xslsfile = "D:\\csr1000v.xlsx"
        wb = xlrd.open_workbook(xslsfile)
        logger.debug("After open workbook")

        sheet = wb.sheet_by_index(0)
        myResult = None
        t_device_id = 0
        t_mgmt_ip = ""
        s_interface_ip = ""
        for i in range(sheet.nrows):
           
            #Logic for s_interface_ip check if we can get from fid table based on source port
            if not sheet.cell_value(i, 2):
                if sheet.cell_value(i, 2) != 'SourcePort' and sheet.cell_value(i, 2) != '':
                    query = "select fid_ip_address from c3p_t_fork_inv_discrepancy where fid_discovered_value='"+sheet.cell_value(i, 2)
                    try:
                        row_count = mycursor.execute(query)
                        myResult = mycursor.fetchall()  
                        logger.info('createCSV :: myResult : %s', myResult)
            
                    except mysql.connector.errors.ProgrammingError as e:
                        logger.error('createCSV :: Exception in select fid_ip_address from c3p_t_fork_inv_discrepancy  : %s', e)
                    if row_count is not None:
                        val=myResult[0]
                        s_interface_ip= val[0]
                        logger.info('createCSV :: t_device_id : %s', t_device_id)
          


            #Logic to find t_device_id, t_mgmt_ip  from device info table from hostname and dcomm=0 only one row
            if not sheet.cell_value(i, 5):
                if sheet.cell_value(i, 5) != 'DestDevice' and sheet.cell_value(i, 5) != '':
                    sqlRes= "select d_id, d_mgmtip from c3p_deviceinfo where d_hostname='"+sheet.cell_value(i, 5)+ "' and d_decomm = 0 "
                    try:
                        row_count = mycursor.execute(sqlRes)
                        myResult = mycursor.fetchall()  
                        logger.info('createCSV :: myResult : %s', myResult)
            
                    except mysql.connector.errors.ProgrammingError as e:
                        logger.error('createCSV :: Exception in select d_id, d_mgmtip from c3p_deviceinfo where d_hostname : %s', e)
                    if row_count is not None:
                        val=myResult[0]
                        t_device_id = val[0]
                        t_mgmt_ip = val[1]
                        logger.info('createCSV :: t_device_id : %s', t_device_id)
         
            if sheet.cell_value(i, 10) == "CDP" or sheet.cell_value(i, 10) == "LLDP" and sheet.cell_value(i, 10)!='':
                entityList.append(TopologyEntityET("LINK",s_device_id,content['hostname'],s_mgmt_ip,
                sheet.cell_value(i, 2),s_interface_ip,
                sheet.cell_value(i, 10),sheet.cell_value(i, 9),
                sheet.cell_value(i, 5),t_device_id, t_mgmt_ip,
                sheet.cell_value(i, 8),sheet.cell_value(i, 10),sheet.cell_value(i, 9),created_by,createdDateTime))

        #Bulk insert
        # query = "INSERT INTO c3p_t_topology (t_topology_type, s_device_id, s_hostname,s_mgmtip,s_interface,s_interface_ip,s_topo_type_name,s_topo_type_id,t_hostname,t_device_id,t_mgmtip,t_neighbor,t_topo_type_name,t_topo_type_id, tp_created_by,tp_created_date) VALUES ('{}', '{}', '{}', '{}', '{}', '{}', '{}', '{}', '{}', '{}', '{}', '{}', '{}', '{}', '{}', '{}')"
        # for obj in entityList: 
        #     formattedQuery=query.format(obj.t_topology_type, obj.s_device_id,obj.s_hostname,obj.s_mgmtip,obj.s_interface,obj.s_interface_ip,obj.s_topo_type_name,obj.s_topo_type_id,obj.t_hostname,obj.t_device_id,obj.t_mgmtip,obj.t_neighbor,obj.t_topo_type_name,obj.t_topo_type_id,obj.tp_created_by,obj.tp_created_date)
        #     mycursor.execute(formattedQuery)
        #     mydb.commit()

        #Response array population
        #For order
        #sql = "INSERT INTO c3p_t_topology (t_topology_type, s_device_id, s_hostname, s_mgmtip, s_interface, s_interface_index,s_interface_ip, s_topo_type_name, s_topo_type_id, t_device_id, t_hostname, t_mgmtip,  t_neighbor, t_neighbor_index, t_neighbor_ip, t_topo_type_name, t_topo_type_id, tp_created_by, tp_created_date) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
        if(len(entityList)>0):
            entityList.pop(0)
            for item in entityList:
                inVal = (item.t_topology_type, item.s_device_id,item.s_hostname,item.s_mgmtip,item.s_interface,"",item.s_interface_ip,item.s_topo_type_name,item.s_topo_type_id,item.t_device_id,item.t_hostname,item.t_mgmtip,item.t_neighbor,"","",item.t_topo_type_name,item.t_topo_type_id,item.tp_created_by, item.tp_created_date)
                inValue.append(inVal)

        logger.info("Invalue:::%s",inValue)

    except Exception as err:
        logger.error("Exception in triggerPhysicalTopology createCSV: %s",err)
    return inValue

def mongofileinsert(content):
    client = MongoClient(configs.get("MONGO_URL"))
    db=client.c3pdbschema
    response = ''
    filepath  = content['filepath']
    # Validating the file path1
    base_path = "/opt/"
    filename = os.path.basename(filepath)
    filepath = os.path.normpath(os.path.join(base_path, filename))
    if not filepath.startswith(base_path):
        logger.error(f"Invalid file path: {filepath}")
        return jsonify({"error": f"Invalid file path: {filepath}"})
    filename = content['filename']
    try:
        mongodb = Connections.create_mongo_connection()
        fs = GridFS(db,"scripts")
        if(fs.exists(filename=filename)):
            logger.error("Exception in mongofileinsert: File exists")
            response = "File exists"
        else:
            with open(filepath,'rb') as f:
                yang = fs.put(f, content_type='application/text', filename=filename)
                response = "File inserted"
    except Exception as err:
        logger.error("Exception in mongofileinsert: %s",err)
    return response