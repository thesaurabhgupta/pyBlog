from c3papplication.common import Connections
from c3papplication.conf.springConfig import springConfig
from jproperties import Properties
import logging
from datetime import datetime
import mysql.connector

configs = springConfig().fetch_config()

logger = logging.getLogger(__name__)

def setCardSlotInformation(data):
    allchildoidlist = []
    device_id_in=data.get('device_id')
    discovery_id_in=data.get('discovery_id')
    device_id=str(device_id_in)
    discovery_id=str(discovery_id_in)
    logger.info("Device id for card slot entry ::: %s",device_id)
    logger.info("Discovery id  for card slot entry:::%s ",discovery_id)
    #Based on device id and discovery id find the matching records from c3p_t_fork_inv_discrepancy
    allchildoidlist = getCollectedOIDsfromFidTable(device_id,discovery_id)

    setSaveAllSlotInfo(allchildoidlist,discovery_id,device_id)
    return True

def getCollectedOIDsfromFidTable(device_id,discovery_id):
    mydb = Connections.create_connection()
    childOidArray = ""
    selectedChildOidList= []
    try:
        mycursor = mydb.cursor(buffered=True)
        sql="SELECT fid_oid_no,fid_child_oid_no  FROM c3p_t_fork_inv_discrepancy where device_id='"+device_id+"'and fid_discovery_id='"+discovery_id+"'"
        mycursor.execute(sql)
        childOidArray = mycursor.fetchall()
        for row in childOidArray:
            val= row[1]
            if ".ST" in val or ".PT" in val or ".CT"  in val:
                selectedChildOidList.append(val)
        logger.info("CHILD OIDs with ST,PT,CT start ::: %s",selectedChildOidList)

    except Exception as err:
        logger.error("Exception in getCollectedOIDsfromFidTable: %s",err)
    finally:
        mydb.close
    return selectedChildOidList

def setSaveAllSlotInfo(childoidlist,discovery_id,device_id):
    mydb = Connections.create_connection()
    listofslots = []
    try:
        mycursor = mydb.cursor(buffered=True)
         #Logic to get all 'ST' in child list
        for row in childoidlist:
            individualarray = row.split(".")
            element = individualarray.pop()
            if element.startswith('STSL'):
                listofslots.append(element)
        for eachelement in listofslots:
            hasSubslot = "Y"
            #Save the slots in slot information table
            #Fetch the slot information from c3p_t_fork_inv_discrepancy
            sql="SELECT fid_discovered_value  FROM c3p_t_fork_inv_discrepancy where device_id='"+device_id+"'and fid_discovery_id='"+discovery_id+"'and fid_child_oid_no like '%"+eachelement+"'"
            mycursor.execute(sql)
            discoveredvalue = mycursor.fetchone()
            if 'SSXX' in eachelement:
                hasSubslot='N'
            now = datetime.now()
            dt_string = now.strftime('%Y-%m-%d %H:%M:%S')
            #Check if device id and discovered value pair is already present in c3p_slots table if yes just update else insert
            sql="SELECT slot_id from c3p_slots where device_id='"+device_id+"'and slot_name='"+discoveredvalue[0]+"'"
            #print(sql)
            mycursor.execute(sql)
            slotTableRec = mycursor.fetchone()
            if slotTableRec is None:
                sql = f"INSERT INTO c3p_slots(slot_name,device_id,has_subslot,discovery_oid,created_by,created_date) values('{discoveredvalue[0]}','{device_id}','{hasSubslot}','{eachelement}','admin','{dt_string}')"
                mycursor.execute(sql)
                mydb.commit()
            else:
                sql = "UPDATE c3p_slots SET slot_name ='"+discoveredvalue[0]+"',has_subslot ='"+hasSubslot+"',discovery_oid ='"+eachelement+ "',updated_date ='"+dt_string+"'where slot_id = '"+str(slotTableRec[0])+"'"
                mycursor.execute(sql)
                mydb.commit()

            if hasSubslot == 'N':
                #Find card information and insert in card table
                if(slotTableRec is None):
                    setSaveCardInfo(eachelement,discovery_id,device_id,mycursor.lastrowid,0)
                else:
                    setSaveCardInfo(eachelement,discovery_id,device_id,str(slotTableRec[0]),0)

            elif hasSubslot == 'Y':
                if(slotTableRec is None):
                    setSaveSubSlot(eachelement,discovery_id,device_id,mycursor.lastrowid)
                else:
                    setSaveSubSlot(eachelement,discovery_id,device_id,str(slotTableRec[0]))
                
           
    except Exception as err:
        logger.error("Exception in setSaveAllSlotInfo: %s",err)
    finally:
        mydb.close
    return True

