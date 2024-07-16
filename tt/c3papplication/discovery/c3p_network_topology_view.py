#!/c3ppy/c3pnwt
""" 
Collect Deviceinformation and generate the network topology view

Author  : Sujit Mahajan
Date    : 04/Dec/2020

"""
from c3pnwt.nwtRF import ncRF  # change the name
from c3pnwt.features.vlan import Vlan
from c3pnwt.features.interface import Interface
from c3pnwt.features.neighbor import Neighbors
from c3pnwt.utils.xml.lib import *
from c3plib.extract import json_extract
import yaml, logging
import pprint
import json
import re

logger = logging.getLogger(__name__)

##########################
# CONFIGURATION OF ACCESS
##########################
USER = "c3pteam"

"""
use of hard coded keys should not be there, please if you find solution to it 
remove the hard coded password in the below function. 

"""
PASS = "csr1000v"
PORT = 830

#########################################################
# REGULAR EXPLRESSIONS FOR MATCHING PORT NAMES TO SPEEDS
# NOTE: This is used in visuzation later to color lines
#########################################################
LINK_SPEEDS = [("^TwentyGigE*", "20"),
               ("^FortyGig*", "40"),
               ("^Ten-GigabitEthernet*", "10"),
               ("^GigabitEthernet*", "1")]

#########################################################
# REGULAR EXPLRESSIONS FOR MATCHING DEVICES HIERARHY
# E.g. Access layer switches have "AC" in their name
# or aggregation layer devices have "AG" in their names
#########################################################
NODE_HIERARCHY = [('.+ICB.*', "2"),
                  ('^[a-zA-Z]{5}AG.*', "3"),
                  ('^[a-zA-Z]{5}AC.*', "2"),
                  ('^[a-zA-Z]{5}L2.*', "4")]


####################
# Connection method
####################
def connect(host, username, password, port):
    args = dict(host=host, username=username, password=password, port=port)
    logger.info("connect - Connecting :: " + host)
    # CREATE CONNECTION
    device = ncRF(**args)
    device.open()
    return device


################################
# Returns RAW python Dictionary
# with Neighbor NETCONF details
#################################
def getNeighbors(device):
    logger.info("getNeighbors - In side getNeighbors")
    neighbors = Neighbors(device)
    neigh_type = dict(default='lldp', choices=['cdp', 'lldp'])
    response = getattr(neighbors, "lldp")
    results = dict(neighbors=response)
    clean_results = list()

    for neighbor in results['neighbors']:
        if str(neighbor['neighbor']) == "None" or str(neighbor['neighbor']) == "":
            logger.info("getNeighbors - Removing probably bad neighbor %s \"" + str(neighbor['neighbor']) + "\"");
        else:
            clean_results.append(neighbor)
    logger.info("getNeighbors - clean_results :: %s", clean_results)
    return clean_results


###############################################
# Takes RAW Dictionary of Neighbors and returns
# simplified Dictionary of only Neighbor nodes
# for visuzation as a node (point)
#
# NOTE: Additionally this using RegEx puts layer
# hierarchy into the result dictionary
###############################################
def getNodesFromNeighborships(neighborships):
    logger.info('getNodesFromNeighborships: start')
    nodes = {'nodes': []}
    # for key,value in neighborships.iteritems():
    for key, value in neighborships.items():
        logger.debug("getNodesFromNeighborships -Key: %s" + str(key) + ":")

        '''
        PATTERNS COMPILATIOn
        '''
        logger.debug("Hostname matched[key]: %s" + key)
        group = "1"  # for key (source hostname)
        for node_pattern in NODE_HIERARCHY:
            logger.debug("getNodesFromNeighborships - Pattern: %s" + node_pattern[0]);
            pattern = re.compile(node_pattern[0]);
            if pattern.match(key):
                logger.debug("getNodesFromNeighborships - match")
                group = node_pattern[1]
                break
        logger.debug("getNodesFromNeighborships - Final GROUP for key: %s" + key + " is %s" + group)

        candidate = {"id": key, "group": group}
        if candidate not in nodes['nodes']:
            logger.debug("getNodesFromNeighborships - adding")
            nodes['nodes'].append(candidate)

        for neighbor in value:
            logger.debug("getNodesFromNeighborships - neighbor: %s" + str(neighbor['neighbor']) + ":")
            '''
            PATTERNS COMPILATIOn
            '''
            logger.debug("getNodesFromNeighborships - Hostname matched: %s" + neighbor['neighbor'])
            group = "1"
            for node_pattern in NODE_HIERARCHY:
                logger.debug("getNodesFromNeighborships - Pattern: %s" + node_pattern[0]);
                pattern = re.compile(node_pattern[0]);
                if pattern.match(neighbor['neighbor']):
                    logger.debug("getNodesFromNeighborships - match")
                    group = node_pattern[1]
                    break
            logger.debug("getNodesFromNeighborships - Final GROUP for neighbor: %s" + key + " is %s" + group)

            candidate2 = {"id": neighbor['neighbor'], "group": group}
            if candidate2 not in nodes['nodes']:
                logger.debug("getNodesFromNeighborships -adding")
                nodes['nodes'].append(candidate2)

    return nodes


