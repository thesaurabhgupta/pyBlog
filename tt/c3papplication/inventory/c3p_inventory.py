import logging
from flask_api import status
from jproperties import Properties
from c3papplication.common import Connections
from c3papplication.conf.springConfig import springConfig
import requests
import json
logger = logging.getLogger(__name__)

configs = springConfig().fetch_config()

C3P_Application = (configs.get("C3P_Application")).strip()


def bmcInventory(param):
    "ipAddress OR hostName OR inventoryId"
    # ipAddress = param.get('managementIp',"")
    ipAddress = param.get('mgmtIp',"")
    ipAddress = ipAddress.replace('\r\n','').replace('\n','') 
    logger.debug("c3p_inventory:bmcInventory :: ipAddress : %s",ipAddress)
    hostName = param.get('hostName',"")
    hostName = hostName.replace('\r\n','').replace('\n','') 
    logger.debug("c3p_inventory:bmcInventory :: hostName : %s", hostName)
    # inventoryId = param.get('deviceId',"")
    inventoryId = param.get('inrId',"")
    inventoryId = inventoryId.replace('\r\n','').replace('\n','') 
    logger.debug("c3p_inventory:bmcInventory :: inventoryId : %s", inventoryId)

    result = {}
    try:
        # Creating a database connection
        mydb = Connections.create_connection()
        mycursor = mydb.cursor(buffered=True)

        if (ipAddress!="" and hostName!="" and inventoryId!=""):
            logger.debug("c3p_inventory:bmcInventory :: All present")
            sql = "SELECT d_hostname,d_vendor,d_mgmtip,d_vnf_support,d_id FROM c3p_deviceinfo where d_mgmtip=%s and d_hostname=%s and d_id=%s"
            logger.debug("c3p_inventory:bmcInventory :: sql : %s",sql)
            mycursor.execute(sql, (ipAddress, hostName, inventoryId))
            data = mycursor.fetchone()
            logger.info("c3p_inventory:bmcInventory :: data : %s",data)

        elif(ipAddress=="" and hostName!="" and inventoryId!=""):
            logger.debug("c3p_inventory:bmcInventory :: hostName,inventoryId present")
            sql = "SELECT d_hostname,d_vendor,d_mgmtip,d_vnf_support,d_id FROM c3p_deviceinfo where d_hostname = %s and d_id =%s"
            logger.debug("c3p_inventory:bmcInventory :: sql : %s", sql)
            mycursor.execute(sql, (hostName,inventoryId,))
            data = mycursor.fetchone()
            logger.info("c3p_inventory:bmcInventory :: data : %s", data)

        elif(ipAddress!="" and hostName=="" and inventoryId!=""):
            logger.debug("c3p_inventory:bmcInventory :: ipAddress,inventoryId present")
            sql = "SELECT d_hostname,d_vendor,d_mgmtip,d_vnf_support,d_id FROM c3p_deviceinfo where d_mgmtip = %s and d_id = %s"
            logger.debug("c3p_inventory:bmcInventory :: sql : %s", sql)
            mycursor.execute(sql, (ipAddress, inventoryId,))
            data = mycursor.fetchone()
            logger.info("c3p_inventory:bmcInventory :: data : %s", data)

        elif(ipAddress!="" and hostName!="" and inventoryId==""):
            logger.debug("c3p_inventory:bmcInventory :: ipAddress,hostName present")
            sql = "SELECT d_hostname,d_vendor,d_mgmtip,d_vnf_support,d_id FROM c3p_deviceinfo where d_mgmtip = %s and d_hostname = %s"
            logger.debug("c3p_inventory:bmcInventory :: sql : %s", sql)
            mycursor.execute(sql, (ipAddress,hostName,))
            data = mycursor.fetchone()
            logger.info("c3p_inventory:bmcInventory :: data : %s", data)

        else:
            logger.debug("c3p_inventory:bmcInventory :: elseloop Any 1 present")
            sql = "SELECT d_hostname,d_vendor,d_mgmtip,d_vnf_support,d_id FROM c3p_deviceinfo where d_mgmtip = %s or d_hostname = %s or d_id = %s"
            #sql = "SELECT d_hostname,d_vendor,d_mgmtip,d_vnf_support,d_id FROM c3p_deviceinfo where d_mgmtip = %s or d_hostname = %s or d_id = %s ", (ipAddress,hostName,inventoryId,)
            logger.debug("c3p_inventory:bmcInventory :: sql : %s", sql)
            mycursor.execute(sql, (ipAddress, hostName, inventoryId, ))
            data = mycursor.fetchone()
            logger.info("c3p_inventory:bmcInventory :: data : %s", data)

        logger.info("c3p_inventory:bmcInventory :: data : %s", data)
        if data is None:
            raise Exception("Input parameters not matched")

        logger.info("Data: %s",data)
        discoveryDetails = APIc3pDiscoveryDetails(data[0])
        logger.info("discoveryDetails: %s", discoveryDetails)
        cardSlots = APIc3pCardSlots(data[0])
        logger.info("cardSlots: %s", cardSlots)
        params = {
            "vendor": data[1],
            "networkType": data[3],
            "ipAddress": data[2],
            "deviceId": data[4]
        }
        logger.info("params %s",params)
        interfaceDetails = APIc3pInterfaceDetails(params)
        logger.info("interfaceDetails: %s", interfaceDetails)
        result = {
            "entity": {
                "deviceDetails": formatDiscoveryDetails(discoveryDetails),
                "interfaces": interfaceDetails,
                "cardslot": cardSlots,
            }
        }
        logger.info("result: %s", result)

    except Exception as err:
        logger.error("inventory::c3p_inventory::bmcInventory: %s", err)
        result = {
            "Error": "BMC Inventory error"
        }

    finally:
        mydb.close
    return result


