from flask import Flask,request,jsonify
from flask_api import status
from c3papplication.common import Connections
import json,logging

logger = logging.getLogger(__name__)

# mydb = Connections.create_connection()
# mycursor = mydb.cursor(buffered=True)


def listRf(id,args) :       
    global data
    print("ID here::",id)
    fieldsData = []   
    filterQuery ="" 
    mydb = Connections.create_connection()
    try:
        mycursor = mydb.cursor(buffered=True)
        if(len(args) != 0):
            field = args["field"]        
            fieldsData = list(field.split(","))
            filterQuery = setFilterData(args)
            
        data = {}
        rfdata = []
        params = []
        if not id:
            resourceSql = "SELECT rf_id ,rf_name,rf_desription,rf_functiontype,rf_role,rf_version,rf_value,rf_priority,rf_category,rf_startdate,rf_enddate,rf_href,rf_basetype,rf_schemalocation,rf_type FROM c3p_resourcefunction"
        else:
            resourceSql = "SELECT rf_id ,rf_name,rf_desription,rf_functiontype,rf_role,rf_version,rf_value,rf_priority,rf_category,rf_startdate,rf_enddate,rf_href,rf_basetype,rf_schemalocation,rf_type FROM c3p_resourcefunction where rf_id = %s"
            params.append(id)
        
        if filterQuery:
            resourceSql +=  " WHERE %s"
            params.append(filterQuery)
        mycursor.execute(resourceSql, params)
        resourceResult = mycursor.fetchall()    
        for rf_result in resourceResult :
            temp_data = {}        
            temp_data["category"] =rf_result[8]
            temp_data["discreption"] =rf_result[1]
            temp_data["endDate"] =rf_result[10]
            temp_data["functionType"] =rf_result[3]
            temp_data["href"] =rf_result[11]
            temp_data["id"] =rf_result[0]
            temp_data["lifecycleState"] ="Field not present in DB"
            temp_data["name"] =rf_result[1]
            temp_data["priority"] =rf_result[7]
            temp_data["role"] =rf_result[4]
            temp_data["startDate"] =rf_result[9]
            temp_data["value"] =rf_result[6]
            temp_data["version"] =rf_result[5]
            temp_data["@baseType"] =rf_result[12]
            temp_data["@schemaLocation"] =rf_result[13]
            temp_data["@type"] =rf_result[14]
            if(len(fieldsData)!=0):
                for fields in fieldsData:                     
                    if("connectivity"== fields):
                        temp_data["connectivity"] = setConnectivity(rf_result[0])
                    if("connectionPoint"== fields):
                        temp_data["connectionPoint"] = setConnectionPointData(rf_result[0])
                    if("resourceRelationship"== fields):
                        temp_data["resourceRelationship"] = setresourceRelationshipData(rf_result[0])
            else:        
                temp_data["connectivity"] = setConnectivity(rf_result[0])
                temp_data["connectionPoint"] = setConnectionPointData(rf_result[0])
                temp_data["resourceRelationship"] = setresourceRelationshipData(rf_result[0])
            rfdata.append(temp_data)
    except Exception as err:
        logger.error("tmf::c3p_tmf_get_api::listRf: %s",err)     
    finally:
        mydb.close
    return jsonify(rfdata),status.HTTP_200_OK

