from jproperties import Properties
import json,logging
import openstack
from novaclient import client as novaclient
from cinderclient import client as cinderclient
from c3papplication.conf.springConfig import springConfig
from keystoneauth1 import loading
from keystoneauth1 import session

logger = logging.getLogger(__name__)

configs = springConfig().fetch_config()

def get_creds():
    try:
        creds = {}
        creds['username'] = (configs.get("OpenStack_Identify_User")).strip()
        creds['password'] = (configs.get("OpenStack_Identify_Password")).strip()
        creds['auth_url'] = (configs.get("OpenStack_Identify_Service")).strip()
        creds['project_id'] = (configs.get("OpenStack_Identify_ProjectId")).strip()
        creds['project_domain_name'] = (configs.get("OpenStack_project_domain_name")).strip()
        creds['user_domain_name'] = (configs.get("OpenStack_user_domain_name")).strip()
        logger.debug('openstack::get_creds:: %s',creds)
    except Exception as err:
        logger.error("openstack::get_creds:: %s",err)
    return creds

def cinderConnect():
    try:
        loader = loading.get_plugin_loader('password')
        auth = loader.load_from_options(auth_url=(configs.get("OpenStack_Identify_Service")).strip(),
                                        username=(configs.get("OpenStack_Identify_User")).strip(),
                                        password=(configs.get("OpenStack_Identify_Password")).strip(),
                                        project_id=(configs.get("OpenStack_Identify_ProjectId")).strip(),
                                        user_domain_name=(configs.get("OpenStack_user_domain_name")).strip())
        sess = session.Session(auth=auth)
        cinder = cinderclient.Client("3", session=sess)
    except Exception as err:
       logger.error("openstack::cinderConnect:: %s",err)  
       cinder=err   
    return cinder

def openstackConnect():
    creds=get_creds()
    try:
        openCreds=openstack.connect(**creds)
    except Exception as err:
        logger.error("openstack::openstackConnect:: %s",err)    
    return openCreds

def novaConnect():
    creds=get_creds()
    try:
        novaCreds=novaclient.Client('2', **creds)
    except Exception as err:
        logger.error("openstack::novaConnect:: %s",err)     
    return novaCreds

def create_Port(network_Name,port_Name,subnet_id):     
    conn=openstackConnect()
    try:
        network=conn.network.find_network(network_Name)
        port= conn.network.create_port( network_id=network.id,
                                        name=port_Name,
                                        fixed_ips=[{
                                                    'subnet_id': subnet_id,
                                                    # 'ip_address': ip_address
                                                   }],
                                        port_security_enabled=False,
                                        security_groups=[]
                                        )
        logger.debug('openstack::create_Port :: %s',port)
    except Exception as err:
        logger.error("openstack::create_Port:: %s",err)
    return port

def create_Server(server_name,image,flavour,nic,userdata,zone):
    nova = novaConnect()
    conn=openstackConnect()
    try:
        image = conn.compute.find_image(image)
        flavour = conn.compute.find_flavor(flavour)
        instance=nova.servers.create(server_name,
                                     image=image.id,
                                     flavor=flavour.id,
                                     nics=nic,
                                     userdata=userdata,
                                     config_drive=True,
                                     availability_zone=zone,
                                     security_groups=[]
                                    )
        status = instance.status
        while status == 'BUILD':
            instance = nova.servers.get(instance.id)
            status = instance.status
        logger.debug('openstack::create_Server :: %s',status)
    except Exception as err:
        logger.error("openstack::create_Server :: %s",err)
    return instance