###############################################
# Takes RAW Dictionary of Neighbors and returns
# simplified Dictionary of only links between
# nodes for visuzation later (links)
#
# NOTE: Additionally this using RegEx puts speed
# into the result dictionary
###############################################
def getLinksFromNeighborships(neighborships):
    logger.info("getLinksFromNeighborships:")

    links = {'links': []}
    # for key,value in neighborships.iteritems():
    for key, value in neighborships.items():
        print(str(key))
        for neighbor in value:

            '''
            PATTERNS COMPILATIOn
            '''
            logger.debug("getLinksFromNeighborships - Interface matched: %s" + neighbor['local_intf'])
            speed = "1"  # DEFAULT
            for speed_pattern in LINK_SPEEDS:
                logger.debug("getLinksFromNeighborships - Pattern: %s" + speed_pattern[0])
                pattern = re.compile(speed_pattern[0])

                if pattern.match(neighbor['local_intf']):
                    speed = speed_pattern[1]

            logger.debug("getLinksFromNeighborships - Final SPEED: %s" + speed)

            links['links'].append({"source": key, "target": neighbor['neighbor'], "value": speed})

    return links


##############################################
# Filters out links from simplified Dictionary
# that are not physical
# (e.g Loopback or VLAN interfaces)
#
# NOTE: Uses the same RegEx definitions as
# speed assignment
##############################################
def filterNonPhysicalLinks(interfacesDict):
    onlyPhysicalInterfacesDict = dict()

    logger.debug("filterNonPhysicalLinks :: %s", interfacesDict)

    # for key,value in interfacesDict.iteritems():
    for key, value in interfacesDict.items():
        logger.debug("filterNonPhysicalLinks - Key: %s" + str(key) + ":")
        onlyPhysicalInterfacesDict[key] = [];

    for interface in value:

        bIsPhysical = False;
        for name_pattern in LINK_SPEEDS:
            pattern = re.compile(name_pattern[0])

            if pattern.match(interface['local_intf']):
                bIsPhysical = True;
                onlyPhysicalInterfacesDict[key].append({"local_intf": interface['local_intf'],
                                                        "oper_status": interface['oper_status'],
                                                        "admin_status": interface['admin_status'],
                                                        "actual_bandwith": interface['actual_bandwith'],
                                                        "description": interface['description']})
                break;

        logger.debug("filterNonPhysicalLinks - %s",
                     str(bIsPhysical) + " - local_intf:" + interface['local_intf'] + " is physical.")

    return onlyPhysicalInterfacesDict


##############################################
# Filters out links from simplified Dictionary
# that are not in Operational mode "UP"
##############################################
def filterNonActiveLinks(interfacesDict):
    onlyUpInterfacesDict = dict()

    logger.debug("filterNonActiveLinks")
    # for key,value in interfacesDict.iteritems():
    for key, value in interfacesDict.items():
        logger.debug("filterNonActiveLinks - Key: %s" + str(key) + ":")
        onlyUpInterfacesDict[key] = [];

        for interface in value:
            if interface['oper_status'] == 'UP':
                onlyUpInterfacesDict[key].append({"local_intf": interface['local_intf'],
                                                  "oper_status": interface['oper_status'],
                                                  "admin_status": interface['admin_status'],
                                                  "actual_bandwith": interface['actual_bandwith'],
                                                  "description": interface['description']})
            logger.debug("filterNonActiveLinks - local_intf: %s" + interface['local_intf'] + " is OPRATIONAL.")

    return onlyUpInterfacesDict;


