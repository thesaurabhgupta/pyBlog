from flask import jsonify
from flask_api import status
import logging
from c3papplication.common import Connections

logger = logging.getLogger(__name__)

# Endpoints to TMF 634  Method ['GET']
# http://localhost:5000/c3p-p-core/api/ResourceSpec/v41/
# http://localhost:5000/c3p-p-core/api/ResourceSpec/v41/RS1001

def listResourceSpec(id, args):
    data = {}
    mydb = Connections.create_connection(Connections.config_rescat)
    fieldsData = []
    filterQuery = ""
    rsdata = []
    try:
        mycursor = mydb.cursor(buffered=True)
        if args:
            field = args.get("field", "")
            fieldsData = field.split(",")
            logger.debug("tmf::c3p_tmf_res_spec_get_api::listResourceSpec::field: %s", fieldsData)
            filterQuery = setFilterResource(args)
        resourceSql = "SELECT rs_rowid, rs_href, rs_name, rs_description, rs_type, rs_basetype, rs_schemalocation, rs_version, " \
                    "rs_isBundle, rs_lastUpdate, rs_lifeCycleStatus, rs_Category, rs_prs_id, rs_created_by, rs_created_date, " \
                    "rs_updated_by, rs_updated_date, rs_lrs_id, B.rtp_StartDateTime, B.rtp_endDateTime, rs_id " \
                    "FROM c3p_resource_specification A " \
                    "INNER JOIN c3p_timeperiod B ON A.rs_validfor = B.rtp_id"
        params = []
        if id:
            resourceSql += f" HAVING rs_id = %s"
            params.append(id)
        if filterQuery:
            resourceSql += f" AND %s"
            params.append(filterQuery)
        mycursor.execute(resourceSql, params)
        resourceResult = mycursor.fetchall()
        for rs_result in resourceResult:
            data = {}
            if rs_result[4] == 'physicalresourcespecification':
                vendor = getPhysicalResourceVendor(rs_result[12])
            else:
                vendor = getLogicalResourceVendor(rs_result[17])
            data = {
                "id": rs_result[20],
                "href": rs_result[1],
                "name": rs_result[2],
                "isCatalogItem": 1,
                "description": rs_result[3],
                "type": rs_result[4],
                "@type": rs_result[4],
                "vendor": vendor,
                "@baseType": rs_result[5],
                "@schemaLocation": rs_result[6],
                "version": rs_result[7],
                "isBundle": rs_result[8],
                "lastUpdate": rs_result[9],
                "lifecycleStatus": rs_result[10],
                "category": rs_result[11],
                "createdBy": rs_result[13],
                "createdDate": rs_result[14],
                "updatedBy": rs_result[15],
                "updatedDate": rs_result[16],
                "lrsId": rs_result[17],
                "validFor": {
                    "StartDateTime": rs_result[18],
                    "EndDateTime": rs_result[19]
                },
                "targetResourceSchema": {
                    "type": rs_result[4],
                    "@type": rs_result[4],
                    "@schemaLocation": rs_result[6]
                },
                "attachment": getAttachments(rs_result[20]),
                "attachmentRef": getAttachmentRef(rs_result[20]),
                "relatedParty": getRelatedParty(rs_result[20]),
                "resourceSpecCharacteristic": getResourceSpecCharacteristics(rs_result[20]),
                "resourceSpecRelationship": getResourceSpecRelationship(rs_result[20]),
            }
            rsdata.append(data)
    except Exception as err:
        logger.error("tmf::c3p_tmf_res_spec_get_apiv2::listResourceSpec: %s", err)
    finally:
        mydb.close()
    if not id:
        return jsonify(rsdata),status.HTTP_200_OK
    else:
        return jsonify(rsdata[0]),status.HTTP_200_OK


def getPhysicalResourceVendor(rs_id):
    mydb = Connections.create_connection(Connections.config_rescat)
    vendor_name = ""
    try:
        mycursor = mydb.cursor(buffered=True)
        resourceSql = "SELECT prs_vendor FROM c3p_physicalresourcespecification WHERE prs_id = %s"
        mycursor.execute(resourceSql, [rs_id])
        resourceResult = mycursor.fetchall()
        if resourceResult:
            vendor_name = resourceResult[0][0]
    except Exception as err:
        logger.error("tmf::c3p_tmf_res_spec_get_apiv2::getPhysicalResourceVendor: %s", err)
    finally:
        mydb.close()
    return vendor_name


def getLogicalResourceVendor(rs_id):
    mydb = Connections.create_connection(Connections.config_rescat)
    vendor_name = ""
    try:
        mycursor = mydb.cursor(buffered=True)
        resourceSql = "SELECT v_vendor FROM c3p_logicalresourcespecification WHERE rs_lrs_id = %s"
        mycursor.execute(resourceSql, [rs_id])
        resourceResult = mycursor.fetchall()
        if resourceResult:
            vendor_name = resourceResult[0][0]
    except Exception as err:
        logger.error("tmf::c3p_tmf_res_spec_get_apiv2::getLogicalResourceVendor: %s", err)
    finally:
        mydb.close()
    return vendor_name


