import json,logging
from datetime import datetime
from flask import jsonify
#import Connections
from c3papplication.common import Connections
from c3papplication.conf.springConfig import springConfig
import requests 
from requests.auth import HTTPBasicAuth
from jproperties import Properties
import mysql.connector
from c3papplication.discovery import c3p_physical_topology as phyTopology
import ipaddress

logger = logging.getLogger(__name__)

configs = springConfig().fetch_config()


""" Create Logical Topology 
        Based on discovery value, this module will generate the Logical Topology View for given device / network element 
        sIP     : Source IP Address 
        sHost   : Source Host Name 
        lTopo   : Type of Logical Topology to View, value of this parameter will consider only if opr = 'VRL' 
                    'ALL    : All logical topplogy e.g. BGP, OSPF 
                    'RBGP'   : BGP Logical Topology
                    'ROSPFV2'  : OSPFV2 Logical Topology
        opr     : Operation t perform 
                    'VLT'   : View Logical Topology
                    'RLT'   : Refresh the Logical Topology
        sSystem : Source System 
                    'C3P-UI': Consider as Internal C3P
                    
"""

def create_logical_topology(content):
    
    s_mgmtip    = content['mgmtip']
    s_hostname  = content['hostname']
    s_device_id = content['device_id']
    lTopo       = content['topology']
    opr         = content['operation']
    sSystem     = content['sourcesystem']

    logger.debug('s_mgmtip      ::%s', s_mgmtip)
    logger.debug('s_hostname    ::%s', s_hostname)
    logger.debug('s_device_id   ::%s', s_device_id)
    logger.debug('lTopo         ::%s', lTopo)
    logger.debug('opr           ::%s', opr)
    logger.debug('sSystem       ::%s', sSystem)



