from flask import Flask, render_template, request
from chatterbot import ChatBot
import requests, json
import logging
from c3papplication.chatbot import trainer
import ipaddress
from jproperties import Properties
from c3papplication.common import Connections, c3p_lib
from c3papplication.conf.springConfig import springConfig
from concurrent.futures import ThreadPoolExecutor
import os

app = Flask(__name__)
logger = logging.getLogger(__name__)

configs = springConfig().fetch_config()

c3p_chatbot = (configs.get("C3P_chatbot")).strip()
C3P_Application = (configs.get("C3P_Application")).strip()
path = (configs.get("path_file")).strip()

reqesturl = C3P_Application + 'c3p-p-core/requestDetails/search/'
pingurl = c3p_chatbot + '/c3p-p-core/api/PingTest/'
framelossurl = c3p_chatbot + '/c3p-p-core/api/frameloss/'
latencyurl = c3p_chatbot + '/c3p-p-core/api/latency/'
throughputurl = c3p_chatbot + '/c3p-p-core/api/throughput/'
tracerouteurl = c3p_chatbot + '/c3p-p-core/api/TraceRoute/'
backupurl = c3p_chatbot + '/c3p-p-core/api/backupRequest'
discoveryurl = c3p_chatbot + '/c3p-p-core/api/ext/discovery/'

trainer.train()


def discoverInfo(mgmtip):
    mydb = Connections.create_connection()
    mycursor = mydb.cursor(buffered=True)

    try:
        mycursor.execute("SELECT d_hostname,d_vendor,c_site_id FROM c3p_deviceinfo  where d_mgmtip='" + mgmtip + "' ")
        data = mycursor.fetchone()
        mycursor.execute("SELECT c_cust_name FROM c3p_cust_siteinfo  where id='" + str(data[2]) + "' ")
        custName = mycursor.fetchone()
        result = "Ip Address:{} HostName:{} Vendor:{} Customer:{}".format(mgmtip, data[0], data[1], custName[0])
    except Exception as err:
        logger.error("Exception in discoverInfo in chatterbot: %s", err)
        result = (" Exception in hostname:%s", err)
    mydb.close
    return (result)


def discoverDetails(address):
    try:
        ip = ipaddress.ip_address(address)  # validate the ip address
        deviceDetails = discoverInfo(str(ip))
        response = deviceDetails + "\n Are device details are correct:[True/False]"

    except Exception as err:
        logger.error("Exception in discoverDetails in chatterbot: %s", err)
        response = "IP address is not valid"
    return response


def discoverRun(address):
    try:
        ip = ipaddress.ip_address(address)  # validate the ip address
        ipdata = '{"discoveryType":"ipSingle","discoveryName":"test","startIp":"input","community":"Public","ipType":"ipv4","endIp":"","netMask":"","sourcesystem":"c3p-ui","createdBy":"admin"} '
        myobj = ipdata.replace("input", str(ip))
        myobj = json.loads(myobj)
        response = requests.post(discoveryurl, json=myobj)
        response = str(response.json())
    except Exception as err:
        logger.error("Exception in discoverRun in chatterbot: %s", err)
        response = "IP address is not valid"
    return response


def getHostName(mgmtip):
    mydb = Connections.create_connection()
    mycursor = mydb.cursor(buffered=True)
    try:
        mycursor.execute("SELECT d_hostname FROM c3p_deviceinfo  where d_mgmtip='" + mgmtip + "' ")
        result = mycursor.fetchone()
    except Exception as err:
        logger.error("Exception in hostname in chatterbot: %s", err)
        result = (" Exception in hostname:%s", err)
    mydb.close
    return (result)