def setFilterData(args):
    filterQuery = ""
    count = 0
    for i in args:          
        if(count>0 and filterQuery!=""):
            filterQuery = filterQuery+" and "
        if("category"== i):
            filterQuery = filterQuery +"rf_category = '"+args[i]+"'"
        if("description"== i):
            filterQuery = filterQuery +"rf_desription = '"+args[i]+"'"
        if("endDate"== i):
            filterQuery = filterQuery +"rf_enddate = '"+args[i]+"'"
        if("functionType"== i):
            filterQuery = filterQuery +"rf_functiontype = '"+args[i]+"'"
        if("href"== i):
            filterQuery = filterQuery +"rf_href = '"+args[i]+"'"
        if("id"== i):
            filterQuery = filterQuery +"rf_id = '"+args[i]+"'"
        if("name"== i):
            filterQuery = filterQuery +"rf_name = '"+args[i]+"'"
        if("priority"== i):
            filterQuery = filterQuery +"rf_priority = '"+args[i]+"'"
        if("role"== i):
            filterQuery = filterQuery +"rf_role = '"+args[i]+"'"
        if("startDate"== i):
            filterQuery = filterQuery +"rf_startdate = '"+args[i]+"'"
        if("value"== i):
            filterQuery = filterQuery +"rf_value = '"+args[i]+"'"
        if("version"== i):
            filterQuery = filterQuery +"rf_version = '"+args[i]+"'"
        count = count + 1
    print(filterQuery)
    return filterQuery     

def setConnectivity(rfId):
    cndata = []
    mydb = Connections.create_connection()
    try:
        mycursor = mydb.cursor(buffered=True)
        connectivitySql = "select cy_rowid,cy_connectivity_id,rf_id,cy_name,cy_description,cy_type,cy_basetype,cy_schemalocation from c3p_connectivity where rf_id = %s"
        mycursor.execute(connectivitySql, (rfId,))
        connectivityResult = mycursor.fetchall()
        #cn_fields_names = [col[0] for col in mycursor.description]
        for cn_result in connectivityResult :
            temp_data = {}
            #for i in range(0,len(cn_result)):
            #   temp_data[cn_fields_names[i]] = cn_result[i]
            temp_data["discreption"] =cn_result[4]
            temp_data["id"] =cn_result[0]
            temp_data["name"] =cn_result[3]
            temp_data["@baseType"] =cn_result[6]
            temp_data["@schemaLocation"] =cn_result[7]
            temp_data["@type"] =cn_result[5]
            temp_data["connection"] = setConnection(cn_result[0])
            cndata.append(temp_data)
    except Exception as err:
        logger.error("tmf::c3p_tmf_get_api::setConnectivity: %s",err)     
    finally:
        mydb.close
    return cndata

def setConnection(cnId):
    conndata = []
    mydb = Connections.create_connection()
    try:
        mycursor = mydb.cursor(buffered=True)
        connectionsql = "select co_rowid,cy_connectivity_id,co_connection_name,co_association_type,co_endpoint_a ,co_endpoint_z from c3p_connections where co_rowid =%s" 
        mycursor.execute(connectionsql, (cnId,))
        connectionResult = mycursor.fetchall()
        #cn_fields_names = [col[0] for col in mycursor.description]
        for cn_result in connectionResult :
            temp_data = {}                
        #   for i in range(0,len(cn_result)):
        #      temp_data[cn_fields_names[i]] = cn_result[i]                      
            temp_data["associationType"] =cn_result[4]
            temp_data["id"] =cn_result[0]
            temp_data["name"] =cn_result[3]
            temp_data["@baseType"] ="Field not present in DB"
            temp_data["@schemaLocation"] ="Field not present in DB"
            temp_data["@type"] ="Field not present in DB"
            endpointData = []
            if(cn_result[4] !=  None):            
                endpointData.append(setEndpoint(cn_result[4]))
            if(cn_result[5] !=  None):            
                endpointData.append(setEndpoint(cn_result[5]))
            temp_data["endPoint"] = endpointData
            conndata.append(temp_data)
    except Exception as err:
        logger.error("tmf::c3p_tmf_get_api::setConnection: %s",err)     
    finally:
        mydb.close    
    return conndata

