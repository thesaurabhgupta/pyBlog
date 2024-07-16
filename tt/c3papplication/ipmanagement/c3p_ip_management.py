import logging, logging.config
from os import path
from datetime import datetime
import json
from jproperties import Properties
from c3papplication.common import Connections
from c3papplication.conf.springConfig import springConfig
from mysql.connector.errors import Error, ProgrammingError

logger = logging.getLogger(__name__)

configs = springConfig().fetch_config()
    
def getPoolId():
  mydb = Connections.create_connection()
  myPoolValues={"output":[],"error":""}
  try:
      mycursor = mydb.cursor(buffered=True)
      mycursor.execute("SELECT r_ip_pool_id,r_ip_pool_purpose FROM c3p_ip_range_pool_mgmt ")
      myDbValue = mycursor.fetchall()  
      for myDbValue in myDbValue:
        myDbValue={"poolID":myDbValue[0],"ippoolpurpose":myDbValue[1]}    
        myPoolValues["output"].append(myDbValue)   
        myPoolValues.update(myPoolValues) 
      logger.debug('Get all iprange pool available :: %s', myPoolValues)           
  except Exception as e:
      myPoolValues={"output":[], "error": "Unkown error in ippoolrange"}
      logger.error("Exception in ippoolrange: %s",e)
  finally:
    mydb.close
  return(myPoolValues)

def checkHostIp(poolId):  
  mydb = Connections.create_connection()  
  myPoolValues={"output":[],"error":""}
  try: 
      mycursor = mydb.cursor(buffered=True)
      for poolId in poolId:
          mycursor.execute("SELECT h_pool_id,h_status,h_start_ip FROM c3p_host_ip_mgmt where h_pool_id = %s and h_status ='Available'", (poolId,))
          myDbValue = mycursor.fetchone()
          if myDbValue != None:
              myDbValue={"poolID":myDbValue[0],"ip":myDbValue[2]}
              myPoolValues["output"].append(myDbValue)       
      if len(myPoolValues['output'] )== 0:
        myDbValue={"output":[],"error":"Pool id not Available"}
      else:
        myDbValue=myPoolValues['output'][0]
        myDbValue={"output":[myDbValue],"error":""}                                           
  except Exception as e:
                  myDbValue={"output":[],"error":"Unknown error in checking hostip"} 
                  logger.error("Exception in Hostip: %s",e)      
  finally:
    mydb.close
  return(myDbValue)

def allocateHostIp(content):
  
  hStatus= content['hStatus']
  customer= content['customer']
  region= content['region']
  siteName= content['siteName']
  siteId= content['siteId']
  hostName= content['hostName']
  role= content['role']
  createdBy= content['createdBy']
  updatedBy= content['updatedBy']
  poolIdIp= content['ipPools']
  
  mydb = Connections.create_connection()
  try:
    mycursor = mydb.cursor(buffered=True)
    dateCreated= datetime.today().strftime('%Y-%m-%d %H:%M:%S') 
    dateUpdate= datetime.today().strftime('%Y-%m-%d %H:%M:%S') 
    for x in poolIdIp:
      poolId=x['poolId']
      startIp=x['startIp'] 
      sql="update c3p_host_ip_mgmt set h_updated_by=%s,h_created_by=%s,h_role=%s,h_hostname=%s,h_site_id= %s,h_site_name= %s,h_region= %s,h_customer= %s,h_status=%s,h_created_date=%s,h_updated_date=%s where h_start_ip=%s and h_pool_id= %s"
      mycursor.execute(sql, (updatedBy, createdBy, role, hostName, siteId, siteName, region, customer, hStatus, dateCreated, dateUpdate, startIp, poolId))
      mydb.commit()
      myData={"output":[x],"error":" "}    
    
  except Exception as e:
    logger.error("Exception in allocation of status: %s",e)
    myData={"output":[],"error":"The Ip is not allocated"}  
  finally:
    mydb.close                  
  return( myData)  