# def create_logical_topology(s_mgmtip, s_hostname, s_device_id , lTopo, opr, sSystem):

    tp_created_date     = datetime.today().strftime('%Y-%m-%d %H:%M:%S')
    

    # if logical_topology == 'BGP':
    #     l_OID = '1.3.6.1.2.1.15.3.1.%'
    # elif logical_topology == 'OSPF':
    #     l_OID = '1.3.6.1.2.1.15.3.1.%'

    #l_created_date = datetime.today().strftime('%Y-%m-%d %H:%M:%S')


    BGP_Neighbour_Status    = []
    BGP_Neighbour_IPAddress = []
    BGP_Neighbour_ASNumber  = []
    BGP_Source_ASNumber     = ''
    OSPF_IPAddress          = []
    OSPF_Neighbour_ID       = []
    OSPF_Priority           = []
    OSPF_Neighbour_Stat     = []
    OSPF_AreaID             = []    # Capture Area ID
    #ROSPF                   = []
    inValue                 = []
    #rOSPF                   = []    # JSON result for OSPF
    #rBGP                    = []    # JSON result for BGP
    logical_topo_data       = []
    topology_color          = {"RBGP":"#e70000", "ROSPFV2":"#00e700", "ROSPFV3":"#0000e7","VPN-Tunnel":"#a1a1a1", "VPN-VRF":"#b0a643","VPN-IPSec":"#b6f2c0","LINK":"#140056"}
    topology_label          = {"RBGP":"Routing BGP", "ROSPFV2":"Routing OSPF V2", "ROSPFV3":"Routing OSPF V3","VPN-Tunnel":"VPN-Tunnel", "VPN-VRF":"VPN-VRF","VPN-IPSec":"VPN-IPSec","LINK":"LINK"}

    
    #linkHead = ("SourceIP","SOurceHost", )

    mydb = Connections.create_connection()
    try:    
        mycursor = mydb.cursor(buffered=True)

        refresh_logical_topology(s_mgmtip, sSystem)

        if sSystem.lower() == 'c3p-ui':
            sql = "SELECT fid_ip_address, device_id, fid_oid_no, fid_child_oid_no, fid_discovered_value FROM c3p_t_fork_inv_discrepancy WHERE (fid_oid_no LIKE '1.3.6.1.2.1.15.%' OR fid_oid_no LIKE '1.3.6.1.2.1.14.%') AND fid_ip_address = %s"
        else:
            sql = "SELECT fid_ip_address, device_id, fid_oid_no, fid_child_oid_no, fid_discovered_value FROM c3p_t_ext_fork_inv_discrepancy WHERE (fid_oid_no LIKE '1.3.6.1.2.1.15.%' OR fid_oid_no LIKE '1.3.6.1.2.1.14.%') AND fid_ip_address = %s"

        try:
            mycursor.execute(sql, (s_mgmtip,))
            results = mycursor.fetchall()
        except mysql.connector.errors.ProgrammingError as e:
            logger.debug('CLT :: Fetch Error :: %s', e)

        for res in results:
            if res[2] == '1.3.6.1.2.1.15.3.1.7':
                BGP_Neighbour_IPAddress.append(res[4])
            elif res[2] == '1.3.6.1.2.1.15.2':
                BGP_Source_ASNumber = res[4]
            elif res[2] == '1.3.6.1.2.1.15.3.1.9':
                BGP_Neighbour_ASNumber.append(res[4])
            elif res[2] == '1.3.6.1.2.1.15.3.1.3':
                BGP_Neighbour_Status.append(res[4])
            elif res[2] == '1.3.6.1.2.1.14.10.1.1':
                OSPF_IPAddress.append(res[4])
            elif res[2] == '1.3.6.1.2.1.14.10.1.3':
                OSPF_Neighbour_ID.append(res[4])
            elif res[2] == '1.3.6.1.2.1.14.10.1.5':
                OSPF_Priority.append(res[4])
            elif res[2] == '1.3.6.1.2.1.14.10.1.6':
                OSPF_Neighbour_Stat.append(res[4])
            elif res[2] == '1.3.6.1.2.1.14.2.1.1':
                OSPF_AreaID.append(res[4])
        """ For BGP Neighbour - Logical Topology """

        for m in range(len(BGP_Neighbour_IPAddress)):
            inValue=('RBGP', s_device_id , s_hostname, s_mgmtip, '', '', '', 'ASNumber', BGP_Source_ASNumber, 0, '', '', '', '', BGP_Neighbour_IPAddress[m], 'ASNumber', BGP_Neighbour_ASNumber[m], 'system', tp_created_date);
            logical_topo_data.append(inValue)

        """ For OSPF Neighbour - Logical Topology """
        logger.debug('Length OSPF_IPAddress::: %s', len(OSPF_IPAddress))
        logger.debug('Length OSPF_AreaID::: %s', len(OSPF_AreaID))

        if len(OSPF_IPAddress) != len(OSPF_AreaID):
            if len(OSPF_IPAddress) > len(OSPF_AreaID):
                for m in range (len(OSPF_IPAddress)-len(OSPF_AreaID)):
                    OSPF_AreaID.append('-')
            else:
                for m in range (len(OSPF_AreaID)-len(OSPF_IPAddress)):
                    OSPF_IPAddress.append('-')

       
        for m in range(len(OSPF_IPAddress)):
            inValue=('ROSPFV2', s_device_id , s_hostname, s_mgmtip, '', '', '', 'AreaID', OSPF_AreaID[m], 0, '', '', '', '', OSPF_IPAddress[m], 'AreaID', OSPF_AreaID[m], 'system', tp_created_date);
            #inValue=('ROSPFV2', s_device_id , s_hostname, s_mgmtip, '', '', '', 'AreaID', ROSPF[m][1], 0, '', '', '', '', ROSPF[m][0], 'AreaID', ROSPF[m][1], 'system', tp_created_date);
            logical_topo_data.append(inValue)
           
        """ Refresh Logical Topology 
                Step 1 : Delete existing logical topology from Logical Topology Link Table
                Step 2  : Insert discovered values in Logical Topology Link Table 
        """
        if sSystem.lower() != 'c3p-ui':  
            #Call to physical topology
            physicalTopologyDataForDB = []
            #1. First call to generate text files after show commands
            #Required JSON Input ::: {"mgmtip":"10.62.0.113","hostname":"csr1000v1","device_id":522,"sourcesystem":"c3p-ui"}
            content['mgmtip']=s_mgmtip
            content['hostname']=str(s_device_id)
            content['device_id']=s_device_id
            content['sourcesystem']=sSystem.lower()
            logger.debug('Input for triggerPhysicalTopology::: %s', content)

            show_cmd_disc_file = phyTopology.triggerPhysicalTopology(content)

            #2. Call to second method to create xml and give output array
            #Required JSON Input:::
            # {
            # "files": [
            #     "D:\\csr1000v_120210723121306.txt",
            #     "D:\\csr1000v_120210723121307.txt",
            #     "D:\\csr1000v_120210723121308.txt"
            # ],
            # "hostname":"csr1000v",
            # "s_device_id":"581308",
            # "s_mgmtip":"10.62.0.113",
            # "created_by":"system"
            # }
            data = {}
            data['hostname'] = str(s_device_id)
            data['s_device_id'] = s_device_id
            data['s_mgmtip'] = s_mgmtip
            data['created_by'] = 'system'
            fileObj=show_cmd_disc_file
            files=[]
            files.append(fileObj)
            data['files'] = files
            logger.debug('Input for createCSV:::%s', data)

            physicalTopologyDataForDB = phyTopology.createCSV(data)
            if(len(physicalTopologyDataForDB)>0):
                for item in physicalTopologyDataForDB:     
                    logical_topo_data.append(item)
            logger.debug('logical_topo_data:::%s', logical_topo_data)
                                   
        eData = 0
        if sSystem.lower() == 'c3p-ui':
            sql = "INSERT INTO c3p_t_topology (t_topology_type, s_device_id, s_hostname, s_mgmtip, s_interface, s_interface_index,s_interface_ip, s_topo_type_name, s_topo_type_id, t_device_id, t_hostname, t_mgmtip,  t_neighbor, t_neighbor_index, t_neighbor_ip, t_topo_type_name, t_topo_type_id, tp_created_by, tp_created_date) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
            try:
                mycursor.executemany(sql, logical_topo_data)
                logger.debug('CLT :: Rows Data %s', logical_topo_data)
                logger.debug('CLT :: Rows inserted %s ', mycursor.rowcount)
                #logger.debug('CLT :: Rows inserted %s ', mycursor.rowcount)
                eData = 'C3P-DR-201'
            except mysql.connector.errors.ProgrammingError as e:
                logger.debug('CLT :: INSERT Error #1 :: %s', e)
                #logger.debug('CLT :: INSERT Error #1 :: %s', e)
                eData = 'C3P-DR-500'
                #return(1)         
            mydb.commit()  
            #Physical topolocy 

        else:           # 23/05/21 : Topology generated for an external system
            
            eData = []
            newHeaders={"Content-type":"application/json","Accept":"application/json"}
            url=configs.get("SNow_C3P_Topology")   # ServiceNow URL for Data loading

            for m in logical_topo_data:
                #eData.append({ "t_topology_type":m[1], "s_device_id":m[2], "s_hostname":m[3], "s_mgmtip":m[4], "s_interface":m[5],"s_interface_index":m[6],    "s_interface_ip":m[7], "s_topo_type_name":m[8], "s_topo_type_id":m[9],"t_device_id":m[10],"t_hostname":m[11],"t_mgmtip":m[12],"t_neighbor":m[13],"t_neighbor_index":m[14],  "t_neighbor_ip":m[15],"t_topo_type_name":m[16],"t_topo_type_id":m[17],"tp_created_by":m[18],"tp_created_date":m[19],"tp_updated_by":m[20],"tp_updated_date":m[21]})
                eData.append({ "t_topology_type":m[0], 
                "s_device_id":m[1], 
                "s_hostname":m[2], 
                "s_mgmtip":m[3], 
                "s_interface":m[4],
                "s_interface_index":m[5],   
                "s_interface_ip":m[6], 
                "s_topo_type_name":m[7],    
                "s_topo_type_id":m[8],
                "t_device_id":m[9],
                "t_hostname":m[10],
                "t_mgmtip":m[11],
                "t_neighbor":m[12],
                "t_neighbor_index":m[13],   
                "t_neighbor_ip":m[14],
                "t_topo_type_name":m[15],
                "t_topo_type_id":m[16],
                "tp_created_by":m[17],
                "tp_created_date":''.join(str(m[18]))
                })
            
            respH =requests.post(url,data=json.dumps(eData), headers=newHeaders, auth=HTTPBasicAuth(configs.get("SNow_C3P_User"), configs.get("SNow_C3P_Password")))
            logger.debug('CLT :: Return JSON to External Application %s %s', sSystem, respH.json())
          
            return(respH.status_code)

    
        if sSystem.lower() != 'c3p-ui':
            return('CLT :: External System Status Code :: ok')
        else:
            logger.debug("eData:::%s",eData)
            return(eData)

    except Exception as err:
        logger.error("CLT :: Exception :: %s",err)
    finally:
        mydb.close
    