def getAttachments(id):
    mydb = Connections.create_connection(Connections.config_rescat)
    attachment_data = []
    try:
        mycursor = mydb.cursor(buffered=True)
        resourceSql = (
            "SELECT rsa_id, rsa_href, rsa_name, rsa_mimeType, rsa_url, rsa_description, "
            "rsa_created_date, rsa_updated_date, rsa_attachmentType, rsa_content, "
            "rsa_size, rsa_validFor, rsa_baseType, rsa_schemaLocation, rsa_type, "
            "rsa_created_by, rsa_updated_by "
            "FROM c3p_resource_specification_attachment WHERE rs_id = %s"
        )
        mycursor.execute(resourceSql, [id])
        resourceResult = mycursor.fetchall()
        for rs_result in resourceResult:
            data = {
                "id": rs_result[0],
                "href": rs_result[1],
                "name": rs_result[2],
                "mimeType": rs_result[3],
                "url": rs_result[4],
                "description": rs_result[5],
                "createdDate": rs_result[6],
                "updatedDate": rs_result[7],
                "attachmentType": rs_result[8],
                "content": rs_result[9],
                "size": rs_result[10],
                "validFor": rs_result[11],
                "@baseType": rs_result[12],
                "@schemaLocation": rs_result[13],
                "type": rs_result[14],
                "@type": rs_result[14],
                "createdBy": rs_result[15],
                "updatedBy": rs_result[16],
            }
            attachment_data.append(data)
    except Exception as err:
        logger.error("tmf::c3p_tmf_res_spec_get_apiv2::getAttachments: %s", err)
    finally:
        mydb.close()
    return attachment_data


def getAttachmentRef(id):
    mydb = Connections.create_connection(Connections.config_rescat)
    attachment_data = []
    try:
        mycursor = mydb.cursor(buffered=True)
        resourceSql = (
            "SELECT rsar_id, rsar_href, rsar_name, rsar_url, rsar_description, "
            "rsar_baseType, rsar_referredType, rsar_schemaLocation, rsar_type, "
            "rsar_created_by, rsar_creted_date, rsar_updated_date, rsar_updated_by "
            "FROM c3p_resource_specification_attachmentref WHERE rs_id = %s"
        )
        mycursor.execute(resourceSql, [id])
        resourceResult = mycursor.fetchall()
        for rs_result in resourceResult:
            data = {
                "id": rs_result[0],
                "href": rs_result[1],
                "name": rs_result[2],
                "url": rs_result[3],
                "description": rs_result[4],
                "@baseType": rs_result[5],
                "referredType": rs_result[6],
                "@schemaLocation": rs_result[7],
                "type": rs_result[8],
                "@type": rs_result[8],
                "createdBy": rs_result[9],
                "createdDate": rs_result[10],
                "updatedDate": rs_result[11],
                "updatedBy": rs_result[12],
            }
            attachment_data.append(data)
    except Exception as err:
        logger.error("tmf::c3p_tmf_res_spec_get_apiv2::getAttachmentRef: %s", err)
    finally:
        mydb.close()
    return attachment_data


def getRelatedParty(id):
    mydb = Connections.create_connection(Connections.config_rescat)
    relatedparty_data = []
    try:
        mycursor = mydb.cursor(buffered=True)
        resourceSql = (
            "SELECT rsrp_id, rsrp_href, rsrp_role, rsrp_name, rsrp_referredType, "
            "rc_id, rcg_id, rsrp_baseType, rsrp_schemaLocation, rsrp_type, "
            "rsrp_created_by, rsrp_created_date, rsrp_updated_by, rsrp_updated_date "
            "FROM c3p_resource_specification_relatedparty "
            "WHERE rs_id = %s"
        )
        mycursor.execute(resourceSql, [id])
        resourceResult = mycursor.fetchall()
        for rs_result in resourceResult:
            data = {
                "id": rs_result[0],
                "href": rs_result[1],
                "role": rs_result[2],
                "name": rs_result[3],
                "referredType": rs_result[4],
                "@baseType": rs_result[7],
                "@schemaLocation": rs_result[8],
                "type": rs_result[9],
                "@type": rs_result[9],
                "createdBy": rs_result[10],
                "createdDate": rs_result[11],
                "updatedBy": rs_result[12],
                "updatedDate": rs_result[13],
            }
            relatedparty_data.append(data)
    except Exception as err:
        logger.error("tmf::c3p_tmf_res_spec_get_apiv2::getRelatedParty: %s", err)
    finally:
        mydb.close()
    return relatedparty_data