def setEndpoint(eId):       
    temp_data = {}
    mydb = Connections.create_connection()
    try:
        mycursor = mydb.cursor(buffered=True)
        if(eId != None):
            endPointsql = "Select ep_rowid ,ep_name,device_id,port_id,ep_is_root,type,href,referredtype,basetype,ep_schemalocation from c3p_endpoints where ep_rowid =%s" 
            mycursor.execute(endPointsql, (eId,))
            endPointResult = mycursor.fetchone()
            #en_fields_names = [col[0] for col in mycursor.description]            
            #for i in range(0,len(endPointResult)):
            #   temp_data[en_fields_names[i]] = endPointResult[i]   
            if(endPointResult != None ):
                temp_data["href"] =endPointResult[6]
                temp_data["id"] =endPointResult[0]
                temp_data["isRoot"] =endPointResult[4]
                temp_data["name"] =endPointResult[1]
                temp_data["@baseType"] =endPointResult[8]
                temp_data["@refferedType"] =endPointResult[7]
                temp_data["@schemaLocation"] =endPointResult[9]
                temp_data["@type"] =endPointResult[5]
                temp_data["connectionPoint"]=setConnectionPoint(endPointResult[3])
    except Exception as err:
        logger.error("tmf::c3p_tmf_get_api::setEndpoint: %s",err)     
    finally:
        mydb.close
    return temp_data



def setConnectionPoint(pId):       
    temp_data ={}
    mydb = Connections.create_connection()
    try:
        mycursor = mydb.cursor(buffered=True)
        if(pId != None):
            portsql = "select port_id ,port_name,version,href,port_status,baseType,referredType,schemaLocation,type from c3p_ports where port_id =%s" 
            mycursor.execute(portsql, (pId,))
            portResult = mycursor.fetchone()        
            temp_data = setConnectionJsonData(portResult)  
    except Exception as err:
        logger.error("tmf::c3p_tmf_get_api::setConnectionPoint: %s",err)     
    finally:
        mydb.close 
    return temp_data


def setConnectionPointData(rfId):
    #import pdb;pdb.set_trace()
    conndata = []
    mydb = Connections.create_connection()
    try:
        mycursor = mydb.cursor(buffered=True)
        portsql = "SELECT rr_rowid,rr_rf_id,resource_id FROM c3p_resource_relationships where rr_rf_id =%s" 
        mycursor.execute(portsql, (rfId,))
        portResult = mycursor.fetchall()
        for port in portResult :
            connectionsql = "select slot_id,slot_name,device_id from c3p_slots where device_id =%s" 
            mycursor.execute(connectionsql, (port[2],))
            connectionResult = mycursor.fetchall()
            for conn in connectionResult :
                sql = "SELECT card_id,card_name,slot_id FROM c3p_cards where slot_id =%s" 
                mycursor.execute(sql, (conn[0],))
                dataResult = mycursor.fetchall()                        
                for cn_result in dataResult :
                    portquery = "select port_id ,port_name,version,href,port_status,baseType,referredType,schemaLocation,type from c3p_ports where card_id =%s" 
                    mycursor.execute(portquery, (cn_result[0],))
                    portQueryResult = mycursor.fetchall()
                    #cn_fields_names = [col[0] for col in mycursor.description]  
                    for result in portQueryResult :                           
                        conndata.append(setConnectionJsonData(result))
    except Exception as err:
        logger.error("tmf::c3p_tmf_get_api::setConnectionPointData: %s",err)     
    finally:
        mydb.close                
    return conndata
        
def setConnectionJsonData(portResult):
    temp_data = {}
    try:
        if(portResult!= None):
            temp_data["href"] =portResult[3]
            temp_data["id"] =portResult[0]
            temp_data["version"] =portResult[2]
            temp_data["name"] =portResult[1]
            temp_data["@baseType"] =portResult[5]
            temp_data["@refferedType"] =portResult[6]
            temp_data["@schemaLocation"] =portResult[7]
            temp_data["@type"] =portResult[8]
    except Exception as err:
        logger.error("tmf::c3p_tmf_get_api::setConnectionJsonData: %s",err)    
    return temp_data