def computeInstanceMcc(parameters):
    mcm=["Base Interconnect","Management Network"]
    csm=["Base Interconnect","East west","Management Network"]
    ssm=["Base Interconnect","East west","Management Network","Gn", "Sx", "Sgi"]
    ports_Id=[]
    nic=[]
    sourceSystem= parameters["sourceSystem"]
    username= parameters["username"]
    userrole= parameters["userrole"]
    servername=parameters["server"]["servername"]
    image=parameters["server"]["image"]
    flavour=parameters["server"]["flavour"]
    userdata=parameters["server"]["userdata"]
    zone=parameters["server"]["zone"]
  
    conn=openstackConnect()
    try:
        if len(parameters["port"]) == 2:
            for seq in mcm:
                logger.debug('openstack::computeInstanceMcc::seq:: %s', seq)
                content=(list(filter(lambda x:x["Port Desc"]==seq,parameters["port"])))
                logger.debug('openstack::computeInstanceMcc::content:: %s', content)
                network=content[0]["network"]
                port_Name=content[0]["port_Name"]
                subnet_Id= content[0]["subnet_Id"]
                port_response=create_Port(network_Name=network,port_Name=port_Name,subnet_id=subnet_Id)
                logger.debug('openstack::computeInstanceMcc::port_response:: %s', port_response)
                port=conn.get_port(port_Name)
                ports_Id.append(port.id)
        elif len(parameters["port"]) == 3:
            for seq in ssm:
                content=(list(filter(lambda x:x["Port Desc"]==seq,parameters["port"])))
                network=content[0]["network"]
                port_Name=content[0]["port_Name"]
                subnet_Id= content[0]["subnet_Id"]
                port_response=create_Port(network_Name=network,port_Name=port_Name,subnet_id=subnet_Id)
                logger.debug('openstack::computeInstanceMcc::port_response:: %s', port_response)
                port=conn.get_port(port_Name)
                ports_Id.append(port.id)
        elif len(parameters["port"]) == 6:
            for seq in csm:
                content=(list(filter(lambda x:x["Port Desc"]==seq,parameters["port"])))
                network=content[0]["network"]
                port_Name=content[0]["port_Name"]
                subnet_Id= content[0]["subnet_Id"]
                port_response=create_Port(network_Name=network,port_Name=port_Name,subnet_id=subnet_Id)
                logger.debug('openstack::computeInstanceMcc::port_response:: %s', port_response)
                port=conn.get_port(port_Name)
                ports_Id.append(port.id)
        logger.debug('openstack::computeInstanceMcc::PortIDs:: %s',ports_Id)
        for x in range (len(ports_Id)):
            nic.append({'port-id': ports_Id[x]})
        instance=create_Server(servername,image,flavour,nic,userdata,zone)
        res={"Status":instance.status,"address":instance.addresses}
       
    except Exception as err:
        logger.error("openstack::computeInstanceMcc:: %s",err)
        res={"Status": "Failure"}
    logger.debug('openstack::computeInstanceMcc::status:: %s',res)    
    return res

def volumeResize(content):
    conn=openstackConnect()
    cinder=cinderConnect()
    instance=content["instance"]
    feature=content["features"]
    for k in feature:
        if k["key"]=="diskSize":
            diskSize=k["value"]
    try:
        server=conn.get_server(instance)
        instanceId=server.id
        logger.debug('openstack::c3p_compute::volumeResize::instanceId %s', instanceId)
        VolumeId=server.volumes[0]["id"]
        cinder.volumes.detach(VolumeId, VolumeId)
        cinder.volumes.reset_state(VolumeId, 'Available', attach_status='detached')
        cinder.volumes.extend(VolumeId,diskSize)
        cinder.volumes.attach(instance_uuid=instanceId,volume=VolumeId, mountpoint="/dev/vdb",host_name=instance,mode='rw')
        response = conn.get_volume(VolumeId)
        # response={"size":response["size"],"instance":response["attachments"][0]["host_name"],"status":response["status"]}
        if response["status"]=="in-use":
            response={"status" : "success", "error" : "",}
    except Exception as err:
        logger.error("openstack::c3p_compute::volumeResize :: %s",err)
        response={"error": "Error fetching volume size","status":"failure"}
    finally:
            cinder.volumes.attach(instance_uuid=instanceId,volume=VolumeId, mountpoint="/dev/vdb",host_name=instance,mode='rw')
    return response

def resizeFlavor(content):
    conn=openstackConnect()
    nova=novaConnect()
    instance=content["instance"]
    feature=content["features"]
    for k in feature:
        if k["key"]=="flavor":
            flavor=k["value"]
    try:
        server=conn.get_server(instance)
        instanceId=server.id
        logger.debug('openstack::c3p_compute::resizeFlavo::instanceId %s', instanceId)
        flav=conn.compute.find_flavor(flavor)
        flavId=flav.id
        nova.servers.resize(instanceId,flavId)
        server=conn.get_server(instance)
        status=server.status
        while status == "RESIZE":
            server=conn.get_server(instance)
            status=server.status
        response=nova.servers.confirm_resize(instanceId)
        response=conn.get_server(instance)
        # response={"flavor":response["flavor"]["original_name"],"instance":response["name"],"status":response["vm_state"]}
        if response["vm_state"]=="resized":
            response={"status" : "success", "error" : "",}
    except Exception as err:
        logger.error("openstack::c3p_compute::resizeFlavor :: %s",err)
        response={"error": "Error resizing Flavor", "status":"failure"}
    return response 