def refresh_logical_topology(r_mgmtip, r_sSystem):
    mydb = Connections.create_connection()
    try:    
        mycursor = mydb.cursor(buffered=True)
        if r_sSystem.lower() == 'c3p-ui':
            sql = "SELECT count(*) FROM c3p_t_topology WHERE s_mgmtip = %s"
            params = (r_mgmtip,)
        else:
            logger.debug('RLT :: External Application :: %s', r_sSystem)

        try:
            mycursor.execute(sql, params)
        except mysql.connector.errors.ProgrammingError as e:
            logger.debug('RLT :: Count Check Error :: %s', e)

        if mycursor.rowcount > 0:
            if r_sSystem.lower() == 'c3p-ui':
                sql = "DELETE FROM c3p_t_topology WHERE s_mgmtip = %s"
                params = (r_mgmtip,)
            else:
                logger.debug('RLT :: External Application :: %s', r_sSystem)

            try:
                mycursor.execute(sql, params)
                logger.debug('RLT :: Rows Deleted %s ', mycursor.rowcount)
            except mysql.connector.errors.ProgrammingError as e:
                logger.debug('RLT :: Fetch Error :: %s', e)
                # return(1)
            mydb.commit()
        else:
            logger.debug('RLT :: For new IP :: %s', r_mgmtip)
    except Exception as err:
        logger.debug("RLT :: Exception :: %s", err)
        # logger.error("RLT :: Exception :: %s", err)
    finally:
        mydb.close()
    return '0'