def backup(address):
    try:
        ip = ipaddress.ip_address(address)  # validate the ip address
        ipdata = '{"hostname":"C3PRTR1","managementIp":"input","startup":true,"running":false,"backupType":"run","scheduleDate":"","requestType":"backup"}'
        myobj = ipdata.replace("input", str(ip))
        hostname = getHostName(str(ip))
        response = "Ipaddress:{}, Hostname:{}".format(ip, hostname[0])  # dont remove ':'
        response = str(
            response) + ",Type of backup that needs to be taken:[startup/running]"  # dont remove ',' before Type of backup
    except Exception as err:
        logger.error("Exception in backup in chatterbot: %s", err)
        response = "IP address is not valid"
        myobj = ""
    return response, myobj


def rfStartupRunning(input, ip, hostmane):
    try:
        if input == "startup":
            ipdata = '{"hostname":"hn","managementIp":"input","startup":"true","running":"false","backupType":"run","scheduleDate":"","requestType":"backup"}'
            myobj = ipdata.replace("input", str(ip)).replace("hn", str(hostmane))
            myobj = json.loads(myobj)
            response = requests.post(backupurl, json=myobj)
            response = str(response.json())
            print("startup json response", response)
        if input == "running":
            ipdata = '{"hostname":"hn","managementIp":"input","startup":false,"running":true,"backupType":"run","scheduleDate":"","requestType":"backup"}'
            myobj = ipdata.replace("input", str(ip)).replace("hn", str(hostmane))
            myobj = json.loads(myobj)
            response = requests.post(backupurl, json=myobj)
            response = str(response.json())
    except Exception as err:
        logger.error("Exception in rfStartupRunning in chatterbot: %s", err)
        response = ("Exception in rfStartupRunning in chatterbot: %s", err)
    return response


def throughputTest(address):
    try:
        ip = ipaddress.ip_address(address)  # validate the ip address
        print("ip", ip)
        ipdata = '{"srcMgmtIP":"input","srcMgmtPort":"22","destMgmtIP":"","destMgmtPort":"","packetCount":60,"throughputUnit":"Mbps","bufferSize":1024,"srcApplication":"C3P"}'
        myobj = ipdata.replace("input", str(ip))
        myobj = json.loads(myobj)
        response = requests.post(throughputurl, json=myobj)
        response = str(response.json())
    except Exception as err:
        logger.error("Exception in throughputTest in chatterbot: %s", err)
        response = "IP address is not valid"
    return response


def framelossTest(address):
    try:
        ip = ipaddress.ip_address(address)  # validate the ip address
        ipdata = '{"ipAddress":"input","packetSize":30,"packetCount":10}'
        myobj = ipdata.replace("input", str(ip))
        myobj = json.loads(myobj)
        response = requests.post(framelossurl, json=myobj)
        response = str(response.json())
    except Exception as err:
        logger.error("Exception in framelossTest in chatterbot: %s", err)
        response = "IP address is not valid"
    return response


def pingTest(address):
    try:
        ip = ipaddress.ip_address(address)  # validate the ip address
        ipdata = '{"ipAddress":"input"}'
        myobj = ipdata.replace("input", str(ip))
        myobj = json.loads(myobj)
        print("ping json", myobj)
        response = requests.post(pingurl, json=myobj)
        print("ping res", response)
        response = str(response.json())
    except Exception as err:
        logger.error("Exception in pingTest in chatterbot: %s", err)
        response = "IP address is not valid"
    return response


def tracerouteTest(address):
    try:
        ip = ipaddress.ip_address(address)  # validate the ip address
        ipdata = '{"ipAddress":"input"}'
        myobj = ipdata.replace("input", str(ip))
        myobj = json.loads(myobj)
        response = requests.post(tracerouteurl, json=myobj)
        response = str(response.json())
    except Exception as err:
        logger.error("Exception in tracerouteTest in chatterbot: %s", err)
        response = "IP address is not valid"
    return response


def latencyTest(address):
    try:
        ip = ipaddress.ip_address(address)  # validate the ip address
        print("ip", ip)
        ipdata = '{"ipAddress":"input","packetSize":30,"packetCount":10}'
        myobj = ipdata.replace("input", str(ip))
        myobj = json.loads(myobj)
        response = requests.post(latencyurl, json=myobj)
        response = str(response.json())
    except Exception as err:
        logger.error("Exception in latencyTest in chatterbot: %s", err)
        response = "IP address is not valid"
    return response


