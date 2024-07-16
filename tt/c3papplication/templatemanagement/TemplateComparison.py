
import json,logging

from pysnmp.proto.rfc1902 import Null
from c3papplication.common import Connections
from jproperties import Properties
import difflib

from c3papplication.templatemanagement.CommandDeatilsVO import CommandDetails
from c3papplication.templatemanagement.FeatureDetailsVO import FeatureDetails
from c3papplication.templatemanagement.DeviceDetailsVO import DeviceDetails
from c3papplication.conf.springConfig import springConfig


logger = logging.getLogger(__name__)

configs = springConfig().fetch_config()

def computeTemplateDifference(content):
    mydb = Connections.create_connection()
    logger.debug('TemplateComparison -> Request Json:::%s',content)
    mycursor = mydb.cursor(buffered=True)
    data = {}
    input1 = None
    if content is not Null:
        for item in content:
            commandList=[]
            logger.debug('TemplateComparison -> item value:::%s', item)
            finaltemplate = item['templateId'] + '_V' + item['templateVersion']
            logger.debug('TemplateComparison -> Final Template:::%s', finaltemplate)
            mycursor.execute("SELECT * FROM c3p_template_master_feature_list where is_Save='1' and command_type=%s;", (finaltemplate,))
            for feature in mycursor.fetchall():
                logger.debug('feature value %s', feature)
                mycursor.execute("select c3p_template_master_command_list.command_value,c3p_template_master_command_list.command_id,c3p_template_transaction_command_list.command_position,c3p_template_master_command_list.no_form_command,c3p_template_master_command_list.command_type from c3p_template_master_command_list ,c3p_template_transaction_command_list where c3p_template_master_command_list.command_id=%s and c3p_template_master_command_list.command_id =c3p_template_transaction_command_list.command_id and c3p_template_master_command_list.command_sequence_id =c3p_template_transaction_command_list.command_sequence_id and c3p_template_transaction_command_list.command_template_id=%s;", (str(feature[0]), finaltemplate, ))
                commands = mycursor.fetchall()
                for command in commands:
                    commandList.append(command[0])
            if input1 is None:
                commandList.append(command[0])
                input1 = ' '.join(commandList)
                logger.debug('TemplateComparison -> Input 1 is:::%s',input1)
            else:
                commandList.append(command[0])
                input2 = ' '.join(commandList)
                logger.debug('TemplateComparison -> Input 2 is:::%s',input2)
        if input1 != None and input2 != None:
            l1= input1.split("\n")
            l2= input2.split("\n")
            hDiff = difflib.HtmlDiff()
            hDiff._styles = """ """
            hD = hDiff.make_file(l1,l2)
            logger.debug('TemplateComparison -> File value:::%s', hD)
            data['comparisonFile'] = hD
            json_data = json.dumps(data)   
        else:
            logger.error("TemplateComparison -> Either of the inputs is empty")
    return json_data
