import difflib
import logging
import os
import xmltodict
from datetime import datetime

from c3papplication.common import Connections
from c3papplication.conf.springConfig import springConfig

logger = logging.getLogger(__name__)

configs = springConfig().fetch_config()

def xmlComparison(request):
    input_file = request.get("config_file", "")
    template_id = request.get("template_id", "")
    req_id = request.get("requestId", "")
    req_version = request.get("version", "")

    if not input_file or not template_id:
        return {"error": "Invalid input parameters"}
    
    # Validating the file path
    base_path = configs.get("XML_Config_filepath", "")
    filename = os.path.basename(input_file)
    fullpath = os.path.normpath(os.path.join(base_path, filename))
    if not fullpath.startswith(base_path):
        logger.error(f"Invalid file path: {fullpath}")  # nosem: python.logging.security.injection
        return jsonify({"error": f"Invalid file path: {fullpath}"})

    if not os.path.exists(fullpath):
        logger.error(f"File not found: {fullpath}") # nosem: python.logging.security.injection
        return jsonify({"error": f"File not found: {fullpath}"})
    
    try:
        with open(fullpath, 'r') as myfile:
            input_file_json = xmltodict.parse(myfile.read())
    except Exception as e:
        logger.error(f"Error occurred while processing file: {e}")
        return {"error": f"Error occurred while processing file"}
    
    # Reading input file and actual file from db
    actual_file, message = create_backupfile(template_id)
    if not actual_file:
        return {"error": message}
    actual_file_json = xmltodict.parse(actual_file)

    input_file_mo=[]
    actual_file_mo=[]
    baselinefileNomoinbackupfile=[]
    try:
        # Comparing and removing uncommon managedObjects between actual and input files
        len_input_file=len(input_file_json["raml"]["cmData"]["managedObject"])
        len_actual_file=len(actual_file_json["raml"]["cmData"]["managedObject"])
        for item in input_file_json["raml"]["cmData"]["managedObject"][0:len_input_file]:
            j1=(item["@distName"])
            file1item=list(filter(lambda y:y["@distName"]==j1,actual_file_json["raml"]["cmData"]["managedObject"]))
            if file1item:
                input_file_mo.append(item)
            else:
                baselinefileNomoinbackupfile.append(item)
    
            for item2 in actual_file_json["raml"]["cmData"]["managedObject"][0:len_actual_file]:
                if (item["@distName"] == item2["@distName"]):
                    actual_file_mo.append(item2)

        del input_file_json["raml"]["cmData"]["managedObject"]
        input_file_json["raml"]["cmData"]["managedObject"]=input_file_mo
        input_file_xml = xmltodict.unparse(input_file_json, pretty=True)
        input_file_xml = input_file_xml.replace('<?xml version="1.0" encoding="utf-8"?>',"",1).strip()
        # logger.info(f"Input file xml: {input_file_xml}")
        del actual_file_json["raml"]["cmData"]["managedObject"]
        actual_file_json["raml"]["cmData"]["managedObject"]= actual_file_mo
        actual_file_xml = xmltodict.unparse(actual_file_json, pretty=True)
        actual_file_xml = actual_file_xml.replace('<?xml version="1.0" encoding="utf-8"?>',"",1).strip()   
        # logger.info(f"Actual file xml {actual_file_xml}")

        difference = difflib.HtmlDiff(tabsize=4)
        html = difference.make_file(fromlines=actual_file_xml.splitlines(), fromdesc="Present Configuration",
                                    tolines=input_file_xml.splitlines(), todesc="Expected Configuration")
        logger.info("Compared HTML generation successful")
        
        # Variables to store token changes analysed result
        added = 0
        no_change = 0
        deleted = 0
        modified = 0
        actualJsonData = {}
        compareResult = {}
        configuredJsonData = {}
        for base_item in input_file_mo:
            if base_item.get('p', ""):
                pValues = base_item.get('p', []) if type(base_item.get('p', [])) == list else [base_item['p']]
                for p in pValues:
                    key = base_item['@distName'] + '::' + p['@name']
                    configuredJsonData[key] = p['#text']
            if base_item.get('list', ""):
                list_item = base_item.get('list')
                for each in list_item:
                    if each.get('p', ""):
                        key = base_item['@distName'] + '::' + each['@name']
                        configuredJsonData[key] = each['p']
                    else:
                        items = each.get('item', {})
                        pValues = items.get('p', []) if type(items.get('p', [])) == list else [items['p']]
                        for p in pValues:
                            key = base_item['@distName'] + '::' + each['@name'] + '/' +  p['@name'] 
                            configuredJsonData[key] = p['#text']
                

        for back_item in actual_file_mo:
            if back_item.get('p', ""):
                pValues = back_item.get('p', []) if type(back_item.get('p', [])) == list else [back_item['p']]
                for p in pValues:
                    key = back_item['@distName'] + '::' + p['@name']
                    actualJsonData[key] = p['#text']
            if back_item.get('list', ""):
                list_item = back_item.get('list')
                for each in list_item:
                    if each.get('p', ""):
                        key = back_item['@distName'] + '::' + each['@name']
                        actualJsonData[key] = each['p']
                    else:
                        items = each.get('item', {})
                        pValues = items.get('p', []) if type(items.get('p', [])) == list else [items['p']]
                        for p in pValues:
                            key = back_item['@distName'] + '::' + each['@name'] + '/' +  p['@name']
                            actualJsonData[key] = p['#text']
                        
        configuredKeys = configuredJsonData.keys()
        actualKeys = actualJsonData.keys()

        logger.info("Starting the token comparison")
        for key in actualJsonData.keys():
            # Storing the key information for the token comparison
            compare_dict = {
                'mo_value': key.split('::')[0],
                'parameter_audited': key.split('::')[1],
                'expected_result': configuredJsonData.get(key, ''),
                'actual_value': actualJsonData.get(key, '')
            }
            # Comparing the configured values with the actual values and setting the flag of result
            if key in configuredKeys:
                if configuredJsonData[key] == actualJsonData[key]:
                    compare_dict['flag'] = 'NoChange'
                    no_change += 1
                else:
                    compare_dict['flag'] = 'Modified'
                    modified += 1
            else:
                compare_dict['flag'] = 'Additional'
                added += 1
            compareResult[key] = compare_dict

        # For those tokens missing in the actual keys we are flagging it to be deleted
        for key in configuredKeys:
            if key not in actualKeys:
                compare_dict = {
                    'mo_value': key.split('::')[0],
                    'parameter_audited': key.split('::')[1],
                    'expected_result': configuredJsonData.get(key, ''),
                    'actual_value': actualJsonData.get(key, ''),
                    'flag': 'Deleted'
                }
                compareResult[key] = compare_dict
                deleted += 1

        changes = {
            'added': added,
            'modified': modified,
            'nochange': no_change,
            'deleted': deleted
        }
        logger.info(f"Changes: {changes}") 
    except Exception as err:
        logger.error(f"Exception during comparison: {err}")
        return {"error": "Unable to do comparison"}
    
    store_status = storeToDb(compareResult, req_id, req_version, template_id)
    if not store_status:
        return {"error": "Unable to store to DB"}
    
    store_status = storeRequestToMongo(req_id, changes, html)
    if not store_status:
        return {"error": "Unable to store to DB"}
    
    return {"message": "Successfully compared and saved to database"}