def getResourceSpecCharacteristics(id):
    mydb = Connections.create_connection(Connections.config_rescat)
    characteristics_data = []
    try:
        mycursor = mydb.cursor(buffered=True)
        resourceSql = (
            "SELECT rsc_name, rsc_description, rsc_valueType, rsc_configurable, "
            "rsc_minCardinality, rsc_maxCardinality, rsc_isUnique, rsc_rsr_id, "
            "rsc_extensible, rsc_regex, rsc_validFor, rsc_baseType, rsc_schemaLocation, "
            "rsc_type, rsc_valueSchemaLocation, rsc_created_by, rsc_created_date, "
            "rsc_updated_by, rsc_updated_date, rsc_id "
            "FROM c3p_resource_specification_characteristics "
            "WHERE rs_id = %s"
        )
        mycursor.execute(resourceSql, [id])
        resourceResult = mycursor.fetchall()
        for rs_result in resourceResult:
            data = {
                "name": rs_result[0],
                "description": rs_result[1],
                "valueType": rs_result[2],
                "configurable": rs_result[3],
                "maxCardinality": rs_result[4],
                "minCardinality": rs_result[5],
                "isUnique": rs_result[6],
                "extensible": rs_result[8],
                "regex": rs_result[9],
                "validFor": rs_result[10],
                "@baseType": rs_result[11],
                "@schemaLocation": rs_result[12],
                "type": rs_result[13],
                "@type": rs_result[13],
                "valueSchemaLocation": rs_result[14],
                "createdBy": rs_result[15],
                "createdDate": rs_result[16],
                "updatedBy": rs_result[17],
                "updatedDate": rs_result[18],
                "resourceSpecCharacteristicValue": getResourceSpecCharacteristicsValue(rs_result[19]),
                "resourceSpecCharacteristicRelationship": getResourceSpecCharacteristicsRelationship(rs_result[19])
            }
            characteristics_data.append(data)
    except Exception as err:
        logger.error("tmf::c3p_tmf_res_spec_get_apiv2::getResourceSpecChar: %s", err)
    finally:
        mydb.close()
    return characteristics_data


def getResourceSpecCharfromRelationship(id):
    mydb = Connections.create_connection(Connections.config_rescat)
    characteristics_data = []
    try:
        mycursor = mydb.cursor(buffered=True)
        resourceSql = (
            "SELECT rsc_name, rsc_description, rsc_valueType, rsc_configurable, "
            "rsc_minCardinality, rsc_maxCardinality, rsc_isUnique, rsc_extensible, "
            "rsc_regex, rsc_validFor, rsc_baseType, rsc_schemaLocation, rsc_type, "
            "rsc_valueSchemaLocation, rsc_created_by, rsc_created_date, rsc_updated_by, "
            "rsc_updated_date, rsc_id "
            "FROM c3p_resource_specification_characteristics "
            "WHERE rsc_rsr_id = %s"
        )
        mycursor.execute(resourceSql, [id])
        resourceResult = mycursor.fetchall()
        for rs_result in resourceResult:
            data = {
                "name": rs_result[0],
                "description": rs_result[1],
                "valueType": rs_result[2],
                "configurable": rs_result[3],
                "maxCardinality": rs_result[4],
                "minCardinality": rs_result[5],
                "isUnique": rs_result[6],
                "extensible": rs_result[7],
                "regex": rs_result[8],
                "validFor": rs_result[9],
                "@baseType": rs_result[10],
                "@schemaLocation": rs_result[11],
                "type": rs_result[12],
                "@type": rs_result[12],
                "valueSchemaLocation": rs_result[13],
                "createdBy": rs_result[14],
                "createdDate": rs_result[15],
                "updatedBy": rs_result[16],
                "updatedDate": rs_result[17],
                "resourceSpecCharacteristicValue": getResourceSpecCharacteristicsValue(rs_result[18]),
                "resourceSpecCharacteristicRelationship": getResourceSpecCharacteristicsRelationship(rs_result[18])
            }
            characteristics_data.append(data)
    except Exception as err:
        logger.error("tmf::c3p_tmf_res_spec_get_apiv2::getResourceSpecChar: %s", err)
    finally:
        mydb.close()
    return characteristics_data


def getResourceSpecCharacteristicsValue(id):
    mydb = Connections.create_connection(Connections.config_rescat)
    characteristics_value_data = []
    try:
        mycursor = mydb.cursor(buffered=True)
        resourceSql = (
            "SELECT rscv_value, rscv_valueType, rscv_isDefault, rscv_rangeInterval, "
            "rscv_regex, rscv_unitOfmeasure, rscv_validFor, rscv_valueFrom, rscv_valueTo, "
            "rscv_baseType, rscv_schemaLocation, rscv_type, rscv_created_by, rscv_created_date, "
            "rscv_updated_by, rscv_updated_date "
            "FROM c3p_resource_specification_characteristic_value "
            "WHERE rsc_id = %s"
        )
        mycursor.execute(resourceSql, [id])
        resourceResult = mycursor.fetchall()
        for rs_result in resourceResult:
            data = {
                "value": rs_result[0],
                "valueType": rs_result[1],
                "isDefault": rs_result[2],
                "rangeInterval": rs_result[3],
                "regex": rs_result[4],
                "unitOfmeasure": rs_result[5],
                "validFor": rs_result[6],
                "valueFrom": rs_result[7],
                "valueTo": rs_result[8],
                "@baseType": rs_result[9],
                "@schemaLocation": rs_result[10],
                "type": rs_result[11],
                "@type": rs_result[11],
                "createdBy": rs_result[12],
                "createdDate": rs_result[13],
                "updatedBy": rs_result[14],
                "updatedDate": rs_result[15]
            }
            characteristics_value_data.append(data)
    except Exception as err:
        logger.error("tmf::c3p_tmf_res_spec_get_apiv2::getResourceSpecCharValue: %s", err)
    finally:
        mydb.close()
    return characteristics_value_data