def setresourceRelationshipData(rfId):
    resourceData = []
    mydb = Connections.create_connection()
    try:
        mycursor = mydb.cursor(buffered=True)
        resourcesql = "SELECT rr_rowid,rr_rf_id,resource_id,rr_relationshiptype,rr_basetype,rr_schemalocation,rr_type,resource_referredtype FROM c3p_resource_relationships where rr_rf_id =%s" 
        mycursor.execute(resourcesql, (rfId,))
        resourceResult = mycursor.fetchall()
        for resource in resourceResult :
            temp_data = {}       
            temp_data["relationshipType"] =resource[3]
            temp_data["@baseType"] =resource[4]
            temp_data["@refferedType"] =resource[7]
            temp_data["@schemaLocation"] =resource[5]
            temp_data["@type"] =resource[6]
            temp_data["resource"]= setResourceData(resource[2])
            resourceData.append(temp_data)
    except Exception as err:
        logger.error("tmf::c3p_tmf_get_api::setActivationFeatureData: %s",err)     
    finally:
        mydb.close
    return resourceData

def setResourceData(dId):
    mydb = Connections.create_connection()
    try:
        mycursor = mydb.cursor(buffered=True)
        deviceSql ="Select d_id ,d_hostname from c3p_deviceinfo where d_id = %s"
        mycursor.execute(deviceSql, (dId,))
        deviceResult = mycursor.fetchone()
        resourcesql = "SELECT r_device_id,r_category,r_adminState,r_description,r_href,r_opertionalState,r_resourceStatus,r_resourceVersion,r_endOperatingDate,r_startOperatingDate,r_usageState,r_resourceSpecification,r_basetype,r_referredtype,r_schemalocation,r_type  FROM c3p_deviceinfo_ext where r_device_id = %s"
        mycursor.execute(resourcesql, (dId,))
        resourceResult = mycursor.fetchone()
        temp_data = {}       
        temp_data["administrativeType"] =resourceResult[3]
        temp_data["category"] =resourceResult[3]
        temp_data["description"] =resourceResult[3]
        temp_data["endOperationDate"] =resourceResult[3]
        temp_data["href"] =resourceResult[3]
        temp_data["id"] =deviceResult[0]
        temp_data["name"] =deviceResult[1]
        temp_data["operationalState"] =resourceResult[3]
        temp_data["resourceStatus"] =resourceResult[3]
        temp_data["resourceVersion"] =resourceResult[3]
        temp_data["startOperatingDate"] =resourceResult[3]
        temp_data["usageState"] =resourceResult[3]
        temp_data["@baseType"] =resourceResult[4]
        temp_data["@refferedType"] =resourceResult[7]
        temp_data["@schemaLocation"] =resourceResult[5]
        temp_data["@type"] = resourceResult[6]   
        temp_data["resourceCharacteristics"] = setresourceCharacteristicData(deviceResult[0]) 
        temp_data["activationFeature"] = setActivationFeatureData(deviceResult[0])
    except Exception as err:
        logger.error("tmf::c3p_tmf_get_api::setResourceData: %s",err)     
    finally:
        mydb.close              
    return temp_data

def setresourceCharacteristicData(dId):
    resourceData = []
    mydb = Connections.create_connection()
    try:
        mycursor = mydb.cursor(buffered=True)
        resourcesql = "select rc_characteristic_id,rc_characteristic_name,rc_characteristic_value,rc_valuetype,rc_basetype,rc_schemalocation,rc_type from c3p_resourcecharacteristics where  rc_feature_id is NULL and device_id = %s" 
        mycursor.execute(resourcesql, (dId,))
        resourceResult = mycursor.fetchall()
        for resource in resourceResult :
            temp_data = {}       
            temp_data["id"] =resource[0]
            temp_data["name"] =resource[1]
            temp_data["value"] =resource[2]
            temp_data["valueType"] =resource[3]
            temp_data["@baseType"] =resource[4]        
            temp_data["@schemaLocation"] =resource[5]
            temp_data["@type"] =resource[6]        
            resourceData.append(temp_data)
    except Exception as err:
        logger.error("tmf::c3p_tmf_get_api::setresourceCharacteristicData: %s",err)     
    finally:
        mydb.close     
    return resourceData