################################################
# Takes RAW neighbors dictionary and simplified
# links dictionary and cross-references them to
# find links that are there, but have no neighbor
################################################
def filterLinksWithoutNeighbor(interfacesDict, neighborsDict):
    neighborlessIntlist = dict()

    logger.debug("filterLinksWithoutNeighbor")
    # for devicename,neiInterfaceDict in neighborships.iteritems():
    for devicename, neiInterfaceDict in neighborsDict.items():
        logger.debug("filterLinksWithoutNeighbor - Key(device name): %s" + str(devicename) + ":")

        neighborlessIntlist[devicename] = []

        for interface in interfacesDict[devicename]:
            bHasNoNeighbor = True
            for neighbor_interface in neiInterfaceDict:
                logger.debug("filterLinksWithoutNeighbor - local_intf: %s" + interface['local_intf']
                             + " neighbor_interface['local_intf']:" + neighbor_interface['local_intf'])
                if interface['local_intf'] == neighbor_interface['local_intf']:
                    # Tries to remove this interface from list of interfaces
                    # interfacesDict[devicename].remove(interface)
                    bHasNoNeighbor = False
                    logger.debug("filterLinksWithoutNeighbor - BREAK")
                    break;
            if bHasNoNeighbor:
                neighborlessIntlist[devicename].append(interface)
                logger.debug(
                    "filterLinksWithoutNeighbor - Neighborless Interface on device: %s" + devicename + " int:" +
                    interface['local_intf'])

    return neighborlessIntlist;


###########################
# Collects all Interfaces
# using NETCONF interface
# from a Device
#
# NOTE: INcludes OperStatus
# and ActualBandwidth and
# few other parameters
###########################

def getInterfaces(device):
    logger.debug('getInterfaces')

    E = data_element_maker()
    top = E.top(
        E.Ifmgr(
            E.Interfaces(
                E.Interface(
                )
            )
        )
    )
    nc_get_reply = device.get(('subtree', top))

    intName = findall_in_data('Name', nc_get_reply.data_ele)
    ## 2 == DOWN ; 1 == UP
    intOperStatus = findall_in_data('OperStatus', nc_get_reply.data_ele)
    ## 2 == DOWN ; 1 == UP
    intAdminStatus = findall_in_data('AdminStatus', nc_get_reply.data_ele)
    IntActualBandwidth = findall_in_data('ActualBandwidth', nc_get_reply.data_ele)
    IntDescription = findall_in_data('Description', nc_get_reply.data_ele)

    deviceActiveInterfacesDict = []
    for index in range(len(intName)):

        # Oper STATUS
        OperStatus = 'UNKNOWN'
        if intOperStatus[index].text == '2':
            OperStatus = 'DOWN'
        elif intOperStatus[index].text == '1':
            OperStatus = 'UP'

        # Admin STATUS
        AdminStatus = 'UNKNOWN'
        if intAdminStatus[index].text == '2':
            AdminStatus = 'DOWN'
        elif intAdminStatus[index].text == '1':
            AdminStatus = 'UP'

        deviceActiveInterfacesDict.append({"local_intf": intName[index].text,
                                           "oper_status": OperStatus,
                                           "admin_status": AdminStatus,
                                           "actual_bandwith": IntActualBandwidth[index].text,
                                           "description": IntDescription[index].text})

    return deviceActiveInterfacesDict


""" Must convert this call into a URL - API call as end point /c3p/api/nwTopologyView/ 

Input JSON with list of Host Name / IP address

"""


###########################
# GET Network Topology View
# Input parameter is the Hostname / IP Address / Device ID
###########################