def getResourceSpecCharacteristicsRelationship(id):
    mydb = Connections.create_connection(Connections.config_rescat)
    characteristics_value_data = []
    try:
        mycursor = mydb.cursor(buffered=True)
        resourceSql = (
            "SELECT rscr_name, rscr_relationshipType, rscr_resourceSpecificationHref, "
            "rscr_resourceSpecificationId, rscr_validFor, rscr_schemaLocation, rscr_type, "
            "rscr_basetype, rscr_created_by, rscr_created_date, rscr_updated_by, rscr_updated_date "
            "FROM c3p_resource_specchar_relationship "
            "WHERE rscr_characteristicSpecificationId = %s"
        )
        mycursor.execute(resourceSql, [id])
        resourceResult = mycursor.fetchall()
        for rs_result in resourceResult:
            data = {
                "name": rs_result[0],
                "relationshipType": rs_result[1],
                "resourceSpecificationHref": rs_result[2],
                "resourceSpecificationId": rs_result[3],
                "validFor": rs_result[4],
                "@schemaLocation": rs_result[5],
                "@baseType": rs_result[7],
                "type": rs_result[6],
                "@type": rs_result[6],
                "createdBy": rs_result[8],
                "createdDate": rs_result[9],
                "updatedBy": rs_result[10],
                "updatedDate": rs_result[11]
            }
            characteristics_value_data.append(data)
    except Exception as err:
        logger.error("tmf::c3p_tmf_res_spec_get_apiv2::getResourceSpecCharRelationship: %s", err)
    finally:
        mydb.close()
    return characteristics_value_data


def getResourceSpecRelationship(id):
    mydb = Connections.create_connection(Connections.config_rescat)
    relationship_data = []
    try:
        mycursor = mydb.cursor(buffered=True)
        resourceSql = (
            "SELECT rsr_id, rsr_href, rsr_name, rsr_relationshipType, "
            "rsr_defaultQuantity, rsr_maximumQuantity, rsr_minimumQuantity, "
            "rsr_role, rsr_validFor, rsr_baseType, rsr_schemaLocation, "
            "rsr_type, rsr_created_by, rsr_created_date, rsr_updated_date, "
            "rsr_updated_by "
            "FROM c3p_resource_specification_relationship "
            "WHERE rs_id = %s"
        )
        mycursor.execute(resourceSql, [id])
        resourceResult = mycursor.fetchall()
        for rs_result in resourceResult:
            data = {
                "id": rs_result[0],
                "href": rs_result[1],
                "name": rs_result[2],
                "relationshipType": rs_result[3],
                # "sourceRsId": rs_result[4],  # Commented out as it is not used
                "defaultQuantity": rs_result[4],
                "maximumQuantity": rs_result[5],
                "minimumQuantity": rs_result[6],
                "role": rs_result[7],
                "validFor": rs_result[8],
                "@baseType": rs_result[9],
                "@schemaLocation": rs_result[10],
                "type": rs_result[11],
                "@type": rs_result[12],
                "createdBy": rs_result[12],
                "createdDate": rs_result[13],
                "updatedDate": rs_result[14],
                "updatedBy": rs_result[15],
                "resourceSpecCharacteristic": getResourceSpecCharfromRelationship(rs_result[0])
            }
            relationship_data.append(data)
    except Exception as err:
        logger.error("tmf::c3p_tmf_res_spec_get_apiv2::getResourceSpecRelationship: %s", err)
    finally:
        mydb.close()
    return relationship_data


def setFilterResource(args):
    args = {k: v[0] for k, v in dict(args).items()}
    logger.debug("tmf::c3p_tmf_res_spec_get_apiv2::setFilterResource::filterArgs: %s", args)
    filterQuery = ""
    try:
        field_map = {
            "name": "rs_name",
            "category": "rs_category",
            "description": "rs_description",
            "href": "rs_href",
            "type": "rs_type",
            "basetype": "rs_basetype",
            "resourceVersion": "rs_version",
            "lifeCycleStatus": "rs_lifecycleStatus"
        }
        filters = [f"{field_map[k]} = '{v}'" for k, v in args.items() if k in field_map.keys()]
        filterQuery += " AND ".join(filters)
        logger.debug("tmf::c3p_tmf_res_spec_get_apiv2::setFilterResource::filterQuery: %s", filterQuery)
    except Exception as err:
        logger.error("tmf::c3p_tmf_res_spec_get_apiv2::setFilterResource: %s",err)
    return filterQuery


# Endpoints to TMF 634  Method ['GET']
# http://localhost:5000/c3p-p-core/api/PhysicalResourceSpec/v41/
# http://localhost:5000/c3p-p-core/api/PhysicalResourceSpec/v41/RS1001