def getStatusRequestID(requestid):
    try:
        searchData = '{"key":"Request ID","value":"input","version":"1","notif_id":"","userName":"admin","userRole":"admin"}'
        myobj = searchData.replace("input", str(requestid))
        myobj = json.loads(myobj)
        response = requests.post(reqesturl, json=myobj)
        response = (response.json())
        removeEntity = response.get('entity')
        routput = removeEntity.get('output')
        res = dict(map(str.strip, sub.split(':', 1)) for sub in routput.split(', ') if ':' in sub)
        res = str(res).replace("'", "").replace("[{", "").replace("}]", "")
        res = json.loads(res)
        response = (res.get('status'))
        response = ('Status:', response)
    except Exception as err:
        logger.error("Exception in getStatusRequestID in chatterbot: %s", err)
        response = "Request id {} is not valid".format(requestid)
    return response


def storeData(loginuser, usertext):
    try:
        with open(path + loginuser + '.txt', 'a') as filehandle:
            filehandle.write('%s\n' % usertext)
            logger.debug("entered in to text file to store data:  %s", usertext)
    except Exception as err:
        logger.error("Exception in store data: %s", err)


def readData(loginuser):
    store = []
    try:
        with open(path + loginuser + '.txt', 'r') as filehandle:
            for line in filehandle:
                # remove linebreak which is the last character of the string
                currentPlace = line[:-1]
                # add item to the list
                store.append(currentPlace)
            logger.debug('entered in to text file to read data :: %s', store)
    except Exception as err:
        logger.error("Exception in read data: %s", err)
    return store


def deleteUserFile(loginuser):
    try:
        os.remove(path + loginuser + '.txt')
    except Exception as err:
        logger.error("Exception in deleting file: %s", err)