def nwTopologyView(inParam):
    logger.debug("nwTopologyView - Opening DEVICES.txt in local directory to read target device IP/hostnames")

    # This will be the primary result neighborships dictionary
    neighborships = dict()

    # This will be the primary result interfaces dictionary
    interfaces = dict()

    '''
    LETS GO AND CONNECT TO EACH ONE DEVICE AND COLLECT DATA
    '''
    logger.debug("nwTopologyView - Starting LLDP info collection...")
    logger.debug('nwTopologyView - in Parameters :: %s', inParam)
    ########################
    # JSON Extraction Logic
    #######################
    r = json.dumps(inParam)
    logger.debug("nwTopologyView - r type :: %s", type(r))
    hnames = json_extract(r, 'hostname')
    logger.debug("nwTopologyView - name :: %s", hnames)

    for nhost in inParam['hostname']:
        logger.debug(nhost + USER + PASS + str(PORT))
        devicehostname = nhost.replace('\n', '')
        device = connect(devicehostname, USER, PASS, PORT)
        logger.debug("nwTopologyView - device :: %s", device)
        if device.connected:
            print("success")
        else:
            logger.debug("nwTopologyView - failed to connect to %s" + nhost + " .. skipping")
            continue

        ###
        # Here we are connected, let collect Interfaces
        ###
        interfaces[devicehostname] = getInterfaces(device)
        logger.debug("nwTopologyView - Interfaces :: %s", interfaces[devicehostname])
        ###
        # Here we are connected, let collect neighbors
        ###
        new_neighbors = getNeighbors(device)
        neighborships[devicehostname] = new_neighbors

    '''
    NOW LETS PRINT OUR ALL NEIGHBORSHIPS FOR DEBUG
    '''
    pprint.pprint(neighborships)
    with open('output/neighborships.json', 'w') as outfile:
        json.dump(neighborships, outfile, sort_keys=True, indent=4)
        logger.debug("nwTopologyView - JSON printed into neighborships.json")

    '''
    NOW LETS PRINT OUR ALL NEIGHBORSHIPS FOR DEBUG
    '''
    interfaces = filterNonActiveLinks(filterNonPhysicalLinks(interfaces))
    pprint.pprint(interfaces)
    with open('output/interfaces.json', 'w') as outfile:
        json.dump(interfaces, outfile, sort_keys=True, indent=4)
        logger.debug("nwTopologyView - JSON printed into interfaces.json")

    '''
    GET INTERFACES WITHOUT NEIGHRBOR
    '''
    logger.debug("=====================================")
    logger.debug("no_neighbor_interfaces.json DICTIONARY ")
    logger.debug("======================================")
    interfacesWithoutNeighbor = filterLinksWithoutNeighbor(interfaces, neighborships)
    with open('output/no_neighbor_interfaces.json', 'w') as outfile:
        json.dump(interfacesWithoutNeighbor, outfile, sort_keys=True, indent=4)
        logger.debug("JSON printed into no_neighbor_interfaces.json")

    '''
    NOW LETS FORMAT THE DICTIONARY TO NEEDED D3 LIbary JSON
    '''
    logger.debug("================")
    logger.debug("NODES DICTIONARY")
    logger.debug("================")
    nodes_dict = getNodesFromNeighborships(neighborships)
    pprint.pprint(nodes_dict)

    logger.debug("================")
    logger.debug("LINKS DICTIONARY")
    logger.debug("================")
    links_dict = getLinksFromNeighborships(neighborships)
    pprint.pprint(links_dict)

    logger.debug("==========================================")
    logger.debug("VISUALIZATION graph.json DICTIONARY MERGE")
    logger.debug("==========================================")
    visualization_dict = {'nodes': nodes_dict['nodes'], 'links': links_dict['links']}

    with open('output/graph.json', 'w') as outfile:
        json.dump(visualization_dict, outfile, sort_keys=True, indent=4)
        logger.debug("JSON printed into graph.json")

    # Bugfree exit at the end 
    quit(0)


""" -------------------------------------------------------------- """
###########################
# MAIN ENTRY POINT TO THE 
# SCRIPT IS HERE
###########################  

if __name__ == "__main__":
    quit(0)