def listPhysicalResourceSpec(id, args):
    mydb = Connections.create_connection(Connections.config_rescat)
    fieldsData = []
    filterQuery = ""
    try:
        rspdata = []
        mycursor = mydb.cursor(buffered=True)
        if args:
            field = args.get("field", "")
            fieldsData = list(field.split(","))
            logger.debug("tmf::c3p_tmf_res_spec_get_apiv2::listPhysicalResourceSpec::field: %s", fieldsData)
            filterQuery = setFilterResource(args)
        resourceSql = "SELECT DISTINCT prs_id, prs_model, prs_part, prs_sku, prs_vendor, rs_href, rs_name, " \
                    "rs_description, rs_type, rs_basetype, rs_schemalocation, rs_version, " \
                    "rs_isBundle, rs_lastUpdate, rs_lifeCycleStatus, rs_Category, " \
                    "B.rtp_StartDateTime, B.rtp_endDateTime, rs_id " \
                    "FROM c3p_physicalresourcespecification AS P " \
                    "LEFT JOIN c3p_resource_specification A ON P.prs_id = A.rs_prs_id " \
                    "INNER JOIN c3p_timeperiod B ON A.rs_validfor = B.rtp_id"
        params = []
        if id:
            resourceSql += f" HAVING rs_id = %s"
            params.append(id)
        if filterQuery:
            resourceSql += f" AND %s"
            params.append(filterQuery)
        mycursor.execute(resourceSql, params)
        resourceResult = mycursor.fetchall()
        for rs_result in resourceResult:
            data = {
                "id": rs_result[0],
                "model": rs_result[1],
                "part": rs_result[2],
                "sku": rs_result[3],
                "vendor": rs_result[4],
                "href": rs_result[5],
                "name": rs_result[6],
                "description": rs_result[7],
                "type": rs_result[8],
                "@type": rs_result[8],
                "@baseType": rs_result[9],
                "@schemaLocation": rs_result[10],
                "version": rs_result[11],
                "isBundle": rs_result[12],
                "lastUpdate": rs_result[13],
                "lifecycleStatus": rs_result[14],
                "category": rs_result[15],
                "validFor": {
                    "StartDateTime": rs_result[16],
                    "EndDateTime": rs_result[17]
                },
                "targetResourceSchema": {
                    "type": rs_result[8],
                    "@type": rs_result[8],
                    "@schemaLocation": rs_result[10]
                },
                "attachment": getAttachments(rs_result[18]),
                "attachmentRef": getAttachmentRef(rs_result[18]),
                "relatedParty": getRelatedParty(rs_result[18]),
                "resourceSpecCharacteristic": getResourceSpecCharacteristics(rs_result[18]),
                "resourceSpecRelationship": getResourceSpecRelationship(rs_result[18])
            }
            rspdata.append(data)
    except Exception as err:
        logger.error("tmf::c3p_tmf_res_spec_get_apiv2::listPhysicalResourceSpec: %s", err)
    finally:
        mydb.close()
    if not id:
        return jsonify(rspdata), status.HTTP_200_OK
    else:
        return jsonify(rspdata[0]), status.HTTP_200_OK


# Endpoints to TMF 634  Method ['GET']
# http://localhost:5000/c3p-p-core/api/LogicalResourceSpec/v41/
# http://localhost:5000/c3p-p-core/api/LogicalResourceSpec/v41/RS1003

def listLogicalResourceSpec(id, args):
    mydb = Connections.create_connection(Connections.config_rescat)
    logger.info(dict(args))
    lrs_data = []
    try:
        resourceSql = ""
        mycursor = mydb.cursor(buffered=True)
        fieldsData = args.get("field", "").split(",")
        logger.debug("tmf::c3p_tmf_res_spec_get_apiv2::listLogicalResourceSpec::field: %s", fieldsData)
        filterQuery = setFilterResource(args) if args else ""
        resourceSql = "SELECT DISTINCT v_imagename, v_disktype, v_disksize_gb, v_vendor, v_family, v_os, v_osversion, v_model, v_devicetype, v_status, v_image_ref, P.rs_lrs_id, rs_rowid, rs_href, rs_name, rs_description, rs_type, rs_basetype, rs_schemalocation, " \
                    "rs_version, rs_isBundle, rs_lastUpdate, rs_lifeCycleStatus, rs_Category, B.rtp_StartDateTime, B.rtp_endDateTime, " \
                    "rs_id FROM c3p_logicalresourcespecification AS P LEFT JOIN c3p_resource_specification A ON P.rs_lrs_id = A.rs_lrs_id INNER JOIN c3p_timeperiod B ON A.rs_validfor = B.rtp_id"
        params = []
        if id:
            resourceSql += f" HAVING rs_id = %s"
            params.append(id)
        if filterQuery:
            resourceSql += f" AND %s"
            params.append(filterQuery)
        mycursor.execute(resourceSql, params)
        resourceResult = mycursor.fetchall()
        for rs_result in resourceResult:
            data = {
                "imageName": rs_result[0],
                "diskType": rs_result[1],
                "diskSize": rs_result[2],
                "vendor": rs_result[3],
                "family": rs_result[4],
                "os": rs_result[5],
                "osVersion": rs_result[6],
                "model": rs_result[7],
                "deviceType": rs_result[8],
                "status": rs_result[9],
                "imageRef": rs_result[10],
                "lrsId": rs_result[11],
                "id": rs_result[12],
                "href": rs_result[13],
                "name": rs_result[14],
                "description": rs_result[15],
                "type": rs_result[16],
                "@type": rs_result[16],
                "@baseType": rs_result[17],
                "@schemaLocation": rs_result[18],
                "version": rs_result[19],
                "isBundle": rs_result[20],
                "lastUpdate": rs_result[21],
                "lifecycleStatus": rs_result[22],
                "category": rs_result[23],
                "validFor": {
                    "StartDateTime": rs_result[24],
                    "EndDateTime": rs_result[25],
                },
                "targetResourceSchema": {
                    "type": rs_result[16],
                    "@type": rs_result[16],
                    "@schemaLocation": rs_result[18],
                },
                "attachment": getAttachments(rs_result[26]),
                "attachmentRef": getAttachmentRef(rs_result[26]),
                "relatedParty": getRelatedParty(rs_result[26]),
                "resourceSpecCharacteristic": getResourceSpecCharacteristics(rs_result[26]),
                "resourceSpecRelationship": getResourceSpecRelationship(rs_result[26]),
            }
            lrs_data.append(data)
    except Exception as err:
        logger.error("tmf::c3p_tmf_res_spec_get_apiv2::listLogicalResourceSpec: %s", err)
    finally:
        mydb.close()
    if not id:
        return jsonify(lrs_data), status.HTTP_200_OK
    else:
        return jsonify(lrs_data[0]), status.HTTP_200_OK

