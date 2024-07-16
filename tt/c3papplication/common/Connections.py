from distutils.log import debug
import mysql.connector
from mysql.connector import Error
from mysql.connector import errorcode
import sys
from pymongo import MongoClient
import logging, logging.config
from os import path
from jproperties import Properties
from c3papplication.conf.springConfig import springConfig


# global mydb 
# mydb = mysql.connector.connect()
# log_file_path = path.join(path.dirname(path.abspath(__file__)), 'conf/logging.conf')
# logging.config.fileConfig(log_file_path, disable_existing_loggers=False)
logger = logging.getLogger(__name__)

configs = springConfig().fetch_config()

c3p_schema_hostname= (configs.get("C3P_Schema_hostname")).strip()
c3p_schema= (configs.get("C3P_Schema")).strip()


config = {
  'user': 'root',
  'password': ']NKI:5QZz^0qJ@zg',
  'host': c3p_schema_hostname,
  'database': c3p_schema,
  'raise_on_warnings': True
}

# c3p_user_schema_hostname= (configs.get("C3P_User_Schema_hostname")).strip()
# c3p_rescat_schema= (configs.get("C3P_Rescat_Schema")).strip()

# config_rescat = {
#   'user': 'root',
#   'password': 'SQL@1234',
#   'host': c3p_user_schema_hostname,
#   'database': c3p_rescat_schema,
#   'raise_on_warnings': True
# }

def create_connection(default_config=config):
  #mydb = mysql.connector.connect()    #None
  mydb = sqlConnection(default_config)
  # print('DB Connection ::', mydb)
  #logger.debug('DB Connection 11:: %s', mydb.get_server_info())
  logger.debug('DB Connection :: %s', mydb)
  try:
    if mydb is not None and mydb.is_connected():
      logger.debug('DB Connection - Connected :: %s', mydb.get_server_info())
      # connecte()
    else:
      # print('DB Connection - Not Connected :: ')      
      mydb = mysql.connector.connect(**default_config)
      #logger.debug('DB Connection 22:: %s', mydb)
      #logger.debug('DB Connection 33:: %s', mydb.is_connected())
      #logger.debug('DB Connection 44:: %s', mydb.get_server_info())
      #mydb._execute_query('set max_allowed_packet=67108864)
      #connection.execute('set max_allowed_packet=67108864')
  except mysql.connector.Error as e:
    logger.error('DB Connection - Error :: %s >> %s', e, mysql.connector.errorcode)
  # finally:
  #     if mydb is not None and mydb.is_connected():
  #       print('DB Connection - Closing DB')
  #       mydb.close()
  return mydb

def sqlConnection(configs):
  conn = None
  try:   
    conn = mysql.connector.connect(**configs)
    logger.debug('sqlConnection conn:: %s', conn)  
  except mysql.connector.InterfaceError as interfaceError:
    logger.error('sqlConnection - interfaceError :: %s - errorcode - %s', interfaceError, mysql.connector.errorcode)
    #sqlConnection()
  except mysql.connector.DatabaseError as databaseError:
    logger.error('sqlConnection - databaseError :: %s - errorcode - %s', databaseError, mysql.connector.errorcode)
    #sqlConnection()
  except mysql.connector.Error as e:
    logger.error('DB Connection - Error :: %s >> %s', e, mysql.connector.errorcode)
    #sqlConnection()
  return conn

def create_mongo_connection():
  client = MongoClient('mongodb://10.179.90.73:27017')
  try:
    mongo=client.c3pdbschema
    logger.debug('common::connections:create_mongo_connection:: %s', mongo)  
  except:
    e = sys.exc_info()[0]
    logger.error('create_mongo_connection - Error :: %s', e)
  return mongo


def connecte():
  conne = None
  myPoolValues={"output":[],"error":""}
  try:
    conne = mysql.connector.connect(user='clouduser', password='Root@1234',host='10.179.90.67',database='c3pdbschema_dev',port=3306)
    if conne.is_connected():
      print('Connected to MySQL database')
      logger.debug("Connected to MySQL database - dbtest")
      mycur = conne.cursor()
      mycur.execute("SELECT r_ip_pool_id,r_ip_pool_purpose FROM c3p_ip_range_pool_mgmt ")
      myDbValue = mycur.fetchall()
      for myDbValue in myDbValue:
        myDbValue={"poolID":myDbValue[0],"ippoolpurpose":myDbValue[1]}    
        myPoolValues["output"].append(myDbValue)   
        myPoolValues.update(myPoolValues) 
      logger.debug('Get all iprange pool available :: %s', myPoolValues)   
  except Error as e:
    myPoolValues={"output":[],"error":str(e)}
    logger.error("Exception in ippoolrange: %s",e)
  finally:
    if conne is not None and conne.is_connected():
      conne.close()

  
      
