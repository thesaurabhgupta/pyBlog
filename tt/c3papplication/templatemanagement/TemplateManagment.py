import logging
import datetime
from c3papplication.common import Connections
from c3papplication.conf.springConfig import springConfig
import requests,json
from jproperties import Properties

from c3papplication.templatemanagement.CommandDeatilsVO import CommandDetails
from c3papplication.templatemanagement.FeatureDetailsVO import FeatureDetails
from c3papplication.templatemanagement.DeviceDetailsVO import DeviceDetails


""" 
    Author: Dhanshri Mane
    This class Save VNF Template Feature ,Attribute and Command using Yang Files and Xml Command
"""


class TemplateManagment:
    global parent_id
    global p_id
    global configs

    def __init__(self):
        self.logger = logging.getLogger(__name__)
      
        self.configs = springConfig().fetch_config()


    '''Extract Request Json and assign xml  commad to CommandDetails and 
            featch treeview and YangFile in yangExtractor'''

    def templateManagmentDatatoDB(self, jsonData):
        self.parent_id = ""
        self.p_id = ""
        msg = ''
        try:
            data = json.loads(jsonData)
            #data = jsonData
            self.logger.debug("templateManagmentDatatoDB - data - %s", data)
            fileName = data['templateName']
            self.logger.debug("templateManagmentDatatoDB - fileName - %s", fileName)
            template_id = fileName.replace(".yang", "")
            jsonValue = {"filename": fileName}
            self.logger.debug("templateManagmentDatatoDB - jsonValue - %s", jsonValue)
            xmlValue = self.setXmlDetails(data['xml'])
            treeData = requests.post(self.configs.get("Python_Application") + '/c3p-p-core/api/yang/treeview',
                                     json=jsonValue)
            treeData = treeData.json()
            self.logger.debug("templateManagmentDatatoDB - treeData - %s", treeData)
            treeData = treeData.get("featureTree").replace("\r", "")
            treeValue = treeData.split("\n")
            yangData = requests.post(self.configs.get("Python_Application") + '/c3p-p-core/api/yang', json=jsonValue)
            # yangData = extractor.getYang(jsonValue)
            yangData = yangData.json()
            self.logger.debug("templateManagmentDatatoDB - yangData - %s", yangData)
            yangData = yangData.get("yangFile").replace("\r", "")
            created_date = self.getCurrentDate()
            feature_id = None
            tag_id = None
            userName = "admin"
            commands = self.assignCommandData(xmlValue, created_date, userName, template_id)
            deviceDeatils = self.setDeviceDeatils(data['deviceDetails'])
            featureDataValue = self.setFeatureDeviceDeatils(deviceDeatils, created_date, userName)
            self.logger.debug("templateManagmentDatatoDB - featureDataValue - %s", featureDataValue)
            commandsData = []
            valueXML = []
            setTagCount = 0
            for data in treeValue:
                dataValue = ""
                for command in xmlValue:
                    if ("+--rw" in data):
                        dataValue = data.split("+--rw", 1)[1].strip()
                        if ("xmlns" in command and dataValue in command):
                            commandsData, valueXML = self.setRwXMlCommand(yangData, featureDataValue, command,
                                                                          dataValue, template_id, xmlValue, commands)
                            break
                        else:
                            dataValue = dataValue.split(" ", 1)[0].strip()
                            commandsData = self.recurrsiveCall(valueXML, yangData, commandsData, featureDataValue,
                                                               command, dataValue, template_id)
                    elif ("+--ro" in data):
                        dataValue = data.replace('+--ro', '').strip()
                        commands, setTagCount = self.setTagData(featureDataValue, dataValue, command, xmlValue,
                                                                commands, template_id)
                        if (setTagCount == 1):
                            break
                    else:
                        break
                if (setTagCount == 1):
                    break

            self.saveMasterCommands(commands)
            self.assignAttribData(commandsData, yangData, treeValue, userName, created_date)
            self.saveBasicTemplateDetails(deviceDeatils, template_id, userName, created_date)
            self.saveTemplateTreeStructure(deviceDeatils, fileName)
            msg = "Template Created SuccessFully"
        except Exception as e:
            self.logger.error("templateManagmentDatatoDB - Exception - %s", e)
            msg = "Template Not Created SuccessFully"

        self.logger.error("templateManagmentDatatoDB - msg - %s", msg)
        return {"msg": msg}

    # Get configurable (rw in tree view)xml commands
    def setRwXMlCommand(self, yangData, featureDataValue, command, dataValue, template_id, xmlValue, commands):
        commandValue = command.partition('xmlns')
        cmd = commandValue[0].replace("<", "").replace(">", "").strip()
        start_index = xmlValue.index(command)
        end_index = xmlValue.index("</" + cmd + ">")
        commandsData = commands[start_index:end_index + 1]
        valueXML = xmlValue[start_index:end_index + 1]
        commandsData = self.recurrsiveCall(valueXML, yangData, commandsData, featureDataValue, command, dataValue,
                                           template_id)
        self.parent_id = featureDataValue.get_f_id()
        return commandsData, valueXML

    def setXmlDetails(self, xmlData):
        xmlValue = xmlData.split("\n")
        xmlValue = [s.strip() for s in xmlValue]
        xmlValue.remove(xmlValue[0])
        xmlValue.remove(xmlValue[0])
        xmlValue.pop()
        return xmlValue

    def getCurrentDate(self):
        created_date = str(datetime.datetime.now())
        created_date = created_date.split(".")
        created_date = created_date[0]
        return created_date

    # Set Tag Id to Feature
    def setTagData(self, featureDataValue, dataValue, command, xmlValue, commands, template_id):
        tag_id = 'T'
        featureDataValue.set_f_id(tag_id)
        featureDataValue.set_f_name(dataValue)
        featureDataValue.set_f_replicationind(0)
        featureDataValue.set_f_parent_id(None)
        start_index = 0
        end_index = 0
        setTagCount = 0
        featureFalg = False
        if ("xmlns" in command and dataValue in command):
            commandData = command.partition('xmlns')
            start_index = xmlValue.index(command)
            end_index = xmlValue.index((commandData[0].replace('<', '</')).rstrip() + ">")
            featureFalg = True
        elif (dataValue in command):
            start_index = xmlValue.index(command)
            end_index = xmlValue.index(command.replace('<', '</').rstrip())
            featureFalg = True
        if (featureFalg == True):
            featureDataValue = self.saveMasterFeatures(featureDataValue, template_id)
            comandList = commands[start_index:end_index + 1]
            comandList = self.assignFIdToCmd(featureDataValue, comandList)
            commands = self.changeCmdFID(commands, comandList, start_index, end_index)
            setTagCount = setTagCount + 1

        return commands, setTagCount

    # Check Conatiner and List in Yang and assign parentId to Feature
    # Check If Continer has leaf or not if leaf present then assig
    def recurrsiveCall(self, xmlValue, yangData, commands, featureDataValue, command, dataValue, template_id):
        dataCmd = ""
        if ("xmlns" in command):
            dataCmd = command
            commandValue = command.partition('xmlns')
            command = commandValue[0]

        if ("/>" not in command and "</" not in command):
            command = command.replace("<", "").replace(">", "").strip()
            if ("*" not in dataValue and command == dataValue):
                featureFlag = False
                tagFalse = False
                featureName = "container " + command
                if (featureName in yangData):
                    if ("xmlns" in dataCmd):
                        start_index = xmlValue.index(dataCmd)
                    else:
                        start_index = xmlValue.index("<" + command + ">")
                    end_index = xmlValue.index("</" + command + ">")
                    if (xmlValue.count("<" + command + ">") == 1 or "xmlns" in dataCmd):
                        comandList = commands[start_index:end_index + 1]
                        count = 0
                        for cmddata in comandList:
                            #if ("xmlns" in cmddata.get_cmd_value() and command in cmddata.get_cmd_value()):
                               # data = "<" + command + ">"
                               # cmddata.set_cmd_value(data)

                            if (cmddata.get_cmd_value() != ("<" + command + ">")):
                                if ('/>' in cmddata.get_cmd_value() and count == 0):
                                    cmd = cmddata.get_cmd_value().replace('<', '').replace('/>', '').strip()
                                    if (('leaf ' + cmd) in yangData):
                                        featureFlag = True
                                        tagFalse = False
                                        featureDataValue.set_f_id("F")
                                        featureDataValue.set_f_name(command)
                                        featureDataValue.set_f_replicationind(0)
                                        if (self.parent_id != "" and self.p_id != ""):
                                            if (self.parent_id == comandList[0].get_cmd_master_fid()):
                                                featureDataValue.set_f_parent_id(self.parent_id)
                                            elif (self.p_id == comandList[0].get_cmd_master_fid()):
                                                featureDataValue.set_f_parent_id(self.p_id)
                                        else:
                                            featureDataValue.set_f_parent_id(None)
                                        featureDataValue = self.saveMasterFeatures(featureDataValue, template_id)
                                        self.p_id = featureDataValue.get_f_id()


                                count = count + 1
                                if (count != 0):
                                    break
                        if (featureFlag == False):
                            featureDataValue.set_f_id("T")
                            featureDataValue.set_f_name(command)
                            featureDataValue.set_f_replicationind(0)
                            if (self.parent_id != "" and self.p_id != ""):
                                if (self.parent_id == comandList[0].get_cmd_master_fid()):
                                    featureDataValue.set_f_parent_id(self.parent_id)
                                elif (self.p_id == comandList[0].get_cmd_master_fid()):
                                    featureDataValue.set_f_parent_id(self.p_id)
                            else:
                                featureDataValue.set_f_parent_id(None)
                            if (self.parent_id != ""):
                                id = self.parent_id.replace("T", "")
                                idValue = int(id)
                                value = idValue + 1
                                valueId = "T" + str(value)
                                if (comandList[0].get_cmd_master_fid() == valueId):
                                    self.parent_id = valueId

                            featureDataValue = self.saveMasterFeatures(featureDataValue, template_id)
                            self.p_id = featureDataValue.get_f_id()
                            tagFalse = True
                        if (featureFlag == True or tagFalse == True):
                            comandList = self.assignFIdToCmd(featureDataValue, comandList)
                        commands = self.changeCmdFID(commands, comandList, start_index, end_index)
            elif ("*" in dataValue and command + "*" == dataValue):
                value = "leaf-list " + command
                if (value in yangData):
                    pass
                else:
                    featureName = "list " + command
                    if (featureName in yangData):
                        #self.logger.debug("featureName ID %s", featureName)
                        if (xmlValue.count("<" + command + ">") == 1):
                            start_index = xmlValue.index("<" + command + ">")
                            end_index = xmlValue.index("</" + command + ">")
                            comandList = commands[start_index:end_index + 1]
                            featureDataValue.set_f_id("F")
                            featureDataValue.set_f_name(command)
                            featureDataValue.set_f_replicationind(1)
                            if (self.parent_id == comandList[0].get_cmd_master_fid()):
                                featureDataValue.set_f_parent_id(self.parent_id)
                            elif (self.p_id == comandList[0].get_cmd_master_fid()):
                                featureDataValue.set_f_parent_id(self.p_id)

                            featureDataValue = self.saveMasterFeatures(featureDataValue, template_id)
                            self.p_id = featureDataValue.get_f_id()

                            comandList = self.assignFIdToCmd(featureDataValue, comandList)
                            commands = self.changeCmdFID(commands, comandList, start_index, end_index)

        return commands


    # Assign Sequence Id and Basic Details to Command
    def assignCommandData(self, xmlValue, createdDate, createdBy, templateid):
        commandList = []
        squence_id = 1
        for command in xmlValue:
            comandData = CommandDetails()
            comandData.set_cmd_seq_id(squence_id)
            comandData.set_cmd_value(command)
            comandData.set_cmd_created_date(createdDate)
            comandData.set_cmd_command_created_by(createdBy)
            comandData.set_cmd_checked(0)
            comandData.set_cmd_template_id(templateid)
            squence_id = squence_id + 1
            commandList.append(comandData)
        return commandList

    def changeCmdFID(self, commands, commandList, start_index, end_index):
        count = 0
        for cmd in commands:
            if (count >= start_index and count <= (end_index + 1)):
                for cmdData in commandList:
                    if (cmd.get_cmd_value() == cmdData.get_cmd_value()):
                        cmd.set_cmd_master_fid(cmdData.get_cmd_master_fid())

            count = count + 1
        return commands

    # Assign Basic Deatils to Feature
    def setDeviceDeatils(self, deviceDeatils):
        deviceData = DeviceDetails()
        deviceData.set_vendor(deviceDeatils["vendor"])
        deviceData.set_family("All")
        deviceData.set_os(deviceDeatils["os"])
        deviceData.set_osversion(deviceDeatils["osversion"])
        deviceData.set_region("All")
        deviceData.set_networktype("VNF")
        return deviceData

    # Assign Basic Deatils to Feature
    def setFeatureDeviceDeatils(self, deviceDeatils, creadedDate, createdBy):
        featureDataValue = FeatureDetails()
        featureDataValue.set_f_version('1.0')
        featureDataValue.set_f_vendor(deviceDeatils.get_vendor())
        featureDataValue.set_f_family(deviceDeatils.get_family())
        featureDataValue.set_f_os(deviceDeatils.get_os())
        featureDataValue.set_f_osversion(deviceDeatils.get_osversion())
        featureDataValue.set_f_networkfun(deviceDeatils.get_networktype())
        featureDataValue.set_f_region(deviceDeatils.get_region())
        featureDataValue.set_f_created_by(createdBy)
        featureDataValue.set_f_created_date(creadedDate)
        return featureDataValue

    def assignFIdToCmd(self, featureDataValue, comandList):
        for cmd in comandList:
            cmd.set_cmd_master_fid(featureDataValue.get_f_id())
        return comandList

    # Save Feature Details in c3p_m_features Table
    def saveMasterFeatures(self, featureDataValue, templatId):
        mydb = Connections.create_connection()
        try:
            fName = templatId + "::" + featureDataValue.get_f_name()
            self.logger.debug("featureId",fName)
            dataCheck = self.getFeatureId(fName, featureDataValue.get_f_created_date(), mydb)
            if (dataCheck == None):
                mycursor = mydb.cursor(buffered=True)
                insert_query = "insert into c3p_m_features(f_name,f_replicationind,f_version,f_vendor,f_family,f_os," \
                               "f_osversion,f_networkfun,f_created_by,f_region,f_created_date,f_parent_id)" \
                               " Values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"

                val = (fName, featureDataValue.get_f_replicationind(),
                       featureDataValue.get_f_version(), featureDataValue.get_f_vendor(),
                       featureDataValue.get_f_family(), featureDataValue.get_f_os(),
                       featureDataValue.get_f_osversion(), featureDataValue.get_f_networkfun(),
                       featureDataValue.get_f_created_by(), featureDataValue.get_f_region(),
                       featureDataValue.get_f_created_date(), featureDataValue.get_f_parent_id()
                       )
                mycursor.execute(insert_query, val)
                f_id = self.getFeatureId(fName, featureDataValue.get_f_created_date(), mydb)
                featureDataValue.set_f_row_id(f_id[0])
                featureDataValue.set_f_id(featureDataValue.get_f_id() + str(featureDataValue.get_f_row_id()))
                self.logger.debug("saveMasterFeatures - featureDataValue.get_f_id - %s", featureDataValue.get_f_id())
                mycursor.execute(
                    "update  c3p_m_features set f_id ='" + featureDataValue.get_f_id() + "' where f_rowid = '" + str(
                        featureDataValue.get_f_row_id()) + "'")
                mydb.commit()
            else:
                featureDataValue.set_f_id(dataCheck[1])

        except Exception as err:
            mydb.rollback()
            self.logger.error("saveMasterFeatures - Exception - %s", err)

        finally:
            mydb.close()

        return featureDataValue

    def getFeatureId(self, fName, createdDate, mydb):
        mycursor = mydb.cursor(buffered=True)
        dataCheck = None
        try:
            get_query = "select *  from c3p_m_features where f_name =%s and f_created_date =%s;"
            mycursor.execute(get_query, (fName, createdDate,))
            dataCheck = mycursor.fetchone()
        except Exception as err:
            self.logger.error("getFeatureId - Exception - %s", err)
        return dataCheck

    # Insert Command with FeatureId
    def saveMasterCommands(self, comandList):        
        mydb = Connections.create_connection()
        mycursor = mydb.cursor(buffered=True)
        try:
            self.logger.debug("saveMasterCommands - Command insertion started")
            for command in comandList:
                query = "insert into c3p_template_master_command_list (command_value,command_sequence_id,command_type," \
                        "master_f_id,command_created_by,command_created_date,checked) values(%s,%s,%s,%s,%s,%s,%s);"
                val = (command.get_cmd_value(), command.get_cmd_seq_id(), command.get_cmd_template_id(),
                       command.get_cmd_master_fid(), command.get_cmd_command_created_by(),
                       command.get_cmd_created_date(), command.get_cmd_checked()
                       )
                mycursor.execute(query, val)
                mydb.commit()
            self.logger.debug("saveMasterCommands - Command inserted SuccessFully")
        except Exception as msg:
            mydb.rollback()
            self.logger.debug("saveMasterCommands - Command Data not inserted SuccessFully")
            self.logger.error("saveMasterCommands - Error- %s", msg)
        finally:
            mydb.close()

    # Save Template Basic Details in templateconfig_basic_details Table
    def saveBasicTemplateDetails(self, deviceDeatils, template_id, userName, created_date):
        mydb = Connections.create_connection()
        mycursor = mydb.cursor(buffered=True)
        try:
            query = "insert into templateconfig_basic_details (temp_id,temp_vendor,temp_device_family,temp_device_os," \
                    "temp_os_version,temp_region,temp_created_date,temp_version,temp_parent_version,temp_created_by," \
                    "temp_network_type,temp_alias) values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
            val = (template_id, deviceDeatils.get_vendor(), deviceDeatils.get_family(), deviceDeatils.get_os(),
                   deviceDeatils.get_osversion(), deviceDeatils.get_region(), created_date, "1.0", "1.0", userName,
                   deviceDeatils.get_networktype(), template_id)
            mycursor.execute(query, val)
            mydb.commit()
            self.logger.debug("saveBasicTemplateDetails -Template Data inserted SuccessFully")
        except Exception as msg:
            mydb.rollback()
            self.logger.debug("saveBasicTemplateDetails -Template Data not inserted SuccessFully")
            self.logger.error("saveBasicTemplateDetails - Error- %s", msg)
        finally:
            mydb.close()

    # Check xml Command is leaf or leaf-list in Yang then assign attrib data
    def assignAttribData(self, commands, yangData, treeValue, userName, created_date):
        yangValue = yangData.split("\n")
        yangValue = [s.strip() for s in yangValue]
        mydb = Connections.create_connection()
        key = 0
        keyName = ""
        keyFId = ""
        try:
            for cmd in commands:
                if ("xmlns" not in cmd.get_cmd_value() and "</" not in cmd.get_cmd_value()):
                    cmdVal = None
                    for tree in treeValue:
                        if ('/>' in cmd.get_cmd_value()):
                            cmdData = cmd.get_cmd_value().replace("<", "").replace("/>", "")
                            if (("+--rw " + cmdData) in tree):
                                if (keyName != "" and keyName in cmdData and keyFId == cmd.get_cmd_master_fid()):
                                    key = 1
                                else:
                                    key = 0
                                if (cmdVal != None and
                                        cmd.get_cmd_master_fid() == cmdVal.get_cmd_master_fid()):
                                    pass
                                if (("leaf " + cmdData + " {") in yangData):
                                    dataValue = "leaf " + cmdData + " {"
                                    index = yangValue.index(dataValue)
                                    yangValue = self.setAttribData(cmdData, cmd, yangValue, userName, created_date,
                                                                   index, key, mydb)
                                elif (("leaf-list " + cmdData + " {") in yangData):
                                    index = yangValue.index("leaf-list " + cmdData + " {")
                                    yangValue = self.setAttribData(cmdData, cmd, yangValue, userName, created_date,
                                                                   index, key, mydb)
                                else:
                                    # If data not found in yang then search in tree Data
                                    dataValue = tree.split("+--rw", 1)[1].strip()
                                    attrib = dataValue.split(" ")
                                    dataAttrib = dataValue.replace(attrib[0], " ")
                                    dataAttrib = dataAttrib.replace(" ", "")
                                    self.saveCharacteristicsData(dataAttrib, attrib[0], False, None,
                                                                 cmd.get_cmd_master_fid(),
                                                                 0, userName,
                                                                 created_date, mydb)

                        else:
                            cmdData = cmd.get_cmd_value().replace("<", "").replace(">", "")
                            if (("+--rw " + cmdData) in tree):
                                if ("*" in tree):
                                    keyName = tree[tree.find("["):tree.find("]")]
                                    keyName = keyName.replace("[", "").strip()
                                    keyFId = cmd.get_cmd_master_fid()

                                if (("leaf " + cmdData + " {") in yangData):
                                    dataValue = "leaf " + cmdData + " {"
                                    index = yangValue.index(dataValue)
                                    yangValue = self.setAttribData(cmdData, cmd, yangValue, userName, created_date,
                                                                   index, key, mydb)
                                elif (("leaf-list " + cmdData + " {") in yangData):
                                    index = yangValue.index("leaf-list " + cmdData + " {")
                                    yangValue = self.setAttribData(cmdData, cmd, yangValue, userName, created_date,
                                                                   index, key, mydb)



        except Exception as e:
            self.logger.error("assignAttribData - Error- %s", e)
        finally:
            mydb.close

    # extract values from yang file and check dataType and mandatory data.
    def setAttribData(self, cmdData, cmd, yangValue, userName, created_date, index, key, mydb):
        attribName = cmdData
        featureId = cmd.get_cmd_master_fid()
        start_index = 0
        end_index = 0
        list_value = []
        count = 0

        while index < len(yangValue):
            if (count == 1 and list_value == []):
                break
            elif ("{" in yangValue[index]):
                if (len(list_value) == 0 and count == 0):
                    # start_index = index
                    start_index = index
                    count = 1
                list_value.append("{")
            elif ("}" in yangValue[index]):
                if (len(list_value) > 0):
                    end_index = index
                    # end_index = yangValue.index(yangValue[index])
                    list_value.pop()

            index = index + 1
        if (start_index != 0 and end_index != 0):
            dataValue = yangValue[start_index:end_index]
            type = ""
            required = False
            dataList = []
            replication = 0
            for v in dataValue:
                if ("type" in v):
                    type = v.replace("type", "").strip()
                    if ("{" in type):
                        type = type.replace("{", "").strip()
                if ("enum" in v and "type" not in v):
                    data = v.replace("enum", "").replace("{", "").strip()
                    dataList.append(data)
                if ("mandatory" in v):
                    required = True
                if ("leaf-list " in v):
                    replication = 1

            self.saveCharacteristicsData(type, attribName, required, dataList, featureId, replication, userName,
                                         created_date, key, mydb)

        return yangValue

    # Save characteristics data in c3p_m_characteristics table
    def saveCharacteristicsData(self, dataType, attribName, requiredValue, dataList, f_id, replication, userName,
                                createdDate, key, mydb):
        mycursor = mydb.cursor(buffered=True)
        try:
            get_query = "select *  from c3p_m_characteristics where c_name ='" + attribName + "' and c_f_id ='" + \
                        f_id + "';"
            mycursor.execute(get_query)
            dataCheck = mycursor.fetchone()
            if (dataCheck == None):
                idData = createdDate.split(" ")
                idData = idData[0].replace("-", "")
                get_id = "select Max(c_rowid) from c3p_m_characteristics;"
                mycursor.execute(get_id)
                idValue = mycursor.fetchone()
                if (idValue[0] != None):
                    c_id = 'C' + idData + str(idValue[0])
                else:
                    c_id = 'C' + idData + '0'
                self.logger.debug("characteristics ID %s", c_id)
                required = []
                if (requiredValue == True):
                    required.append('Required')
                else:
                    required.append('None')
                uiComponent = None
                category = None
                if ("enumeration" == dataType):
                    if (dataList != None):
                        query = "insert into t_attrib_funct_m_category (category_name) value ('" + attribName + "')";
                        mycursor.execute(query)
                        get_query = "select id  from t_attrib_funct_m_category where category_name ='" + attribName + "';"
                        mycursor.execute(get_query)
                        id = mycursor.fetchone()
                        for val in dataList:
                            dropDownValQuery = "insert into t_attrib_funct_m_dropdown (attrib_value,category_id) values (%s,%s);"
                            dropDownVal = (val, id[0])
                            mycursor.execute(dropDownValQuery, dropDownVal)
                        uiComponent = 'Single select'
                        category = id[0]
                elif ("boolean" == dataType):
                    get_query = "select id  from t_attrib_funct_m_category where category_name ='" + dataType + "';"
                    mycursor.execute(get_query)
                    id = mycursor.fetchone()
                    uiComponent = 'Single select'
                    category = id[0]
                elif ("uint" in dataType):
                    uiComponent = 'Textbox'
                    if (requiredValue == True):
                        required.append('Numeric')
                    else:
                        required = []
                        required.append('Numeric')
                else:
                    uiComponent = 'Textbox'

            query = "insert into c3p_m_characteristics(c_id,c_name,c_f_id,c_uicomponent,c_validations,c_created_by," \
                    "c_created_date,c_is_key,c_category,c_replicationind) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
            val = (
            c_id, attribName, f_id, uiComponent, str(required), userName, createdDate, key, category, replication)
            mycursor.execute(query, val)
            mydb.commit()
        except Exception as e:
            mydb.rollback()


    def saveTemplateTreeStructure(self, deviceDeatils, fileName):
        mydb = Connections.create_connection()
        try:
            vendor_id = self.getTreeParentId(deviceDeatils.get_vendor())
            if (vendor_id == None):
                vendor_id = self.setTreeParentData(deviceDeatils.get_vendor(), vendor_id)
            os_id = self.getTreeParentId(deviceDeatils.get_os())

            if (os_id == None and vendor_id != None):
                os_id = self.setTreeParentData(deviceDeatils.get_os(), vendor_id)

            version_id = self.getTreeParentId(deviceDeatils.get_osversion())
            if (version_id == None and os_id != None):
                version_id = self.setTreeParentData(deviceDeatils.get_osversion(), os_id)

            if (self.getTreeParentId(fileName) == None):
                if (version_id != None):
                    self.setTreeParentData(fileName, version_id)
                elif (os_id != None):
                    self.setTreeParentData(fileName, os_id)
                elif (vendor_id != None):
                    self.setTreeParentData(fileName, vendor_id)
        except Exception as err:
            mydb.rollback()
            self.logger.error("Exception in saveTemplateTreeStructure: %s", err)
        finally:
            mydb.close

    def getTreeParentId(self,data):
        mydb = Connections.create_connection()
        id = 0
        try:
            mycursor = mydb.cursor(buffered=True)
            get_query = "select vt_row_id  from c3p_vnf_template_details where vt_component_name =%s;"
            mycursor.execute(get_query, (data,))
            id = mycursor.fetchone()
            if (id != None):
                id = id[0]
        except Exception as err:
            self.logger.error("Exception in getTreeParentId: %s", err)
        finally:
            mydb.close
        return id

    def setTreeParentData(self,data,id):
        mydb = Connections.create_connection()
        try:
            mycursor = mydb.cursor(buffered=True)
            query = "insert into c3p_vnf_template_details(vt_component_name,vt_component_parent_id) values (%s,%s)"
            val = (data, id)
            mycursor.execute(query, val)
            mydb.commit()
            id = self.getTreeParentId(data)
        except Exception as err:
            mydb.rollback()
        finally:
            mydb.close()
        return id