# Endpoints to TMF 634  Method ['GET']
# http://localhost:5000/c3p-p-core/api/ResourceSpecRelationship/v41/
# http://localhost:5000/c3p-p-core/api/ResourceSpecRelationship/v41/RS1001


def listResourceSpecRelationship(id):
    data = {}
    mydb = Connections.create_connection(Connections.config_rescat) 
    try:
        resourceSql = ""
        rsdata = []
        mycursor = mydb.cursor(buffered=True)
        resourceSql = "SELECT B.rs_id, A.rsr_source_rs_id, rs_name, rs_category, rs_lifecycleStatus, rs_version, rs_description, " \
                    "rs_type, B.rs_prs_id, B.rs_lrs_id, rsr_relationshipType " \
                    "FROM c3p_resource_specification B LEFT JOIN c3p_resource_specification_relationship A " \
                    "ON A.rsr_source_rs_id = B.rs_id"
        params = []
        if id:
            resourceSql += " WHERE B.rs_id = %s"
            params.append(id)
        mycursor.execute(resourceSql, params)
        resourceResult = mycursor.fetchall()
        resource_id = 1
        for rs_result in resourceResult:
            if rs_result[7] == 'physicalresourcespecification':
                vendor, part = getPhysicalResourcedetails(rs_result[8])
            else:
                vendor, part = getLogicalResourcedetails(rs_result[9])
            data = {
                'id': resource_id,
                'parent_id': resource_id - 1 if rs_result[1] else 0,
                'name': rs_result[2],
                'details': {
                    'summary': {
                        'category': rs_result[3],
                        'status': rs_result[4],
                        'version': rs_result[5],
                        'vendor': vendor,
                        'part': part
                    },
                    'desc': rs_result[6]
                }
            }
            rsdata.append(data)
            resource_id += 1
            data = {
                'id': resource_id,
                'parent_id': resource_id - 1,
                'name': rs_result[10],
                'details': {}
            }
            rsdata.append(data)
            resource_id += 1
        rs_spec_data = {'resourceSpecRelationship': rsdata}
    except Exception as err:
        logger.error("tmf::c3p_tmf_res_spec_get_apiv2::listResourceSpecRelationship: %s", err)
    finally:
        mydb.close()
    return jsonify(rs_spec_data), status.HTTP_200_OK


def getPhysicalResourcedetails(rs_id):
    mydb = Connections.create_connection(Connections.config_rescat)
    vendor_name, vendor_part = "", ""
    try:
        mycursor = mydb.cursor(buffered=True)
        resourceSql = "SELECT prs_vendor, prs_part FROM c3p_physicalresourcespecification WHERE prs_id = %s"
        mycursor.execute(resourceSql, [rs_id])
        resourceResult = mycursor.fetchall()
        if resourceResult:
            vendor_name, vendor_part = resourceResult[0]
    except Exception as err:
        logger.error("tmf::c3p_tmf_res_spec_get_apiv2::getPhysicalResourceSpec: %s", err)
    finally:
        mydb.close()
    return vendor_name, vendor_part


def getLogicalResourcedetails(rs_id):
    mydb = Connections.create_connection(Connections.config_rescat)
    vendor_name, device_type = "", ""
    try:
        mycursor = mydb.cursor(buffered=True)
        resourceSql = "SELECT v_vendor, v_devicetype FROM c3p_logicalresourcespecification WHERE rs_lrs_id = %s"
        mycursor.execute(resourceSql, [rs_id])
        resourceResult = mycursor.fetchall()
        if resourceResult:
            vendor_name, device_type = resourceResult[0]
    except Exception as err:
        logger.error("tmf::c3p_tmf_res_spec_get_apiv2::getLogicalResourceSpec: %s", err)
    finally:
        mydb.close()
    return vendor_name, device_type