def storeToDb(compared_result, req_id, req_ver, template_id):
    try:
        mydb = Connections.create_connection()
        mycursor = mydb.cursor(buffered=True)
        current_time = datetime.now()
        sql = "INSERT INTO `c3p_t_audit_dashboard_result`(adr_request_id, adr_request_version, adr_configuration_value," \
              " adr_result, adr_template_id, adr_template_value, created_date, updated_date, adr_mo_value, adr_parameter_audited) " \
              "VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        values = []
        for key in compared_result:
            config_value = compared_result[key]['expected_result']
            flag = compared_result[key]['flag']
            template_value = compared_result[key]['actual_value']
            mo_value = compared_result[key]['mo_value']
            parameter_audited = compared_result[key]['parameter_audited']
            val = (req_id, req_ver, config_value, flag, template_id, template_value, current_time, current_time, mo_value, parameter_audited)
            values.append(val)
        mycursor.executemany(sql, values)
        mydb.commit()
        mydb.close()
        status = True
    except Exception as err:
        status = False
        logger.error(f"MySQL - Exception in storingEmailData: {err}")

    return status


def create_backupfile(template_id):
    try:
        mydb = Connections.create_connection()
        mycursor = mydb.cursor(buffered=True)

        fetch_query = "SELECT A.command_value AS value FROM c3p_template_master_command_list A INNER JOIN " \
        "c3p_template_master_feature_list B ON A.master_f_id = B.master_f_id " \
        "AND B.command_type = %s ORDER BY A.command_sequence_id"

        mycursor.execute(fetch_query, (template_id,))
        values = mycursor.fetchall()
        mydb.close()
        if not values:
            message = f"Unable to find xml with template id: {template_id}"
            logger.error(f"MySQL - {message}") # nosem: python.logging.security.injection
            return ''.encode("UTF-8"), message

        xml_file = ''.join([v[0] for v in values])
        xml_file = xml_file.encode("UTF-8")
    except Exception as err:
        message = f"Exception in fetching xml file: {err}"
        logger.error(f"MySQL - {message}")
        return ''.encode("UTF-8"), "Error fetching xml file"
    
    return xml_file, "Success"


def storeRequestToMongo(req_id, changes, html):
    try:
        from bson.binary import Binary
        mongodb = Connections.create_mongo_connection()
        req_coll = mongodb['xmlcomparison']
        
        # Ensure html is not None and is a string
        if html is None or not isinstance(html, str):
            raise ValueError("HTML content is invalid.")

        data = {
            'req_id':req_id,
            'file':str(html),
            'added': changes.get('added', 0),
            'modified': changes.get('modified', 0),
            'nochange': changes.get('nochange', 0),
            'deleted': changes.get('deleted', 0)
        }
        req_coll.insert_one(data)
        status=True
        logger.info("successfully stored xml comparison data into xmlcomparison collection in mongodb")
    except Exception as err:
        status = False
        logger.error(f"Mongo - Exception in storing data: {err}")

    return status

def retrieveFromMongo(req_id):
    try:
        mongodb = Connections.create_mongo_connection()
        coll = mongodb['xmlcomparison']
        query = {'req_id':req_id}
        doc = coll.find_one(query)
        if not doc:
            logger.error("Exception in retrieving the request from mongodb")
            raise Exception
        response = {
            'configuration_value': doc.get('file', ''),
            'added': doc.get('added', 0),
            'modified': doc.get('modified', 0),
            'nochange': doc.get('nochange', 0),
            'deleted': doc.get('deleted', 0)
        } 
    except Exception as err:
        logger.error(f"Mongo - Exception in retrieving file: {err}")
    return response