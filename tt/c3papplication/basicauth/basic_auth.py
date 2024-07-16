from functools import wraps
from flask_api import status
from c3papplication.common import Connections
from c3papplication.conf.springConfig import springConfig
from flask import url_for, request, render_template, jsonify
from jproperties import Properties
import logging
import hashlib
from datetime import date, datetime
import hashlib
from Crypto.Cipher import AES
import base64 

configs = springConfig().fetch_config()

logger = logging.getLogger(__name__)

c3p_user_schema_hostname = (configs.get("C3P_User_Schema_hostname"))
c3p_user_schema = (configs.get("C3P_User_Schema"))
secret_key = (configs.get("secret_key"))
user = (configs.get("c3p_usrdb_usernm"))
password = (configs.get("c3p_usrdb_pass_word"))

# User Configs for feting data from userDB
user_config = {
            'user': user,
            'password': password,
            'host': c3p_user_schema_hostname,
            'database': c3p_user_schema,
            'raise_on_warnings': True
        }

class AES_pkcs5:
    def __init__(self,key:str, mode:AES.MODE_CBC=AES.MODE_CBC,block_size:int=16):
        self.key = self.setKey(key)
        self.mode = mode
        self.block_size = block_size

    def pad(self,byte_array:bytearray):
        """
        pkcs5 padding
        """
        pad_len = self.block_size - len(byte_array) % self.block_size
        return byte_array + (bytes([pad_len]) * pad_len)
    
    # pkcs5 - unpadding 
    def unpad(self,byte_array:bytearray):
        return byte_array[:-ord(byte_array[-1:])]

    def setKey(self,key:str):
        key = key.encode('utf-8')
        # From Google
        # Use a stronger key derivation function (KDF) instead of SHA-1
        # key = hashlib.pbkdf2_hmac('sha256', key, salt, iterations)
        return hashlib.sha256(key).digest()

    def encrypt(self,message:str)->str:
        # convert to bytes
        byte_array = message.encode("UTF-8")
        # pad the message - with pkcs5 style
        padded = self.pad(byte_array)
        # new instance of AES with encoded key
        cipher = AES.new(self.key, self.mode)
        # now encrypt the padded bytes
        encrypted = cipher.encrypt(padded)
        # base64 encode and convert back to string
        return base64.b64encode(encrypted).decode('utf-8')

    def decrypt(self,message:str)->str:
        # convert the message to bytes
        byte_array = message.encode("utf-8")
        # base64 decode
        message = base64.b64decode(byte_array)
        # AES instance with the - setKey()
        cipher= AES.new(self.key, self.mode)
        # decrypt and decode
        decrypted = cipher.decrypt(message).decode('utf-8')
        # unpad - with pkcs5 style and return 
        return self.unpad(decrypted)


def authenticate_user(username, password):
    try:
        is_acc_exp = bool

        # logger.debug("basic_auth:authenticate_user :: user_config: %s",user_config)
        mydb = Connections.create_connection(user_config)
        mycursor = mydb.cursor(buffered=True)

        sql = "SELECT user_name, current_password, account_expiry from c3p_t_user_mgt where user_name= %s and current_password= %s"
        try:
            mycursor.execute(sql, (username, password))
            result = mycursor.fetchall()

            # Fetch the date from query result
            acc_exp_date = result[0][2]

            # Check if User Account is Expired
            is_acc_exp = True if date.today() >= acc_exp_date.date() else False
        except Exception as err:
            logger.error("Exception in BasicAuth-authentication: %s", err)
            result = None
    except Exception as err:
        logger.error("Exception in BasicAuth-authentication: %s", err)
    finally:
        mydb.close
    return True if is_acc_exp is False and result is not None else False


def authorize_user(username, password):
    try:
        # logger.debug("basic_auth:authenticate_user :: user_config: %s", user_config)
        mydb = Connections.create_connection(user_config)
        mycursor = mydb.cursor(buffered=True)
        sql = "SELECT user_name, current_password from c3p_t_user_mgt where user_name= %s and current_password= %s"
        try:
            mycursor.execute(sql, (username, password))
            result = mycursor.fetchall()
        except Exception as err:
            logger.error("Exception in BasicAuth-authorization: %s", err)
            result = None
    except Exception as err:
        logger.error("Exception in BasicAuth-authorization: %s", err)
    finally:
        mydb.close
    return True if result else False


##################
# TASK ID: C3P-4063
# TASK Description: Python - User IDs in C3P should be expiring after a specific period of time
# TASK Overview: The below Function is a decorator which will be invoked everytime before executing the business logic
# TASK Working : The below Function will First Authorize the user and then Authenticate. Once its authorize, it will
# then check for the expiry date. IF the user account is expired, it will then respond with 401 Error.
##################
def authenticate(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        password = str(request.headers['password'])
        AES_pkcs5_obj = AES_pkcs5(secret_key)
        encrypted_password = AES_pkcs5_obj.encrypt(password)
        if not authorize_user(str(request.headers['username']), encrypted_password):
            return jsonify({"Error": "User not authorized" , "status":status.HTTP_401_UNAUTHORIZED}), status.HTTP_401_UNAUTHORIZED
        else:
            if not authenticate_user(str(request.headers['username']), encrypted_password):
                return jsonify({"Error": "User account expired", "status":status.HTTP_401_UNAUTHORIZED}), status.HTTP_401_UNAUTHORIZED
        return f(*args, **kwargs)
    return wrapper