def setActivationFeatureData(dId):
    resourceData = []
    mydb = Connections.create_connection()
    try:
        mycursor = mydb.cursor(buffered=True)
        resourcesql = "select rc_characteristic_id,rc_characteristic_name,rc_characteristic_value,rc_valuetype,rc_basetype,rc_schemalocation,rc_type from c3p_resourcecharacteristics where  rc_feature_id is not NULL and device_id = %s" 
        mycursor.execute(resourcesql, (dId,))
        resourceResult = mycursor.fetchall()
        for resource in resourceResult :
            temp_data = {}       
            temp_data["id"] =resource[0]
            temp_data["name"] =resource[1]
            temp_data["value"] =resource[2]
            temp_data["valueType"] =resource[3]
            temp_data["@baseType"] =resource[4]        
            temp_data["@schemaLocation"] =resource[5]
            temp_data["@type"] =resource[6]        
            resourceData.append(temp_data)
    except Exception as err:
        logger.error("tmf::c3p_tmf_get_api::setActivationFeatureData: %s",err)     
    finally:
        mydb.close      
    return resourceData

#Endpoints to TMF 369  Method ['GET']
# http://localhost:5000/C3P/api/Resource/v4/521?field=activationFeature&category=Security
# http://localhost:5000/C3P/api/Resource/v4/521?field=activationFeature
# http://localhost:5000/C3P/api/Resource/v4/521
# http://localhost:5000/C3P/api/Resource/v4/

def listResource(id,args) :       
    global data
    mydb = Connections.create_connection()
    logger.debug("tmf::c3p_tmf_get_api::listResource::ID: %s", id)
    fieldsData = []   
    filterQuery ="" 
    data = {}
    rfdata = [] 
    try:
        mycursor = mydb.cursor(buffered=True)
        if(len(args) != 0):
            field = args["field"]        
            fieldsData = list(field.split(","))
            logger.debug("tmf::c3p_tmf_get_api::listResource::field: %s", fieldsData)
            filterQuery = setFilterResource(args)
        params = []
        if not id:
            resourceSql = "SELECT d_hostname,r_device_id ,r_category,r_adminState,r_description,r_href,r_opertionalState,r_resourceStatus,r_resourceVersion,r_endOperatingDate,r_startOperatingDate,r_usageState,r_basetype,r_schemalocation,r_type FROM c3p_deviceinfo,c3p_deviceinfo_ext WHERE c3p_deviceinfo_ext.r_device_id IN (SELECT d_id FROM c3p_deviceinfo) AND (c3p_deviceinfo_ext.r_device_id = c3p_deviceinfo.d_id) "
        else:
            resourceSql = "SELECT d_hostname,r_device_id ,r_category,r_adminState,r_description,r_href,r_opertionalState,r_resourceStatus,r_resourceVersion,r_endOperatingDate,r_startOperatingDate,r_usageState,r_basetype,r_schemalocation,r_type FROM c3p_deviceinfo,c3p_deviceinfo_ext WHERE c3p_deviceinfo_ext.r_device_id =%s and c3p_deviceinfo.d_id =%s"
            params.append(id)
            params.append(id)
        
        if filterQuery:
            resourceSql += " AND %s"
            params.append(filterQuery)

        mycursor.execute(resourceSql, params)
        resourceResult = mycursor.fetchall()    
        for rf_result in resourceResult :
            temp_data = {}        
            temp_data["administrativeState"] =rf_result[3]
            temp_data["category"] =rf_result[2]
            temp_data["description"] =rf_result[4]
            temp_data["endOperatingDate"] =rf_result[9]
            temp_data["href"] =rf_result[5]
            temp_data["id"] =rf_result[1]
            temp_data["name"] =rf_result[0]
            temp_data["operationalState"] =rf_result[6]
            temp_data["resourceStatus"] =rf_result[7]
            temp_data["resourceVersion"] =rf_result[8]
            temp_data["startOperatingDate"] =rf_result[10]
            temp_data["usageState"] =rf_result[11]
            temp_data["@baseType"] =rf_result[12]
            temp_data["@schemaLocation"] =rf_result[13]
            temp_data["@type"] =rf_result[14]
            if(len(fieldsData)!=0):
                for fields in fieldsData:                     
                    if("activationFeature"== fields):
                        logger.debug("tmf::c3p_tmf_get_api::listResource:: in activationFeature: ")
                        temp_data["activationFeature"] = setFeatures(rf_result[1])
                    if("place"== fields):
                        temp_data["place"] = setPlace(rf_result[1])
                    if("relatedParty"== fields):
                        temp_data["relatedParty"] = setRelatedParty(rf_result[1])    
            else:        
                temp_data["activationFeature"] = setFeatures(rf_result[1])
                temp_data["place"] = setPlace(rf_result[1])
                temp_data["relatedParty"] = setRelatedParty(rf_result[1])
            rfdata.append(temp_data)
    except Exception as err:
        logger.error("tmf::c3p_tmf_get_api::listResource: %s",err)
    finally:
        mydb.close    
    # logger.debug("tmf::c3p_tmf_get_api::listResource::resourceData: %s", rfdata)
    return jsonify(rfdata),status.HTTP_200_OK