def setSaveCardInfo(slot_oid,discovery_id,device_id,slot_row_id,sub_slot_row_id):
    mydb = Connections.create_connection()
    isInSubslot='Y'
    cardIDtoSearch = slot_oid.replace("ST","CT")
    try:
        mycursor = mydb.cursor(buffered=True)
        sql="SELECT fid_discovered_value  FROM c3p_t_fork_inv_discrepancy where device_id='"+device_id+"'and fid_discovery_id='"+discovery_id+"'and fid_child_oid_no like '%"+cardIDtoSearch+"'"
        mycursor.execute(sql)
        cardvalueres = mycursor.fetchone()
        cardvalue = list(cardvalueres)
        logger.debug("Card value: %s",cardvalue)
        now = datetime.now()
        dt_string = now.strftime('%Y-%m-%d %H:%M:%S')
        #Check if card already exists
        sql="SELECT card_id from c3p_cards where slot_id='"+str(slot_row_id)+"'and card_name='"+cardvalue[0]+"'"
        mycursor.execute(sql)
        cardTableRecRes = mycursor.fetchone()
        if cardTableRecRes is None:
            if sub_slot_row_id == 0:
                isInSubslot = 'N'
                sql = f"INSERT INTO c3p_cards(card_name,slot_id,is_in_subslot,created_by,created_date,discovery_oid) values('{cardvalue[0]}','{slot_row_id}','{isInSubslot}','admin','{dt_string}','{cardIDtoSearch}')"
                mycursor.execute(sql)
                mydb.commit()
            else:
                isInSubslot = 'Y'
                sql = f"INSERT INTO c3p_cards(card_name,slot_id,subslot_id,is_in_subslot,created_by,created_date,discovery_oid) values('{cardvalue[0]}','{slot_row_id}','{sub_slot_row_id}','{isInSubslot}','admin','{dt_string}','{cardIDtoSearch}')"
                mycursor.execute(sql)
                mydb.commit()
            savePortInformation(cardIDtoSearch,mycursor.lastrowid,discovery_id,device_id)
        else:
            cardTableRec=list(cardTableRecRes)
            if sub_slot_row_id == 0:
                isInSubslot = 'N'
                sql = "UPDATE c3p_cards SET card_name ='"+cardvalue[0]+"',slot_id ='"+slot_row_id+"',is_in_subslot ='"+isInSubslot+ "',updated_date ='"+dt_string+"'where card_id = '"+str(cardTableRec[0])+"'"
                mycursor.execute(sql)
                mydb.commit()
            else:
                isInSubslot = 'Y'
                sql = "UPDATE c3p_cards SET card_name ='"+cardvalue[0]+"',slot_id ='"+slot_row_id+"',is_in_subslot ='"+isInSubslot+ "',updated_date ='"+dt_string+ "',subslot_id ='"+sub_slot_row_id+"'where card_id = '"+str(cardTableRec[0])+"'"
                mycursor.execute(sql)
                mydb.commit()
            savePortInformation(cardIDtoSearch,str(cardTableRec[0]),discovery_id,device_id)


    except Exception as err:
        logger.error("Exception in setSaveCardInfo: %s",err)
    finally:
        mydb.close
    return True
True

def savePortInformation(card_oid,card_id,discovery_id,device_id):
    mydb = Connections.create_connection()
    portIDtoSearch = card_oid.replace("CT","PT")
    portIDtoSearch = portIDtoSearch[:-2]
    portIDtoSearch = portIDtoSearch+"%"
    try:
        mycursor = mydb.cursor(buffered=True)
        sql="SELECT fid_discovered_value,fid_child_oid_no  FROM c3p_t_fork_inv_discrepancy where device_id='"+device_id+"'and fid_discovery_id='"+discovery_id+"'and fid_child_oid_no like '%"+portIDtoSearch+"'"
        mycursor.execute(sql)
        portvalue = mycursor.fetchall()
        now = datetime.now()
        dt_string = now.strftime('%Y-%m-%d %H:%M:%S')
        for eachport in portvalue:
            portoid = eachport[1]
            temparray = portoid.split(".")
            tempelement = temparray.pop()
            sql="SELECT port_id from c3p_ports where card_id='"+str(card_id)+"'and port_name='"+eachport[0]+"'"
            mycursor.execute(sql)
            portTableRec = mycursor.fetchone()
            if portTableRec is None:
                sql = f"INSERT INTO c3p_ports(port_name,card_id,port_status,created_by,created_date,discovery_oid) values('{eachport[0]}','{card_id}','Free','admin','{dt_string}','{tempelement}')"
                mycursor.execute(sql)
                mydb.commit()
            else:
                sql = "UPDATE c3p_ports SET port_name ='"+eachport[0]+"',card_id ='"+card_id+"',updated_date ='"+dt_string+"'where port_id = '"+str(portTableRec[0])+"'"
                mycursor.execute(sql)
                mydb.commit()
    except Exception as err:
        logger.error("Exception in savePortInformation: %s",err)
    finally:
        mydb.close
    return True

def setSaveSubSlot(discovery_oid,discovery_id,device_id,slot_id):
    mydb = Connections.create_connection()
    try:
        mycursor = mydb.cursor(buffered=True)
        sql="SELECT fid_discovered_value FROM c3p_t_fork_inv_discrepancy where device_id='"+device_id+"'and fid_discovery_id='"+discovery_id+"'and fid_child_oid_no like '%"+discovery_oid+"'"
        mycursor.execute(sql)
        discoveredsubslotvalue = mycursor.fetchall()
        for eachsubslot in discoveredsubslotvalue:
            value = eachsubslot[0]
            now = datetime.now()
            dt_string = now.strftime('%Y-%m-%d %H:%M:%S')
            sql = f"INSERT INTO c3p_subslots(subslot_name,slot_id,created_by,created_date,discovery_oid) values('{value}','{slot_id}','admin','{dt_string}','admin','{discovery_oid}')"
            mycursor.execute(sql)
            mydb.commit()
            setSaveCardInfo(slot_id,discovery_id,device_id,mycursor.lastrowid,mycursor.lastrowid)
    except Exception as err:
        logger.error("Exception in setSaveSubSlot: %s",err)
    finally:
        mydb.close
    return True