# Endpoints to TMF 634  Method ['GET']
# http://localhost:5000/c3p-p-core/api/ResourceFuncSpecification/v41/
# http://localhost:5000/c3p-p-core/api/ResourceFuncSpecification/v41/RFS5001

def listResourceFuncSpecification(id, args):
    data = {}
    mydb = Connections.create_connection(Connections.config_rescat)
    fieldsData = []
    filterQuery = ""
    rfsdata = []
    try:
        mycursor = mydb.cursor(buffered=True)
        if args:
            field = args.get("field", "")
            fieldsData = field.split(",")
            logger.debug("tmf::c3p_tmf_res_spec_get_apiv2::listResourceFuncSpecification::field: %s", fieldsData)
            filterQuery = setFilterResource(args)
        resourceSql = (
            "SELECT DISTINCT P.rfs_id, rfs_category, rfs_description, rfs_href, rfs_isBundle, rfs_lastUpdate, "
            "rfs_lifecycleStatus, rfs_name, rfs_version, rgs_id, rgs_description, rgs_name, rgs_baseType, "
            "rgs_schemaLocation, rgs_type, B.rtp_StartDateTime, B.rtp_endDateTime, A.rfs_id "
            "FROM c3p_resource_function_specification AS P "
            "LEFT JOIN c3p_resource_graph_specification A ON P.rfs_id = A.rfs_id "
            "INNER JOIN c3p_timeperiod B ON P.rfs_validfor = B.rtp_id"
        )
        params = []
        if id:
            resourceSql += f" HAVING A.rfs_id = %s"
            params.append(id)
        if filterQuery:
            resourceSql += f" AND %s"
            params.append(filterQuery)
        mycursor.execute(resourceSql, params)
        resourceResult = mycursor.fetchall()
        for rs_result in resourceResult:
            data = {
                "id": rs_result[0],
                "category": rs_result[1],
                "description": rs_result[2],
                "href": rs_result[3],
                "isBundle": rs_result[4],
                "lastUpdate": rs_result[5],
                "lifecycleStatus": rs_result[6],
                "name": rs_result[7],
                "version": rs_result[8],
                "rgsId": rs_result[9],
                "rgsDescription": rs_result[10],
                "rgsName": rs_result[11],
                "@baseType": rs_result[12],
                "@schemaLocation": rs_result[13],
                "@type": rs_result[14],
                "validFor": {
                    "StartDateTime": rs_result[15],
                    "EndDateTime": rs_result[16]
                },
                "targetResourceSchema": {
                    "type": rs_result[14],
                    "@type": rs_result[14],
                    "@schemaLocation": rs_result[13]
                },
                "ResourceGraphSpecification": getResourceGraphSpecification(rs_result[9]),
                "ConnectionPointSpecificationRef": getConnectionPointSpecificationRef(rs_result[9])
            }
            rfsdata.append(data)
    except Exception as err:
        print(err)
        logger.error("tmf::c3p_tmf_res_spec_get_apiv2::listResourceFuncSpecification: %s", err)
    finally:
        mydb.close()
    if not id:
        return jsonify(rfsdata), status.HTTP_200_OK
    else:
        return jsonify(rfsdata[0]), status.HTTP_200_OK


def getResourceGraphSpecification(id):
    mydb = Connections.create_connection(Connections.config_rescat)
    graph_data = []
    try:
        mycursor = mydb.cursor(buffered=True)
        resourceSql = "SELECT rfs_id, rgs_description, rgs_name, rgs_baseType, rgs_schemaLocation, rgs_type, rgs_id " \
                      "FROM c3p_resource_graph_specification WHERE rgs_id = %s"
        mycursor.execute(resourceSql, [id])
        resourceResult = mycursor.fetchall()
        for rs_result in resourceResult:
            data = {
                "id": rs_result[0],
                "description": rs_result[1],
                "name": rs_result[2],
                "@baseType": rs_result[3],
                "@schemaLocation": rs_result[4],
                "type": rs_result[5],
                "@type": rs_result[5],
                "resourceGraphSpecificationRelationship": getResourceGraphSpecificationRelationship(rs_result[6]),
                "connectionSpecification": getConnectionSpecification(rs_result[6])
            }
            graph_data.append(data)
    except Exception as err:
        print(err)
        logger.error("tmf::c3p_tmf_res_spec_get_apiv2::getResourceGraphSpecification: %s", err)
    finally:
        mydb.close()
    return graph_data


def getResourceGraphSpecificationRelationship(id):
    mydb = Connections.create_connection(Connections.config_rescat)
    graphspec_data = []
    try:
        mycursor = mydb.cursor(buffered=True)
        resourceSql = "SELECT rgs_id, rgsr_relationshipType, rgsr_baseType, rgsr_schemaLocation, rgsr_type, rgsr_id " \
                      "FROM c3p_resource_graph_specification_relationship WHERE rgs_id = %s"
        mycursor.execute(resourceSql, [id])
        resourceResult = mycursor.fetchall()
        for rs_result in resourceResult:
            data = {
                "id": rs_result[0],
                "relationshipType": rs_result[1],
                "@baseType": rs_result[2],
                "@schemaLocation": rs_result[3],
                "type": rs_result[4],
                "@type": rs_result[4],
                "resourceGraphSpecificationRef": getResourceGraphSpecificationRef(rs_result[5])
            }
            graphspec_data.append(data)
    except Exception as err:
        print(err)
        logger.error("tmf::c3p_tmf_res_spec_get_apiv2::getResourceGraphSpecificationRelationship: %s", err)
    finally:
        mydb.close()
    return graphspec_data


