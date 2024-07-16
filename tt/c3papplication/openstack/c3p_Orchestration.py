import json,logging
from heatclient.client import Client as Heat_Client
from keystoneclient.v3 import Client as Keystone_Client
import ast
from c3papplication.common import Connections

logger = logging.getLogger(__name__)

def read_Template(template_id):
    stack_template = ""
    mydb = Connections.create_connection()    
    try:
        mycursor = mydb.cursor(buffered=True)
        sql="SELECT command_value FROM c3p_template_master_command_list where master_f_id = %s order by  command_sequence_id asc"
        mycursor.execute(sql, (str(template_id),))
        template = mycursor.fetchall()
        template = [tuple(ele for ele in sub if ele != '\n') for sub in template] 
        for value in range(len( template)):
            for data in template[value]:
                stack_template+=str(data)    
        logger.debug('read_Template::Template :: %s', stack_template)
    except Exception as err:
        logger.error("read_Template :: Exception: %s",err)
    finally:
        mydb.close
    return(stack_template)

def get_keystone_creds():
    creds = {}
    creds['username'] = "C3P"
    creds['password'] = "c3p_123"
    creds['auth_url'] = "http://10.207.0.11:5000/v3"
    creds['project_name'] = "C3P"
    creds['project_domain_name'] = "default"
    creds['user_domain_name'] = "default"
    return creds

def deployStack(template_id, stackName, parameters):
    stackRes={}
    try:
        creds = get_keystone_creds()
        logger.debug('deployStack::openstack credentials:: %s', stackRes)
        ks_client = Keystone_Client(**creds)
        heat_endpoint = ks_client.service_catalog.url_for(service_type='orchestration', endpoint_type='publicURL')
        heatclient = Heat_Client('1', heat_endpoint, token=ks_client.auth_token)
        stacktemplate=read_Template(template_id)
        keys = ['templateId', 'stack_name']
        for key in keys:
            parameters.pop(key, None)

        stack = heatclient.stacks.create(stack_name=stackName,template=stacktemplate, parameters=parameters)
        uid = stack['stack']['id']
        stack = heatclient.stacks.get(stack_id=uid).to_dict()

        while stack['stack_status'] == 'CREATE_IN_PROGRESS':
            # print ("Stack in state: {}".format(stack['stack_status']))
            stack = heatclient.stacks.get(stack_id=uid).to_dict()
        stackRes = heatclient.stacks.get(stack_id=stackName)
        stackRes = str(stackRes).replace('<Stack ', '').replace('>', '')
        stackRes=ast.literal_eval(stackRes)
        stackRes=json.dumps(stackRes)
    except Exception as err:
        logger.error("deployStack::Exception in Stack creation: %s",err)
        # print("stack error",err) 
    logger.debug('deployStack::Stackstack response :: %s', stackRes)
    return stackRes