def APIc3pDiscoveryDetails(hostName):
    try:
        logger.debug("c3p_inventory:APIc3pDiscoveryDetails")
        url = C3P_Application + "/c3p-j-core/discovery/deviceDetails?hostname=" + hostName
        logger.debug("c3p_inventory:APIc3pDiscoveryDetails :: url : %s",url)
        response = requests.get(url)
        if response.ok:
            return response.json()
    except Exception as err:
        logger.error("inventory::c3p_inventory::APIc3pDiscoveryDetails: %s", err)
        return {"Error": "Discovery Details error"}


def APIc3pCardSlots(hostName):
    try:
        url = C3P_Application + "/c3p-j-core/cardslots/cards?hostName=" + hostName
        logger.debug("c3p_inventory:APIc3pCardSlots :: url : %s", url)
        response = requests.get(url)
        if response.ok:
            return response.json()
    except Exception as err:
        logger.error("inventory::c3p_inventory::APIc3pCardSlots: %s", err)
        return {"Error": "Card Slots error"}


def APIc3pInterfaceDetails(params):
    try:
        url = C3P_Application + "/c3p-j-core/deviceDiscrepancy/intefaceDetails"
        logger.debug("c3p_inventory:APIc3pInterfaceDetails :: url : %s", url)
        response = requests.post(url, json=params)
        displayNameKeyMapping = {
            'Interface Name': 'intName',
            'Description': 'intDescription',
            'IP Address': 'intIPAddress',
            'IP Subnet Mask': 'intIPSubnetMask',
            'Admin Status': 'intAdminStatus',
            'Operational Status': 'intOperationalStatus'
        }
        if response.ok:
            data = response.json()
            logger.info("data in interface %s",data)
            for interface in data["interfaces"]:
                interface['id'] = ''.join(interface['id'].split('.'))
                for child in interface["childOid"]:
                    child['id'] = ''.join(child['id'].split('.'))
            return data
    except Exception as err:
        logger.error("inventory::c3p_inventory::APIc3pInterfaceDetails: %s", err)
        return {"Error": "Interface Details error"}


def deviceInventoryDashboard():
    try:
        url = C3P_Application + "/c3p-j-core/discovery/deviceInventoryDashboard"
        logger.debug("c3p_inventory:deviceInventoryDashboard :: url : %s", url)
        response = requests.get(url)
        if response.ok:
            format_out = formatDashboardData(response.json())
            return {"neList": format_out}
    except Exception as err:
        logger.error("inventory::c3p_inventory::APIc3pDeviceInventoryDashboard: %s", err)
        return {"Error": "Device Inventory Dashboard error"}