def executeBot(loginuser, userText):
    bot = ChatBot("C3PBOT",
                  storage_adapter="chatterbot.storage.SQLStorageAdapter",
                  read_only=True,
                  logic_adapters=[
                      {
                          "import_path": "chatterbot.logic.BestMatch",

                      }
                  ]
                  )
    logger.debug('inputtext :: %s', userText)
    storeData(loginuser, userText)
    botdata = (bot.get_response(userText))
    store = readData(loginuser)
    logger.debug('store data :: %s', store)
    try:
        if botdata.confidence > 0.0:
            botText = (str(botdata.text))
            # print(botText)
        elif ("ping" in store):
            response = pingTest(userText.strip())
            if response != "IP address is not valid":
                botText = (str(response))
                deleteUserFile(loginuser)
            if response == "IP address is not valid":
                botdata = (bot.get_response(response))
                botText = (str(botdata.text))
            if ((userText.strip()).lower()) == "yes":
                botText = "Enter a valid IP"
            if ((userText.strip()).lower()) == "no":
                deleteUserFile(loginuser)
                botText = "Have a nice day!"
        elif ("frameloss" in store):
            response = framelossTest(userText.strip())
            if response != "IP address is not valid":
                botText = (str(response))
                deleteUserFile(loginuser)
            if response == "IP address is not valid":
                botdata = (bot.get_response(response))
                botText = (str(botdata.text))
            if ((userText.strip()).lower()) == "yes":
                botText = "Enter a valid IP"
            if ((userText.strip()).lower()) == "no":
                deleteUserFile(loginuser)
                botText = "Have a nice day!"
        elif ("latency" in store):
            response = latencyTest(userText.strip())
            if response != "IP address is not valid":
                botText = (str(response))
                deleteUserFile(loginuser)
            if response == "IP address is not valid":
                botdata = (bot.get_response(response))
                botText = (str(botdata.text))
            if ((userText.strip()).lower()) == "yes":
                botText = "Enter a valid IP"
            if ((userText.strip()).lower()) == "no":
                deleteUserFile(loginuser)
                botText = "Have a nice day!"
        elif ("throughput" in store):
            response = throughputTest(userText.strip())
            if response != "IP address is not valid":
                botText = (str(response))
                deleteUserFile(loginuser)
            if response == "IP address is not valid":
                botdata = (bot.get_response(response))
                botText = (str(botdata.text))
            if ((userText.strip()).lower()) == "yes":
                botText = "Enter a valid IP"
            if ((userText.strip()).lower()) == "no":
                deleteUserFile(loginuser)
                botText = "Have a nice day!"
        elif ("traceroute" in store):
            response = tracerouteTest(userText.strip())
            if response != "IP address is not valid":
                botText = (str(response))
                deleteUserFile(loginuser)
            if response == "IP address is not valid":
                botdata = (bot.get_response(response))
                botText = (str(botdata.text))
            if ((userText.strip()).lower()) == "yes":
                botText = "Enter a valid IP"
            if ((userText.strip()).lower()) == "no":
                deleteUserFile(loginuser)
                botText = "Have a nice day!"
        elif ("backup" in store):
            response = backup(userText.strip())
            print("backup.....", response)
            storeData(loginuser, str(response))
            print("backup.....", store)
            if response != "IP address is not valid":
                botText = (str(response[0]))
                # deleteUserFile(loginuser)
            if response[0] == "IP address is not valid":
                print(response[0])
                botdata = (bot.get_response(response[0]))
                botText = (str(botdata.text))
            if ((userText.strip()).lower()) == "yes":
                botText = "Enter a valid IP"
            if ((userText.strip()).lower()) == "no":
                deleteUserFile(loginuser)
                botText = "Have a nice day!"
            if (("startup" in (userText.strip()).lower()) or ("running" in (userText.strip()).lower())):
                ip = str(store).partition(',')[2].partition(':')[2].partition(',')[0]
                print("ip", ip)
                hostname = str(store).partition(',')[2].partition(':')[2].partition(':')[2].partition(',')[0]
                print("hostname", hostname)
                response = rfStartupRunning((userText.strip()).lower(), ip, hostname)
                # print(str(response))
                deleteUserFile(loginuser)
                botText = (str(response))
        elif ("discovery" in store):
            response = discoverDetails(userText.strip())
            storeData(loginuser, response)
            print("rf.....", store)
            if response != "IP address is not valid":
                botText = (str(response))
            if ((userText.strip()).lower()) == "true":
                ip = str(store).partition(':')[2].partition(' ')[0]
                response = discoverRun(ip)
                botText = (str(response))
                deleteUserFile(loginuser)
            if response == "IP address is not valid":
                botdata = (bot.get_response(response))
                botText = (str(botdata.text))
            if ((userText.strip()).lower()) == "yes":
                botText = "Enter a valid IP"
            if ((userText.strip()).lower()) == "no" or ((userText.strip()).lower()) == "false":
                deleteUserFile(loginuser)
                botText = "Have a nice day!"
        elif ("status" in store):
            response = getStatusRequestID(userText.strip())
            botText = (str(response))
            deleteUserFile(loginuser)
        else:
            logger.debug('store else loop :: %s', store)
            botText = 'I am sorry, but I do not understand.'
            #   store.clear()
    except Exception as err:
        logger.error("Exception in chatbot: %s", err)
    logger.debug('before return :: %s', store)
    return botText


def getbotresponse(userText):
    userdata = (userText.get('message'))
    loginuser = (userText.get('user').get('name'))
    logger.debug('userdata :: %s', userdata)
    logger.debug('loginuser :: %s', loginuser)
    with ThreadPoolExecutor() as executor:
        results = executor.submit(executeBot, loginuser, userdata, )
        # print(results.result())
    response = {
        "user": {
            "name": "Virtual Bot",
            "type": "bot"
        },
        "message": results.result(),
        "created_at": 1638429490691
    }
    data = json.dumps(response)
    logger.debug('ReturnResponse :: %s', data)
    return data