def getResourceGraphSpecificationRef(id):
    mydb = Connections.create_connection(Connections.config_rescat)
    graphspecref_data = []
    try:
        mycursor = mydb.cursor(buffered=True)
        resourceSql = "SELECT rgsref_id, rgsref_href, rgsref_name, rgsref_baseType, rgsref_referredType, rgsref_schemaLocation, rgsref_type " \
                      "FROM c3p_resource_graph_specification_ref WHERE rgsr_id = %s"
        mycursor.execute(resourceSql, [id])
        resourceResult = mycursor.fetchall()
        for rs_result in resourceResult:
            data = {
                "id": rs_result[0],
                "href": rs_result[1],
                "name": rs_result[2],
                "@baseType": rs_result[3],
                "referredType": rs_result[4],
                "@schemaLocation": rs_result[5],
                "type": rs_result[6],
                "@type": rs_result[6]
            }
            graphspecref_data.append(data)
    except Exception as err:
        print(err)
        logger.error("tmf::c3p_tmf_res_spec_get_apiv2::getResourceGraphSpecificationRef: %s", err)
    finally:
        mydb.close()
    return graphspecref_data


def getConnectionSpecification(id):
    mydb = Connections.create_connection(Connections.config_rescat)
    connection_data = []
    try:
        mycursor = mydb.cursor(buffered=True)
        resourceSql = "SELECT cs_id, cs_associationType, cs_name, cs_baseType, cs_schemaLocation, cs_type, rgs_id " \
                      "FROM c3p_connection_specification WHERE rgs_id = %s"
        mycursor.execute(resourceSql, [id])
        resourceResult = mycursor.fetchall()
        for rs_result in resourceResult:
            data = {
                "id": rs_result[0],
                "associationType": rs_result[1],
                "name": rs_result[2],
                "@baseType": rs_result[3],
                "@schemaLocation": rs_result[4],
                "type": rs_result[5],
                "@type": rs_result[5],
                "endpointSpecificationRef": getEndpointSpecificationRef(rs_result[0])
            }
            connection_data.append(data)
    except Exception as err:
        print(err)
        logger.error("tmf::c3p_tmf_res_spec_get_apiv2::getConnectionSpecification: %s", err)
    finally:
        mydb.close()
    return connection_data


def getEndpointSpecificationRef(id):
    mydb = Connections.create_connection(Connections.config_rescat)
    endpoint_data = []
    try:
        mycursor = mydb.cursor(buffered=True)
        resourceSql = "SELECT cs_id, esr_href, esr_inRoot, esr_name, esr_role, esr_baseType, esr_referredType, esr_schemaLocation, esr_type, esr_id " \
                      "FROM c3p_endpoint_specification_ref WHERE cs_id = %s"
        mycursor.execute(resourceSql, [id])
        resourceResult = mycursor.fetchall()
        for rs_result in resourceResult:
            data = {
                "id": rs_result[0],
                "href": rs_result[1],
                "inRoot": rs_result[2],
                "name": rs_result[3],
                "role": rs_result[4],
                "@baseType": rs_result[5],
                "referredType": rs_result[6],
                "@schemaLocation": rs_result[7],
                "type": rs_result[8],
                "@type": rs_result[8],
                "connectionPointSpecificationRef": getConnectionPointSpecificationRef(rs_result[9])
            }
            endpoint_data.append(data)
    except Exception as err:
        print(err)
        logger.error("tmf::c3p_tmf_res_spec_get_apiv2::getEndpointSpecificationRef: %s", err)
    finally:
        mydb.close()
    return endpoint_data


def getConnectionPointSpecificationRef(id):
    mydb = Connections.create_connection(Connections.config_rescat)
    connectionref_data = []
    try:
        mycursor = mydb.cursor(buffered=True)
        resourceSql = "SELECT cpsr_id, esr_id, rfs_id, cpsr_href, cpsr_name, cpsr_version, cpsr_baseType, cpsr_referredType, cpsr_schemaLocation, cpsr_type " \
                      "FROM c3p_connection_point_specification_ref WHERE esr_id = %s OR rfs_id = %s"
        mycursor.execute(resourceSql, [id, id])
        resourceResult = mycursor.fetchall()
        for rs_result in resourceResult:
            data = {
                "id": rs_result[0],
                "href": rs_result[3],
                "name": rs_result[4],
                "version": rs_result[5],
                "@baseType": rs_result[6],
                "referredType": rs_result[7],
                "@schemaLocation": rs_result[8],
                "type": rs_result[9],
                "@type": rs_result[9]
            }
            connectionref_data.append(data)
    except Exception as err:
        print(err)
        logger.error("tmf::c3p_tmf_res_spec_get_apiv2::getConnectionPointSpecificationRef: %s", err)
    finally:
        mydb.close()
    return connectionref_data