def formatDiscoveryDetails(discoveryDetails):
    """
    Formatting discovery details

    :param: discoveryDetails : dict()

    return: neDetails : list()
    """
    neDetails = []
    # Creating a map for changing the key of discoveryDetails to acceptable format
    detailsRequiredMapping = {
        "dId": "inrId",
        "dHostName": "neHostName",
        "dMgmtIp": "neMgmtIp",
        "dVendor": "neVendor",
        "dModel": "neModel",
        "dOs": "neOs",
        "dOsVersion": "neOsVersion",
        "dSerialNumber": "neSerialNumber",
        "dType": "neType",
        "dRole": "neRole",
        "dDecommDate": "neDecommDate",
        "dDecommTime": "neDecommTime",
        "dDeviceFamily": "neDeviceFamily",
        "dEndOfLife": "neEndOfLife",
        "dEndOfSaleDate": "neEndOfSaleDate",
        "dEndOfSupportDate": "neEndOfSupportDate",
        "dIPAddrSix": "neIPAddrSix",
        "dImageFileName": "neImageFileName",
        "dLifeCycleState": "neLifeCycleState",
        "dMACAddress": "neMACAddress",
        "dNamespace": "neNamespace",
        "dNewDevice": "neNewDevice",
        "dNumberOfPods": "neNumberOfPods",
        "dRefDeviceId": "neRefDeviceId",
        "dReleaseVer": "neReleaseVer",
        "dStatus": "neStatus",
        "dSystemDescription": "neSystemDescription"
    }
    # Looping over the details and create neDetails object
    for each in discoveryDetails['entity']['deviceDetails']:
        neObj = dict()
        contactDetailsList = each.get('contactDetails', [])
        neContactDetailsList = []
        # neContactDetailsList array has lot of objects in which mapping was done to format keys to start with 'ne'
        for contactDetails in contactDetailsList:
            neContactDetails = dict()
            # Looping at all keys and storing the formatted key value with existing key value
            for key in contactDetails.keys():
                neContactDetails[key.replace('d', 'ne', 1)] = contactDetails[key]

            neContactDetailsList.append(neContactDetails)
        custSiteDetails = each.get('custSiteDetails', {})
        # Removing non required data from site details
        custSiteDetails.pop('cSiteStatus', False)
        custSiteDetails.pop('handler', False)
        custSiteDetails.pop('hibernateLazyInitializer', False)
        custSiteDetails.pop('id', False)

        # Creating neObj with informations formatted and fetched
        neObj['contactDetails'] = neContactDetailsList
        neObj['custSiteDetails'] = custSiteDetails
        neObj['locationDetails'] = each.get('locationDetails', {})
        # Fetching other information from the details object to formatted key using the existing key
        for reqDetKey in detailsRequiredMapping.keys():
            neObj[detailsRequiredMapping[reqDetKey]] = each.get(reqDetKey, "")
        neDetails.append(neObj)
    return neDetails


def formatDashboardData(dashboardData):
    """
    Formatting dashboard details

    :param: dashboardData : dict()

    return: neList : list()
    """
    neList = []
    # Creating a map for changing the key of dashboardData to acceptable format
    dashboardRequiredMapping = {
        "customer": "customer",
        "deviceId": "inrID",
        "discreapncyFlag": "neDisFlag",
        "deviceFamily": "neFamily",
        "hostName": "neHostName",
        "isNew": "neIsNew",
        "market": "neMarket",
        "managementIp": "neMgmtIP",
        "model": "neModel",
        "region": "neRegion",
        "role": "neRole",
        "siteId": "neSiteId",
        "status": "neStatus",
        "vendor": "neVendor",
    }
    # Looping over each entitiy data field
    for each in dashboardData['entity'].get('data', []):
        neObj = dict()
        # Creating neObj by replacing new formatted key with value using previous key from teh dashboard object
        for dashReqKey in dashboardRequiredMapping.keys():
            neObj[dashboardRequiredMapping[dashReqKey]] = each.get(dashReqKey, "")
        # Appending to the neList
        neList.append(neObj)
    return neList