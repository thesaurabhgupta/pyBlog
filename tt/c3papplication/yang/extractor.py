import os
import subprocess
from pathlib import Path
import time
from itertools import islice
import platform
import json
from pymongo import MongoClient
from pprint import pprint
from gridfs import GridFS
from bson import objectid
import json
import os.path
from os import path
from jproperties import Properties
from c3papplication.conf.springConfig import springConfig
import requests
import time
import logging, logging.config

logger = logging.getLogger(__name__)

configs = springConfig().fetch_config()

# client = MongoClient(configs.get("MONGO_URL"))
client = MongoClient(configs.get("mongodb://localhost:27017"))

db = client.c3pdbschema


def setParams(heirarchyArray):
    paramvals = dict()

    return paramvals


def runXMLExtractor(filepath, subdir):
    valueToReturn = ""
    tempFilePathXML = configs.get("TEMP_FILE_XML_PATH")
    print("FILE PASSED", filepath)
    process = subprocess.Popen(
        ['pyang', '-p', subdir, '-f', 'sample-xml-skeleton', '--sample-xml-skeleton-defaults', '-o', tempFilePathXML,
         filepath], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    # process = subprocess.Popen(['pyang', '-p',YANG_MODULE_IMPORTS,'-f','sample-xml-skeleton','--sample-xml-skeleton-defaults','-o',tempFilePathXML+"out.xml",filepath],stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    # process = subprocess.Popen(['pyang', '-p','yang','-f','sample-xml-skeleton','--sample-xml-skeleton-defaults','-o',temppath,filepath],stdin =subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,  universal_newlines=True)
    stdout, stderr = process.communicate()
    time.sleep(5)
    # print("temp file exists::",path.exists(temppath))
    if (path.isfile(tempFilePathXML)):
        with open(tempFilePathXML, 'r') as f:
            valueToReturn = f.read()
    else:
        valueToReturn = ""
    if (path.isfile(tempFilePathXML)):
        os.remove(tempFilePathXML)
    print("Valuetoret", valueToReturn)
    return valueToReturn


def runFeatureExtractor(filepath, filename, tempFilePath):
    # print(filepath)
    valueToReturn = ""
    # process = subprocess.Popen(['pyang', '-f','tree' ,filepath],stdin =subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,  universal_newlines=True)
    process = subprocess.Popen(['pyang', '-f', 'tree', filepath], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               shell=True)

    stdout, stderr = process.communicate()
    valueToReturn = stdout
    # Logic to save feature tree in mongo collection
    print(valueToReturn)

    with open(tempFilePath, "w+") as filee:
        filee.writelines(valueToReturn.decode(encoding='UTF-8'))  # Windows

        # filee.writelines(valueToReturn)

    fs = GridFS(db, "featureTree")
    if (fs.exists(filename=filename)):
        pprint("File exists")
    else:
        with open(tempFilePath, 'rb') as f:
            print(path.isfile(tempFilePath))
            print(os.stat(tempFilePath).st_size)
            yang = fs.put(f, content_type='application/text', filename=filename)
            pprint("TreeView loaded in DB")

    return valueToReturn


def getNumberOfLines(filepath):
    """
    file = open(filepath,"r")
    Counter = 0
    Content = file.read()
    CoList = Content.split("\n")
    for i in CoList:
        if i:
            Counter += 1
    print("This is the number of lines in the file")
    print(Counter)
    return Counter

    """
    with open(filepath, "r") as file:
        counter = 0
        Content = file.read()
        CoList = Content.split("\n")
        for i in CoList:
            if i:
                counter += 1
        print("This is the number of lines in the file")
        print(counter)
        return counter
    file.close()


def readReadme(filepath):
    vendor = ""
    firstLine = ""
    osname = ""
    osversion = ""
    paramvals = dict()
    # print(filepath)
    linuxSeperator = "\\/"
    windowsSeperator = "\\"
    array = []
    arrayLine = []
    if platform.system() == 'Windows':
        array = os.path.abspath(filepath).split(windowsSeperator)
    elif platform.system() == 'Linux':
        array = os.path.abspath(filepath).split(linuxSeperator)

    if not array:
        print("Error in splitting filepath")
    else:
        position = array.index('vendor')
        vendor = array[position + 1]
        # print(vendor)

    if len(vendor) != 0:
        with open(filepath, 'r') as fil:
            firstLine = fil.readline()
        # print(firstLine)
        if vendor in firstLine.lower():
            # print("Vendor present in first line")
            arrayLine = firstLine.lower().split(" ")
            print(arrayLine)
            for index, item in enumerate(arrayLine):
                if vendor in item:
                    arrayLine[index] = vendor
                    # print(word)
            vendorPos = arrayLine.index(vendor)
            osname = arrayLine[vendorPos + 1]
            if osname == 'platforms' or osname == 'all':
                osname = 'ALL'
            if len(arrayLine) > vendorPos + 1:
                osversion = arrayLine[vendorPos + 2]
            else:
                osversion = 'ALL'
            # print(osname)
            # print(osversion)

        else:
            print("Vendor not present in first line")
    else:
        print("Error finding vendor")

    paramvals['vendor'] = vendor.upper().replace("\n", "")
    paramvals['os'] = osname.upper().replace("\n", "")
    paramvals['osversion'] = osversion.upper().replace("\n", "")
    return paramvals


def readPlatformJson(filepath):
    paramvals = dict()
    lines = ""
    vendor = ""
    osname = ""
    osversion = ""
    with open(filepath, 'r') as fil:
        lines = fil.read()
    if len(lines) != 0:
        platform_dict = json.loads(lines)
    else:
        print("File is empty")
    # print(platform_dict)
    paramvals['vendor'] = platform_dict['platforms']['platform'][0]['vendor']
    paramvals['os'] = platform_dict['platforms']['platform'][0]['name']
    paramvals['osversion'] = platform_dict['platforms']['platform'][0]['software-version']

    return paramvals


if __name__ == '__main__':
    base = configs.get("YANG_BASE")
    # base = configs.get("YANG_BASE_LOCAL")
    # tempFilePath=configs.get("TEMP_FILE_PATH_LOCAL")
    tempFilePath = configs.get("TEMP_FILE_PATH")
    # tempFilePathXML=configs.get("TEMP_FILE_PATH_LOCAL")
    tempFilePathXML = configs.get("TEMP_FILE_XML_PATH")
    vendor = ""
    osname = ""
    osversion = ""
    deviceDetails = dict()
    xml = ""
    features = ""
    numberOfLines = 0
    linuxSeperator = "/"
    windowsSeperator = "\\"
    arrayMain = []
    outputjson = dict()
    json_object = {}
    for subdir, dirs, files in os.walk(base):
        for filename in files:
            filepath = subdir + os.sep + filename
            # print("subdir",subdir)
            readme = Path(subdir + os.sep + "Readme.md")
            metadatajson = Path(subdir + os.sep + "platform-metadata.json")
            # print(filepath)
            if (readme.is_file() or metadatajson.is_file()):
                if (readme.is_file()):
                    # print("Readme file exist")
                    # numberOfLines = getNumberOfLines(readme)
                    deviceDetails = readReadme(readme)
                    # print(deviceDetails)
                else:
                    deviceDetails = readPlatformJson(metadatajson)
                    # print(deviceDetails)
            else:
                filepathParent = os.path.dirname(os.path.dirname(filepath))
                # print(filepathParent)
                readme = Path(filepathParent + os.sep + "Readme.md")
                metadatajson = Path(filepathParent + os.sep + "platform-metadata.json")
                # print(metadatajson)
                if (readme.is_file() or metadatajson.is_file()):
                    if (readme.is_file()):
                        # print("Readme file exist")
                        # numberOfLines = getNumberOfLines(readme)
                        deviceDetails = readReadme(readme)
                        # print(deviceDetails)
                    else:
                        print("JSON file exist")
                        deviceDetails = readPlatformJson(metadatajson)
                        # print(deviceDetails)
                else:
                    # print("OS",platform.system())
                    if platform.system() == 'Windows':
                        arrayMain = os.path.abspath(filepath).split(windowsSeperator)
                    elif platform.system() == 'Linux':
                        # print("Inside else")
                        arrayMain = os.path.abspath(filepath).split(linuxSeperator)
                    # print("arraymain",arrayMain)
                    arraysize = len(arrayMain)
                    # print("Array Size ",arraysize)
                    position = arrayMain.index('vendor')
                    vendor = arrayMain[position + 1]
                    if (position + 2 > arraysize):
                        osversion = 'ALL'
                    else:
                        osversion = arrayMain[position + 2]
                    if (position + 4 > arraysize):
                        osname = 'ALL'
                    else:
                        osname = arrayMain[position + 4]
                    deviceDetails['vendor'] = vendor.upper()
                    deviceDetails['os'] = osname.upper()
                    deviceDetails['osversion'] = osversion.upper()
                    # print("File not found")

            if ".yang" in filename:
                fileExists = False
                xml = runXMLExtractor(filepath, subdir)
                # print(xml)
                features = runFeatureExtractor(filepath, filename, tempFilePath)

                # print(features)
                # print(deviceDetails)

                outputjson["deviceDetails"] = deviceDetails
                outputjson["yangData"] = filepath
                outputjson["templateName"] = filename
                outputjson["xml"] = xml
                # outputjson["features"] = features.decode('utf-8')

                # Logic to save in C3P Mongo DB
                fs = GridFS(db, "yang")
                if (fs.exists(filename=filename)):
                    pprint("File exists")
                    fileExists = True
                else:
                    with open(filepath, 'rb') as f:
                        yang = fs.put(f, content_type='application/text', filename=filename)
                    pprint("File loaded in DB")

                json_object = json.dumps(outputjson, indent=4)

                print(json_object)
                # print(outputjson)
                # Call python service and send input json to python service
                if (fileExists == False):
                    print("Inside if")
                    resp = requests.post('http://localhost:5000/C3P/api/templateManagment', json=json_object)
                    if resp.status_code != 200:
                        raise Exception('POST /tasks/ {}'.format(resp.status_code))
                        print('Created template')

