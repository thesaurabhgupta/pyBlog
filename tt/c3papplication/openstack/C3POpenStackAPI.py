import requests, json, datetime, time
from flask import request, jsonify
from flask_api import status
from jproperties import Properties
from c3papplication.common import Connections, c3p_lib
from c3papplication.conf.springConfig import springConfig
import logging

configs = springConfig().fetch_config()

""" 
    Author: Anjireddy Reddem
    This class is enabling connection between C3P application and OpenStack Cloud Via various api calls like,
    Alarming, Cloudformation, Compute, Event, Identity, Image, Metric, Network and etc.
"""


class C3POpenStackAPI():

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    """ This method will generates the authentication token, which will be used to connect the OpenStack Apis """

    def openstackAuth(self):
        try:
            url = configs.get("OpenStack_Identify_Service") + '/auth/tokens?nocatalog'
            # print("openstackAuth API url::",url)
            newHeaders = {"Content-Type": "application/json", "Accept": "*/*", "Connection": "keep-alive"}
            body = {}
            body["auth"] = {
                "identity": {
                    "methods": [
                        "password"
                    ],
                    "password": {
                        "user": {
                            "name": configs.get("OpenStack_Identify_User"),
                            "domain": {
                                "name": "Default"
                            },
                            "password": configs.get("OpenStack_Identify_Password")
                        }
                    }
                }
            }
            body_json = json.dumps(body)
            response = requests.post(url, data=body_json, headers=newHeaders)
            self.logger.info("response.status_code: %s", response.status_code)
            if response.status_code == 201:
                self.logger.info("Response: %s", response.json())
                return response.headers['X-Subject-Token']
            elif response.status_code == 401:
                return response.reason
            else:
                return "Unauthorized"
        except Exception as err:
            self.logger.error("Exception: %s", err)
            return "Unauthorized"

    """ This method will fetch the list of images information which are hosted on the OpenStack cloud """

    def fetchImages(self):
        token = self.openstackAuth()
        if token == 'Unauthorized':
            return jsonify({"Error": "Service is unauthorized"}), status.HTTP_401_UNAUTHORIZED
        else:
            url = configs.get("OpenStack_Image_Service") + '/images'
            newHeaders = {"Content-Type": "application/json", "Accept": "*/*", "Connection": "keep-alive",
                          "X-Auth-Token": token}
            body = {}
            body_json = json.dumps(body)
            # print("bodyjson::",body_json)
            response = requests.get(url, data=body_json, headers=newHeaders)
            self.logger.info("Response status_code:: %s", response.status_code)
            if response.status_code == 200:
                self.logger.info("OpenStack Response:: %s", response.json())
                response = self.prepareImageObj(response.json())
                return jsonify(response), status.HTTP_200_OK
            elif response.status_code == 401:
                return jsonify({"Error": "Service is unauthorized"}), status.HTTP_401_UNAUTHORIZED
            else:
                return jsonify({"Error": response.reason}), status.HTTP_400_BAD_REQUEST

    """ This method will fetch the flavors information which are available in the OpenStack cloud """

    def fetchFlavors(self):
        token = self.openstackAuth()
        self.logger.info('token:%s', token)
        if token == 'Unauthorized':
            return jsonify({"Error": "Service is unauthorized"}), status.HTTP_401_UNAUTHORIZED
        else:
            url = configs.get("OpenStack_Compute_Service_V2.1") + '/flavors/detail'
            newHeaders = {"Content-Type": "application/json", "Accept": "*/*", "Connection": "keep-alive",
                          "X-Auth-Token": token}
            body = {}
            body_json = json.dumps(body)
            self.logger.info("bodyjson:: %s", body_json)
            apiResponse = requests.get(url, data=body_json, headers=newHeaders)
            self.logger.info("Response status_code:: %s", apiResponse.status_code)
            if apiResponse.status_code == 200:
                self.logger.info("OpenStack Response:: %s", apiResponse.json())
                response = self.prepareFlavorObj(apiResponse.json())
                return jsonify(response), status.HTTP_200_OK
            elif apiResponse.status_code == 401:
                return jsonify({"Error": "Service is unauthorized"}), status.HTTP_401_UNAUTHORIZED
            else:
                return jsonify({"Error": apiResponse.reason}), status.HTTP_400_BAD_REQUEST

    """ This method can be used for creating a new flavor in the OpenStack cloud """

    def createFlavor(self):
        requestbody = request.json
        self.logger.info("Request Body:: %s", requestbody)
        token = self.openstackAuth()
        if token == 'Unauthorized':
            return jsonify({"Error": "Service is unauthorized"}), status.HTTP_401_UNAUTHORIZED
        else:
            url = configs.get("OpenStack_Compute_Service_V2") + '/flavors'
            newHeaders = {"Content-Type": "application/json", "Accept": "*/*", "Connection": "keep-alive",
                          "X-Auth-Token": token}
            body = {}
            body["flavor"] = requestbody
            body_json = json.dumps(body)
            self.logger.info("bodyjson:: %s", body_json)
            response = requests.post(url, data=body_json, headers=newHeaders)
            self.logger.info("Response status_code::", response.status_code)
            if response.status_code == 200:
                self.logger.info("Response: %s", response.json())
                return jsonify(response.json()), status.HTTP_200_OK
            elif response.status_code == 401:
                return jsonify({"Error": "Service is unauthorized"}), status.HTTP_401_UNAUTHORIZED
            else:
                return jsonify({"Error": response.reason}), status.HTTP_400_BAD_REQUEST

    """ This method will fetch the list of server/instances which are hosted on the OpenStack cloud """

    def fetchServers(self):
        token = self.openstackAuth()
        if token == 'Unauthorized':
            return jsonify({"Error": "Service is unauthorized"}), status.HTTP_401_UNAUTHORIZED
        else:
            url = configs.get("OpenStack_Compute_Service_V2.1") + '/servers'
            newHeaders = {"Content-Type": "application/json", "Accept": "*/*", "Connection": "keep-alive",
                          "X-Auth-Token": token}
            response = requests.get(url, data=json.dumps({}), headers=newHeaders)
            self.logger.info("Response status_code:: %s", response.status_code)
            if response.status_code == 200:
                self.logger.info("Response: %s", response.json())
                return jsonify(response.json()), status.HTTP_200_OK
            elif response.status_code == 401:
                return jsonify({"Error": "Service is unauthorized"}), status.HTTP_401_UNAUTHORIZED
            else:
                return jsonify({"Error": response.reason}), status.HTTP_400_BAD_REQUEST

    """ This method will fetch the server details which is hosted on the OpenStack cloud """

    def fetchServerDetails(self, serverId):
        token = self.openstackAuth()
        if token == 'Unauthorized':
            return jsonify({"Error": "Service is unauthorized"}), status.HTTP_401_UNAUTHORIZED
        else:
            url = configs.get("OpenStack_Compute_Service_V2.1") + '/servers/' + serverId
            newHeaders = {"Content-Type": "application/json", "Accept": "*/*", "Connection": "keep-alive",
                          "X-Auth-Token": token}
            response = requests.get(url, data=json.dumps({}), headers=newHeaders)
            self.logger.info("Response status_code:: %s", response.status_code)
            if response.status_code == 200:
                self.logger.info("Response:: %s", response.json())
                return jsonify(response.json()), status.HTTP_200_OK
            elif response.status_code == 401:
                return jsonify({"Error": "Service is unauthorized"}), status.HTTP_401_UNAUTHORIZED
            else:
                return jsonify({"Error": response.reason}), status.HTTP_400_BAD_REQUEST

    """ This method will fetch the list of available zones which are hosted on the OpenStack cloud """

    def fetchOSZones(self):
        token = self.openstackAuth()
        if token == 'Unauthorized':
            return jsonify({"Error": "Service is unauthorized"}), status.HTTP_401_UNAUTHORIZED
        else:
            url = configs.get("OpenStack_Compute_Service_V2.1") + '/os-availability-zone'
            newHeaders = {"Content-Type": "application/json", "Accept": "*/*", "Connection": "keep-alive",
                          "X-Auth-Token": token}
            response = requests.get(url, data=json.dumps({}), headers=newHeaders)
            self.logger.info("Response status_code:: %s", response.status_code)
            if response.status_code == 200:
                self.logger.info("Response:: %s", response.json())
                return jsonify(response.json()), status.HTTP_200_OK
            elif response.status_code == 401:
                return jsonify({"Error": "Service is unauthorized"}), status.HTTP_401_UNAUTHORIZED
            else:
                return jsonify({"Error": response.reason}), status.HTTP_403_FORBIDDEN

    """ This method can be used for creating a new VNF or Network functions in the OpenStack cloud """

    def createVNFInstance(self, apibody):
        self.logger.info('Start - createVNFInstance')
        mydb = Connections.create_connection()
        try:
            mycursor = mydb.cursor(buffered=True)
            requestId = apibody['requestId']
            # sql =f"SELECT rc_name,rc_value,rc_device_hostname FROM c3p_resourcecharacteristicshistory where so_request_id = '{requestId}'"
            vals = {}
            mycursor.execute(
                "SELECT rc_name,rc_value,rc_device_hostname FROM c3p_resourcecharacteristicshistory where so_request_id = %s'",
                (requestId,));
            resources = mycursor.fetchall()
            for resource in resources:
                t = resource
                # Setting the host name once when rc_name is zone.
                if t[0] == 'zone':
                    vals['name'] = t[2]

                if t[0] == 'securityGroups':
                    securityGroups = []
                    if t[1].find(',') >= 0:
                        groups = t[1].split(',')
                        for group in groups:
                            securityGroup = {}
                            securityGroup["name"] = group
                            securityGroups.append(securityGroup)
                    else:
                        securityGroup = {}
                        securityGroup["name"] = t[1]
                        securityGroups.append(securityGroup)
                    vals[t[0]] = securityGroups
                else:
                    vals[t[0]] = t[1]

            # print("createVNFInstance vals::",vals)
            self.logger.info("createVNFInstance vals:: %s", vals)
            serviceResp = self.createServer(vals)
            result = self.updateInstantiationDetails(serviceResp, requestId, vals['sourceImage'])
            # print("createVNFInstance workflow_status result::",result)
            self.logger.info("createVNFInstance workflow_status result:: %s", result)
            return jsonify({"workflow_status": result}), status.HTTP_201_CREATED
        except Exception as err:
            self.logger.error("Exception: %s", err)
            return jsonify({"Error": "Error while creating VNF Instance"}), status.HTTP_400_BAD_REQUEST
        finally:
            mydb.close()

    """ This method can be used for creating a new server/instance like VNF, VM and Network functions in the OpenStack cloud """

    def createServer(self, requestbody):
        self.logger.info("createServer - Request Body:: %s", requestbody)
        # tempResp={}
        # server={
        # 'security_groups': [{'name': 'test'}, {'name': 'default'}], 'OS-DCF:diskConfig': 'AUTO', 'id': 'a0d99c63-35bf-44cc-b65c-db74964e829d', 'links': [{'href': 'http://10.207.0.11:8774/v2.1/servers/a0d99c63-35bf-44cc-b65c-db74964e829d', 'rel': 'self'}, {'href': 'http://10.207.0.11:8774/servers/a0d99c63-35bf-44cc-b65c-db74964e829d', 'rel': 'bookmark'}], 'adminPass': '5SKE6EEZv8Js'
        # }
        # tempResp['server']=server

        # return jsonify(tempResp),status.HTTP_202_ACCEPTED
        name = requestbody['name']
        imageRef = requestbody['sourceImage']
        flavorRef = requestbody['flavor']
        zone = requestbody['zone']
        networkId = requestbody['network']
        securityGroups = requestbody['securityGroups']
        token = self.openstackAuth()
        if token == 'Unauthorized':
            return jsonify({"Error": "Service is unauthorized"}), status.HTTP_401_UNAUTHORIZED
        else:
            url = configs.get("OpenStack_Compute_Service_V2.1") + '/servers'
            newHeaders = {"Content-Type": "application/json", "Accept": "*/*", "Connection": "keep-alive",
                          "X-Auth-Token": token}
            body = {}
            networks = []
            networkUuid = {}
            networkUuid["uuid"] = networkId
            networks.append(networkUuid)

            server = {}
            server["name"] = name
            server["imageRef"] = imageRef
            server["flavorRef"] = configs.get("OpenStack_Compute_Service_V2.1") + '/flavors/' + flavorRef
            server["availability_zone"] = zone
            server["OS-DCF:diskConfig"] = "AUTO"
            server["networks"] = networks
            server["security_groups"] = securityGroups

            body["server"] = server
            body_json = json.dumps(body)
            self.logger.info("bodyjson:: %s", body_json)
            response = requests.post(url, data=body_json, headers=newHeaders)
            self.logger.info("Response status_code:: %s", response.status_code)
            if response.status_code == 202:
                self.logger.info("Response:: %s", response.json())
                return jsonify(response.json()), status.HTTP_202_ACCEPTED
            elif response.status_code == 401:
                return jsonify({"Error": "Service is unauthorized"}), status.HTTP_401_UNAUTHORIZED
            elif response.status_code == 403:
                return jsonify({"Error": "Service is forbidden"}), status.HTTP_403_FORBIDDEN
            elif response.status_code == 404:
                return jsonify({"Error": "Service is Not Found"}), status.HTTP_404_NOT_FOUND
            elif response.status_code == 409:
                return jsonify({"Error": "Service is having conflict"}), status.HTTP_409_CONFLICT
            else:
                return jsonify({"Error": response.reason}), status.HTTP_400_BAD_REQUEST

    """ This method will fetch the list of networks which are available on the OpenStack cloud """

    def fetchNetworks(self):
        token = self.openstackAuth()
        if token == 'Unauthorized':
            return jsonify({"Error": "Service is unauthorized"}), status.HTTP_401_UNAUTHORIZED
        else:
            url = configs.get("OpenStack_Network_Service") + '/networks'
            newHeaders = {"Content-Type": "application/json", "Accept": "*/*", "Connection": "keep-alive",
                          "X-Auth-Token": token}
            response = requests.get(url, data=json.dumps({}), headers=newHeaders)
            self.logger.info("Response status_code:: %s", response.status_code)
            if response.status_code == 200:
                self.logger.info("Response:: %s", response.json())
                return jsonify(self.prepareNetworkObj(token, response.json())), status.HTTP_200_OK
            elif response.status_code == 401:
                return jsonify({"Error": "Service is unauthorized"}), status.HTTP_401_UNAUTHORIZED
            elif response.status_code == 403:
                return jsonify({"Error": "User is not having rights to access this service"}), status.HTTP_403_FORBIDDEN
            else:
                return jsonify({"Error": response.reason}), status.HTTP_400_BAD_REQUEST

    """ This method will fetch the list of subnets which are available on the OpenStack cloud """

    def fetchSubnets(self):
        token = self.openstackAuth()
        if token == 'Unauthorized':
            return jsonify({"Error": "Service is unauthorized"}), status.HTTP_401_UNAUTHORIZED
        else:
            url = configs.get("OpenStack_Network_Service") + '/subnets'
            newHeaders = {"Content-Type": "application/json", "Accept": "*/*", "Connection": "keep-alive",
                          "X-Auth-Token": token}
            response = requests.get(url, data=json.dumps({}), headers=newHeaders)
            self.logger.info("Response status_code:: %s", response.status_code)
            if response.status_code == 200:
                self.logger.info("Subnet Response:: %s", response.json())
                return jsonify(response.json()), status.HTTP_200_OK
            elif response.status_code == 401:
                return jsonify({"Error": "Service is unauthorized"}), status.HTTP_401_UNAUTHORIZED
            elif response.status_code == 403:
                return jsonify({"Error": "User is not having rights to access this service"}), status.HTTP_403_FORBIDDEN
            else:
                return jsonify({"Error": response.reason}), status.HTTP_400_BAD_REQUEST

    """ This method will fetch the list of security groups which are available on the OpenStack cloud """

    def fetchSecurityGroups(self):
        token = self.openstackAuth()
        if token == 'Unauthorized':
            return jsonify({"Error": "Service is unauthorized"}), status.HTTP_401_UNAUTHORIZED
        else:
            url = configs.get("OpenStack_Network_Service") + '/security-groups'
            newHeaders = {"Content-Type": "application/json", "Accept": "*/*", "Connection": "keep-alive",
                          "X-Auth-Token": token}
            ## Added extra param to fetch only C3P specific security groups
            project_id = '?project_id=' + configs.get("OpenStack_Identify_ProjectId")
            response = requests.get(url + project_id, data=json.dumps({}), headers=newHeaders)
            self.logger.info("Response status_code:: %s", response.status_code)
            if response.status_code == 200:
                self.logger.info("Response:: %s", response.json())
                # return jsonify(response.json()),status.HTTP_200_OK
                return jsonify(self.prepareSecurityGroups(response.json())), status.HTTP_200_OK
            elif response.status_code == 401:
                return jsonify({"Error": "Service is unauthorized"}), status.HTTP_401_UNAUTHORIZED
            elif response.status_code == 403:
                return jsonify({"Error": "User is not having rights to access this service"}), status.HTTP_403_FORBIDDEN
            else:
                return jsonify({"Error": response.reason}), status.HTTP_400_BAD_REQUEST

    def updateInstantiationDetails(self, serviceResp, requestId, imageRef):
        self.logger.info("updateInstantiationDetails serviceResp:: %s", serviceResp)
        result = False
        try:
            self.logger.info("updateInstantiationDetails serviceResp[0]:: %s", serviceResp[0])
            self.logger.info("updateInstantiationDetails serviceResp[1]:: %s", serviceResp[1])
            # print("updateInstantiationDetails serviceResp 22::",serviceResp[0].json)
            if serviceResp[1] == 202:
                respJson = serviceResp[0].json
                respServer = respJson['server']
                serverId = respServer['id']
                serverAdminPass = respServer['adminPass']
                # Call server fetchServerDetails
                serDetails = {}
                # serDetails=self.fetchServerIP(serverId)
                self.logger.info("updateInstantiationDetails serDetails:: %s", serDetails)
                ipAddress = ''
                if "ipAddress" in serDetails:
                    ipAddress = serDetails['ipAddress']
                macAddress = ''
                if "macAddress" in serDetails:
                    macAddress = serDetails['macAddress']

                # print("updateInstantiationDetails ipAddress::",ipAddress)
                self.logger.info("updateInstantiationDetails ipAddress:: %s", ipAddress)
                # Call Resource history to fecth the device details
                deviceResources = c3p_lib.fetchDeviceInfoResourceHistory(requestId)
                # print("updateInstantiationDetails deviceResources::",deviceResources)
                self.logger.info("updateInstantiationDetails deviceResources:: %s", deviceResources)
                # Call Resource history to fecth the vnf details
                # cloudResources = c3p_lib.fetchCloudResourceHistoryDetails(requestId)
                # print("updateInstantiationDetails cloudResources::",cloudResources)
                imageDetails = c3p_lib.fetchVnfImageDetails('OpenStack', imageRef)
                self.logger.info("updateInstantiationDetails imageDetails:: %s", imageDetails)
                rfo_id = deviceResources['rfo_id']
                dev_id = deviceResources['dev_id']
                category = ''
                if rfo_id != None:
                    category = c3p_lib.findCategoryFromRfOrder(rfo_id)

                site_id = c3p_lib.findCustSiteIdFromRequestInfo(requestId)

                if dev_id != None:
                    sqlValues = (dev_id, deviceResources['dev_name'], imageRef, imageDetails[0],
                                 imageDetails[1], imageDetails[2], imageDetails[3], imageDetails[4],
                                 datetime.datetime.now(), "VNF", imageDetails[5], ipAddress, macAddress, site_id, 1)
                else:
                    sqlValues = (deviceResources['dev_name'], imageRef, imageDetails[0],
                                 imageDetails[1], imageDetails[2], imageDetails[3], imageDetails[4],
                                 datetime.datetime.now(), "VNF", imageDetails[5], ipAddress, macAddress, site_id, 0)
                self.logger.info("updateInstantiationDetails sqlValues:: %s", sqlValues)
                # Insert insertDeviceInfoData
                deviceId = c3p_lib.insertDeviceInfoData(dev_id, sqlValues)
                if deviceId != None:
                    # Insert insertDeviceInfoExtData
                    c3p_lib.insertDeviceInfoExtData(deviceId, category, 'Installing', serverId, serverAdminPass)
                    c3p_lib.updateRequestInfoMgmtIp(requestId, ipAddress)
                    c3p_lib.updateResourceHistoryDeviceId(requestId, deviceId)
                    result = True
            else:
                c3p_lib.updateWebServiceInfo(requestId, serviceResp[0].json['Error'])
                self.logger.info("Response is not supported for  updateInstantiationDetails")
        except Exception as err:
            self.logger.error("Exception in updateInstantiationDetails: %s", err)
        return result

    def fetchServerIP(self, serverId):
        serDetails = dict()
        try:
            # Call server fetchServerDetails
            self.logger.info("fetchServerIP serverId:: %s", serverId)
            serviceResp = self.fetchServerDetails(serverId)
            if serviceResp[1] == 200:
                respJson = serviceResp[0].json
                respServer = respJson['server']
                serverId = respServer['id']
                serverName = respServer['name']
                serverStatus = respServer['status']
                ipAddress = ''
                macAddress = ''
                self.logger.info("Method in fetchServerIP serverStatus: %s", serverStatus)
                # If Server instantiation status is not active then wait for time call the server details to fetch the service Active
                # if serverId !=None and serverStatus != 'ACTIVE':
                # respServer = self.fetchActiveServerDetails(serverId)
                # if 'status' in respServer:
                # serverStatus=respServer['status']

                addresses = respServer['addresses']
                self.logger.info("fetchServerIP addresses:: %s", addresses)
                self.logger.info("fetchServerIP addresses[0]:: %s", addresses.items())
                self.logger.info("fetchServerIP addresses[1]:: %s", addresses.keys())
                addrsKeys = list(addresses.keys())
                if len(addrsKeys) > 0 and len(addresses[addrsKeys[0]]) > 0:
                    ipAddress = addresses[addrsKeys[0]][0]['addr']
                    macAddress = addresses[addrsKeys[0]][0]['OS-EXT-IPS-MAC:mac_addr']
                else:
                    ipAddress = ''
                    macAddress = ''
                self.logger.info("fetchServerIP ipAddress:: %s", ipAddress)
                self.logger.info("fetchServerIP macAddress:: %s", macAddress)
                serDetails['id'] = serverId
                serDetails['name'] = serverName
                serDetails['ipAddress'] = ipAddress
                serDetails['macAddress'] = macAddress
                serDetails['status'] = serverStatus
            else:
                self.logger.info("Response is not supported for  updateInstantiationDetails")
        except Exception as err:
            self.logger.error("Exception in fetchServerIP: %s", err)
        return serDetails

    def fetchActiveServerDetails(self, serverId):
        respServer = {}
        self.logger.info("Method in fetchActiveServerDetails: %s", serverId)
        try:
            # Keep process onhold for a min.
            # print("Method in fetchActiveServerDetails After 1 min delay:")
            # Call the server details and check for status
            serviceResp = self.fetchServerDetails(serverId)
            if serviceResp[1] == 200:
                respJson = serviceResp[0].json
                respServer = respJson['server']
                serverId = respServer['id']
                serverStatus = respServer['status']
                self.logger.info("Method in fetchActiveServerDetails serverStatus: %s", serverStatus)
                if serverId != None and serverStatus != 'ACTIVE':
                    # Keep process onhold for a min.
                    # self.processExecutionSleep(10.0)
                    serviceResp = self.fetchServerDetails(serverId)
                    if serviceResp[1] == 200:
                        respJson = serviceResp[0].json
                        respServer = respJson['server']
                        serverId = respServer['id']
                        serverStatus = respServer['status']
                        if serverId != None and serverStatus != 'ACTIVE':
                            # Keep process onhold for a min.
                            # self.processExecutionSleep(10.0)
                            serviceResp = self.fetchServerDetails(serverId)
                            if serviceResp[1] == 200:
                                respJson = serviceResp[0].json
                                respServer = respJson['server']
        except Exception as err:
            self.logger.error("Exception in fetchActiveServerDetails: %s", err)
        return respServer

    def processExecutionSleep(self, delaySecs: float):
        time.sleep(delaySecs)

    def prepareImageObj(self, apiResponse):
        imagesRes = apiResponse['images']
        images = []
        for imageRes in imagesRes:
            image = {}
            image['id'] = imageRes['id']
            image['name'] = imageRes['name']
            image['checksum'] = imageRes['checksum']
            image['disk_format'] = imageRes['disk_format']
            if 'description' in imageRes:
                image['description'] = imageRes['description']
            else:
                image['description'] = ''
            image['min_disk'] = imageRes['min_disk']
            image['min_ram'] = imageRes['min_ram']
            image['size'] = imageRes['size']
            image['status'] = imageRes['status']
            image['visibility'] = imageRes['visibility']
            images.append(image)

        response = {}
        response["images"] = images
        return response

    def prepareFlavorObj(self, apiResponse):
        flavorsRes = apiResponse['flavors']
        flavors = []
        for flavorRes in flavorsRes:
            flavor = {}
            flavor['id'] = flavorRes['id']
            flavor['name'] = flavorRes['name']
            flavor['disk'] = flavorRes['disk']
            flavor['ram'] = flavorRes['ram']
            flavor['vcpus'] = flavorRes['vcpus']
            flavors.append(flavor)

        response = {}
        response["flavors"] = flavors
        return response

    def prepareNetworkObj(self, token, apiResponse):
        networksRes = apiResponse['networks']
        networks = []
        # Fetch available subnets.
        subnetList = self.fetchSubnetList(token)
        self.logger.info('subnetList: %s', subnetList)
        for networkRes in networksRes:
            network = {}
            subnets = []
            network['id'] = networkRes['id']
            network['name'] = networkRes['name']
            network['availability_zones'] = networkRes['availability_zones']
            network['description'] = networkRes['description']
            network['project_id'] = networkRes['project_id']
            network['network_type'] = networkRes['provider:network_type']
            network['physical_network'] = networkRes['provider:physical_network']
            for subnetId in networkRes['subnets']:
                subnet = {}
                subnet['id'] = subnetId
                subnet['name'] = subnetList.get(subnetId)
                subnets.append(subnet)

            network['subnets'] = subnets
            networks.append(network)

        response = {}
        response["networks"] = networks
        return response

    def fetchSubnetList(self, token):
        subnetDist = {}
        try:
            url = configs.get("OpenStack_Network_Service") + '/subnets'
            newHeaders = {"Content-Type": "application/json", "Accept": "*/*", "Connection": "keep-alive",
                          "X-Auth-Token": token}
            response = requests.get(url, data=json.dumps({}), headers=newHeaders)
            # print("Response status_code::",response.status_code)
            if response.status_code == 200:
                # print("Subnet Response::",response.json())
                subnets = response.json()
                subnetsRes = subnets['subnets']
                for subnetRes in subnetsRes:
                    subnetDist[subnetRes['id']] = subnetRes['name']

            # print("subnetDist::",subnetDist)
            return subnetDist
        except Exception as err:
            self.logger.error("Exception: %s", err)
            return subnetDist

    def prepareSecurityGroups(self, apiResponse):
        groupsRes = apiResponse['security_groups']
        secGrps = []
        for groupRes in groupsRes:
            secGrp = {}
            secGrp['id'] = groupRes['id']
            secGrp['name'] = groupRes['name']
            secGrp['project_id'] = groupRes['project_id']
            secGrp['description'] = groupRes['description']
            secGrps.append(secGrp)

        response = {}
        response["security_groups"] = secGrps
        return response