def setFilterResource(args):    
    filterQuery = ""
    count = 0
    logger.debug("tmf::c3p_tmf_get_api::setFilterResource::filterArgs: %s", args)
    try:
        for i in args:          
            if(count>0 and filterQuery!=""):
                filterQuery = filterQuery+" and "
            if("administrativeState"== i):
                filterQuery = filterQuery +"r_adminState = '"+args[i]+"'"
            if("category"== i):
                filterQuery = filterQuery +"r_category = '"+args[i]+"'"
            if("description"== i):
                filterQuery = filterQuery +"r_description = '"+args[i]+"'"
            if("endOperatingDate"== i):
                filterQuery = filterQuery +"r_endOperatingDate = '"+args[i]+"'"
            if("href"== i):
                filterQuery = filterQuery +"r_href = '"+args[i]+"'"
            if("id"== i):
                filterQuery = filterQuery +"r_device_id = '"+args[i]+"'"
            if("name"== i):
                filterQuery = filterQuery +"d_hostname = '"+args[i]+"'"
            if("operationalState"== i):
                filterQuery = filterQuery +"r_opertionalState = '"+args[i]+"'"
            if("resourceStatus"== i):
                filterQuery = filterQuery +"r_resourceStatus = '"+args[i]+"'"
            if("resourceVersion"== i):
                filterQuery = filterQuery +"r_resourceVersion = '"+args[i]+"'"
            if("startOperatingDate"== i):
                filterQuery = filterQuery +"r_startOperatingDate = '"+args[i]+"'"
            if("usageState"== i):
                filterQuery = filterQuery +"r_usageState = '"+args[i]+"'"
            count = count + 1
    except Exception as err:
        logger.error("tmf::c3p_tmf_get_api::setFilterResource: %s",err)     
    logger.debug("tmf::c3p_tmf_get_api::setFilterResource::filterQuery: %s", filterQuery)
    return filterQuery     

def setFeatures(dId):
    fdata = []
    mydb = Connections.create_connection()
    logger.debug("tmf::c3p_tmf_get_api::setFeatures::DeviceID: %s", dId)
    try:
        mycursor = mydb.cursor(buffered=True)
        featureSql = "select distinct(rc_feature_id),f_id, f_isbundled, f_isenabled,f_name,f_basetype,f_schemalocation,f_type from c3p_resourcecharacteristics, c3p_m_features where f_id = rc_feature_id and device_id = %s" 
        mycursor.execute(featureSql, (dId,))
        featureResult = mycursor.fetchall()
        for f_result in featureResult :
            temp_data = {}
            temp_data["id"] =f_result[1]
            temp_data["isBundled"] =f_result[2]
            temp_data["isEnabled"] =f_result[3]
            temp_data["name"] =f_result[4]
            temp_data["@baseType"] =f_result[5]
            temp_data["@schemaLocation"] =f_result[6]
            temp_data["@type"] =f_result[7]
            temp_data["featureCharacteristic"] = setresourceCharacteristic(f_result[0])
            fdata.append(temp_data)
    except Exception as err:
        logger.error("tmf::c3p_tmf_get_api::setFeatures: %s",err)     
    finally:
        mydb.close    
    # logger.debug("tmf::c3p_tmf_get_api::setFeatures::featureData: %s", fdata)
    return fdata