def show_logical_topology(content):
    tData   = {}
    #bData   = []
    dev=[]  # list of device information
    tn      = []    # list of topology names
    oData   = []
    temp_parent = [] #temperorary variable to move child to parent nodes
    temp_child = [] #temperorary variable to move parent to child nodes
    result_list = [] # to store the SQL result
    default_hops = 1
    json_data = ""
    topology_color          = {"RBGP":"#e70000", "ROSPFV2":"#00e700", "ROSPFV3":"#0000e7","VPN-Tunnel":"#a1a1a1", "VPN-VRF":"#b0a643","VPN-IPSec":"#b6f2c0","LINK":"#140056"}
    topology_label          = {"RBGP":"Routing BGP", "ROSPFV2":"Routing OSPF V2", "ROSPFV3":"Routing OSPF V3","VPN-Tunnel":"VPN-Tunnel", "VPN-VRF":"VPN-VRF","VPN-IPSec":"VPN-IPSec","LINK":"LINK"}
    # s_mgmtip    = content['mgmtip']
    # s_hostname  = content['hostname']
    # s_device_id = content['device_id']
    contentRes= {}
    lTopo       = content['topology']
    opr         = content['operation']
    sSystem     = content['sourcesystem']
    devices = content['devices']
    logger.debug('lTopo         ::%s', lTopo)
    logger.debug('opr           ::%s', opr)
    logger.debug('sSystem       ::%s', sSystem)
    mydb = Connections.create_connection()
    try:    
        mycursor = mydb.cursor(buffered=True)

        # fetch no of hops from request payload and handle the error
        try:
            # if nhops is empty in the request_payload n_hops will set to default_hops
            n_hops = default_hops if not content['nhops'] else content['nhops'] 
        except KeyError as e:
            logger.debug('Key Error :: %s', e)
            n_hops = default_hops

        for item in devices:
            logger.debug("item mgmt ip :: %s",item['mgmtip'])
            s_mgmtip    = item['mgmtip']
            s_hostname = item['hostname']
            #s_device_id = item['device_id']
           
            if sSystem.lower() == 'c3p-ui':
                if lTopo == 'ALL':
                    sql = "SELECT t_topology_type, s_hostname, s_mgmtip, t_hostname, t_mgmtip, t_neighbor_ip, s_interface_ip FROM c3p_t_topology WHERE s_mgmtip = %s"
                    params = (s_mgmtip,)
                else:
                    sql = "SELECT t_topology_type, s_hostname, s_mgmtip, t_hostname, t_mgmtip, t_neighbor_ip, s_interface_ip FROM c3p_t_topology WHERE s_mgmtip = %s AND t_topology_type = %s"
                    params = (s_mgmtip, lTopo)
            else:  # 23/05/21: Topology generated for an external system, use table  c3p_t_ext_topology
                logger.debug('CLT :: VLT for External Application %s ', sSystem)

              
            # repeat the loop for n_hops
            for hop_count in range(n_hops):
                logger.debug("hop count :: %s",hop_count)
                try:
                    if (hop_count == 0): #To run the query for 1st time
                        sql = "SELECT t_topology_type, s_hostname, s_mgmtip, t_hostname, t_mgmtip, t_neighbor_ip, s_interface_ip FROM c3p_t_topology WHERE s_hostname = %s AND s_mgmtip = %s"
                        mycursor.execute(sql, (s_hostname, s_mgmtip))
                        results = mycursor.fetchall()
                        logger.debug('CLT :: Rows Fetched %s ', mycursor.rowcount)
                        for child_node in results: # collect the unique child_nodes
                            if child_node[3] in temp_parent:
                                pass
                            else:
                                temp_parent.append(''.join(child_node[3]))               
                        result_list+=results                    
                    
                    elif (lTopo == 'LINK' and hop_count > 0):
                        # This will tranfer the collected child_nodes to parent_nodes so that it can collect next child_nodes 
                        if not temp_parent: 
                            temp_parent = temp_child.copy()
                            temp_child.clear()
                        
                        #To run the above same query for child as parents but with changed s_hostname
                        for each_target in temp_parent: 
                            sql = "SELECT t_topology_type, s_hostname, s_mgmtip, t_hostname, t_mgmtip, t_neighbor_ip, s_interface_ip FROM c3p_t_topology WHERE s_hostname = %s AND t_topology_type = 'LINK'"
                            mycursor.execute(sql, (each_target,))
                            results = mycursor.fetchall()                           
                            # collect the unique child_nodes
                            for child_node in results:  
                                if child_node[3] in temp_child:
                                    pass
                                else:
                                    temp_child.append(''.join(child_node[3]))
                            result_list+=results
                        temp_parent.clear()
                    
                    # run the query for other type of topology
                    else: 
                        mycursor.execute(sql, params)
                        results = mycursor.fetchall()
                        result_list+=results

                except mysql.connector.errors.ProgrammingError as e:
                    print('CLT :: SELECT Error #1 :: %s', e)
                """    
                    List of information fetched from Topology Table 

                    m[0]    : t_topology_type
                    m[1]    : s_hostname
                    m[2]    : s_mgmtip
                    m[3]    : t_hostname
                    m[4]    : t_mgmtip
                    m[5]    : t_interface_ip
                    m[6]    : s_interface_ip
                """
                for child_node in result_list:
                    tn.append(''.join(child_node[0]))
             
                for tItem in set(tn):
                    data    = []
                    uNode   = []
                    lnode   = []
                    dFromInt = ''
                    dToInt = ''
                    for result_item in result_list:
                        #print ('result_item[6]=', result_item[6], '<tItem>',tItem)
                        if result_item[0] == tItem:
                            dFrom = result_item[1]                # Source Host Name
                            #print('m[3] ::',result_item[3],'>',result_item[4], '>', result_item[5])
                            if (result_item[3] != '') or result_item[3].strip() :
                                dTo = result_item[3]
                            elif (result_item[4] != '') or result_item[4].strip():
                                dTo = result_item[4]
                            else:
                                #print('r5 >>>>>>>>>>>>>', result_item[5])
                                dTo = result_item[5]
                            dFromInt = result_item[6]
                            dToInt = dTo
                            #print('********* dFrom=',dFrom,'m[3] ::',result_item[3],'>',result_item[4], '>', result_item[5],'<to>',dTo)
                            data.append({"from":dFrom,"fromInterface":dFromInt,"to":dTo,"toInterface":dToInt})

                            """ Creating node table """
                            lnode.append(dFrom)
                            lnode.append(dTo)
                            """ Node Table formation """
                        
                    for nItem in set(lnode):
                        # uNode.append({"id":nItem,"marker": { "height": 22, "symbol": "url(assets\\imgs\\topology\\L1.png)", "width": 22 }})
                        try:
                            ip = ipaddress.ip_address(nItem)
                            query = "SELECT d_hostname, d_mgmtip, d_type, d_device_family, d_model, d_os, d_os_version, d_vendor, d_vnf_support, c_site_id, d_role FROM c3p_deviceinfo WHERE d_mgmtip = %s"
                            mycursor.execute(query, (ip,))
                            deviceinfo = mycursor.fetchone()
                        except:
                            query = "SELECT d_hostname, d_mgmtip, d_type, d_device_family, d_model, d_os, d_os_version, d_vendor, d_vnf_support, c_site_id, d_role FROM c3p_deviceinfo WHERE d_hostname = %s"
                            mycursor.execute(query, (nItem,))
                            deviceinfo = mycursor.fetchone()

                        if deviceinfo is None:
                            topoinfo = 17 * ["Not available"]
                        else:
                            query = "SELECT c_cust_id, c_cust_name, c_site_id, c_site_name, c_site_region, c_cloudplat_zone FROM c3p_cust_siteinfo WHERE id = %s"
                            mycursor.execute(query, (deviceinfo[9],))
                            custinfo = mycursor.fetchone()
                            topoinfo = (deviceinfo + custinfo) 
                        for x in topoinfo:
                            if x==None:
                                dev.append("Not available")
                            else:    
                                dev.append(x)

                        if not nItem:
                            pass
                        else:
                            if '-e-' in nItem:
                                nurl = "url(assets\\imgs\\topology\\aggregation.png)"
                            elif '-r-' in nItem:
                                nurl = "url(assets\\imgs\\topology\\core.png)"
                            elif '-s-' in nItem:
                                nurl = "url(assets\\imgs\\topology\\switch.png)"
                            elif '-b-' in nItem:
                                nurl = "url(assets\\imgs\\topology\\basement.png)"
                            elif nItem == 'MGMT-Cloud7' or nItem == 'NorthSouth' or nItem =='EastWest':
                                nurl = "url(assets\\imgs\\topology\\network.png)"
                            elif nItem == 'vMME-MGMT':
                                nurl = "url(assets\\imgs\\topology\\other.png)"

                            else:
                                nurl = "url(assets\\imgs\\topology\\other.png)"
                            if dev[0]=="Not available":
                                uNode.append({"id": nItem,"dHostName": dev[0], "marker": {"height": 22, "symbol": nurl,"width": 22}})
                            else:
                                uNode.append({"id": nItem,"dHostName": dev[0],"dMgmtIp": dev[1],"dType": dev[2],"dDeviceFamily": dev[3],"dModel": dev[4],"dOs": dev[5],"dOsVersion": dev[6],"dVendor": dev[7],"dVNFSupport": dev[8],"dRole": dev[10],"cCustId": dev[11],"cCustName": dev[12],"cSiteId": dev[13],"cSiteName": dev[14],"csiteregion": dev[15],"ccloudplatzone": dev[16], "marker": {"height": 22, "symbol": nurl,"width": 22}})
                            dev=[] #clear dev for every iteration
                            
                    #tData={t: { "label":topology_label[t],"color": topology_color[t], "data":data, "nodes":uNode}}
                    #oData.append(tData)
                    #uNode = set(lnode)
                    contentRes[tItem] = { "label":topology_label[tItem],"color": topology_color[tItem], "data":data, "nodes":uNode}
                logger.debug('odata ::>>>>>>>:: %s',oData)
                if not contentRes:
                    contentRes = {"Error":"No data available"}               
                logger.debug('odata ::>>>>>>>:: %s',oData )
                #print('bdata ::*******:: ',lnode, '>>', uNode )                
    
        if sSystem.lower() != 'c3p-ui':
            # eData = []
            return('CLT :: External System Status Code :: ok')
        # else:
        #     print(eData)
        #     return(eData)
    

    except Exception as err:
        logger.error("CLT :: Exception :: %s",err)
    finally:
        mydb.close

       
    return (contentRes)
#Remove below commented code to run this program as independent program
#if __name__ == '__main__':
    # reqData = {
    # "mgmtip": "10.62.0.113",
    # "hostname": "csr1000v4",
    # "device_id": 522,
    # "topology": "ALL",
    # "operation": "RLT",
    # "sourcesystem": "c3p-ui"
    # }
    # create_logical_topology(reqData)