from datetime import datetime
from flask import jsonify
import json,logging
import mysql.connector
from ncclient import manager
import os.path
from os import path
from c3papplication.conf.springConfig import springConfig
from jproperties import Properties
import xml.dom.minidom
import json

configs = springConfig().fetch_config()

logger = logging.getLogger(__name__)

def editConf(inputJson):
    response = dict()  
    uname=inputJson.get('username')
    pwd=inputJson.get('password')
    mgmtip=inputJson.get('managementip')
    vnfdata=inputJson.get('vnfdata')
    logger.info("File Name"+vnfdata)

    flag = True
    try:
        if(len(vnfdata)!=0):
            fromlines=vnfdata
        else:
            response['Error']= 'Config file not found'
            flag = False

        if(flag == True):
            m = manager.connect(host=mgmtip, port=830, username=uname,
                            password=pwd, device_params={'name': 'csr'})
            result = m.edit_config(target='running', config=fromlines)
            response['Error']= '' 
            response['Result']= 'Ok' 
            #int_info = xml_doc.getElementsByTagName(args.key)
            #response['Result']= result


    except Exception as err:
        logger.error("Exception in editConf: %s",err)
    return response

def performTestConf(inputJson): 
    response = dict()  
    uname=inputJson.get('username')
    pwd=inputJson.get('password')
    mgmtip=inputJson.get('managementip')
    filtertosearch=inputJson.get('filtertosearch')
    filepath=inputJson.get('filepath')
    flag = True

    # Validating the file path
    base_path = "/opt/jboss/C3PConfig/PythonScript/"
    filename = os.path.basename(filepath)
    filepath = os.path.normpath(os.path.join(base_path, filename))
    if not filepath.startswith(base_path):
        logger.error(f"Invalid file path: {filepath}")
        return {"error": f"Invalid file path: {filepath}"}
    try:
        if(path.isfile(filepath)):
            with open(filepath, 'r') as f:
                fromlines=f.read()
        else:
            response['Error']= 'Config file not found'
            flag = False

        if(flag == True):
            m = manager.connect(host=mgmtip, port=830, username=uname,
                            password=pwd, device_params={'name': 'csr'})
            entity_filter = fromlines
            outcome =''
            outcome1 =''
            errorMsg =''
            try:
                result = m.get(entity_filter)
                xml_doc = xml.dom.minidom.parseString(result.xml)
                int_info = xml_doc.getElementsByTagName(filtertosearch)
                for x in int_info:
                    outcome1 =''
                    outcome1 =str(x.childNodes[0].data) 
                    outcome = outcome+outcome1
                    logger.info('performTestConf -outcome-> %s',outcome)
            except Exception as e:
                logger.error('Failed to execute <get> RPC: {}'.format(e)) 
                errorMsg = 'failed'              
            response['Error']= errorMsg 
            response['Result']= outcome 
    except Exception as err:
        logger.error("Exception in performTestConf: %s",err)
    return response    