def setresourceCharacteristic(fId):
    resourceData = []
    mydb = Connections.create_connection()
    logger.debug("tmf::c3p_tmf_get_api::setresourceCharacteristic::featureID: %s", fId)
    try:
        mycursor = mydb.cursor(buffered=True)
        resourcesql = "select rc_characteristic_id,rc_characteristic_name,rc_characteristic_value,rc_valuetype,rc_basetype,rc_schemalocation,rc_type from c3p_resourcecharacteristics where  rc_feature_id = %s" 
        mycursor.execute(resourcesql, (fId,))
        resourceResult = mycursor.fetchall()
        for resource in resourceResult :
            temp_data = {}       
            temp_data["id"] =resource[0]
            temp_data["name"] =resource[1]
            temp_data["value"] =resource[2]
            temp_data["valueType"] =resource[3]
            temp_data["@baseType"] =resource[4]        
            temp_data["@schemaLocation"] =resource[5]
            temp_data["@type"] =resource[6]        
            resourceData.append(temp_data)
    except Exception as err:
        logger.error("tmf::c3p_tmf_get_api::setresourceCharacteristic: %s",err)     
    finally:
        mydb.close
    # logger.debug("tmf::c3p_tmf_get_api::setresourceCharacteristic::resourceCharacteristicData %s", resourceData)    
    return resourceData

def setPlace(id):
    resourceData = []
    mydb = Connections.create_connection()
    logger.debug("tmf::c3p_tmf_get_api::setPlace::Id: %s", id)
    try:
        mycursor = mydb.cursor(buffered=True)
        cId = "SELECT c_site_id FROM c3p_deviceinfo WHERE c3p_deviceinfo.d_id =%s"  
        mycursor.execute(cId, (id,))
        Id = mycursor.fetchone()
        resourceResult = "SELECT id,c_site_name FROM c3p_cust_siteinfo WHERE c3p_cust_siteinfo.id =%s" 
        mycursor.execute(resourceResult, (Id[0],))
        resourceResult = mycursor.fetchall() 
        for resource in resourceResult :
            temp_data = {}       
            temp_data["id"] =resource[0]
            temp_data["name"] =resource[1]
            temp_data["role"] ="servingsite"    
            resourceData.append(temp_data)
    except Exception as err:
        logger.error("tmf::c3p_tmf_get_api::setPlace: %s",err)     
    finally:
        mydb.close
    return resourceData

def setRelatedParty(id):
    resourceData = []
    mydb = Connections.create_connection()
    logger.debug("tmf::c3p_tmf_get_api::setRelatedParty::Id: %s", id)
    try:
        mycursor = mydb.cursor(buffered=True)
        cId = "SELECT c_site_id FROM c3p_deviceinfo WHERE c3p_deviceinfo.d_id =%s"  
        mycursor.execute(cId, (id,))
        Id = mycursor.fetchone()
        resourceResult = "SELECT c_cust_id,c_cust_name FROM c3p_cust_siteinfo WHERE c3p_cust_siteinfo.id =%s" 
        mycursor.execute(resourceResult, (Id[0],))
        resourceResult = mycursor.fetchall() 
        for resource in resourceResult :
            temp_data = {}       
            temp_data["id"] =resource[0]
            temp_data["name"] =resource[1]
            temp_data["role"] ="customer"    
            resourceData.append(temp_data)
    except Exception as err:
        logger.error("tmf::c3p_tmf_get_api::setRelatedParty: %s",err)     
    finally:
        mydb.close
    return resourceData