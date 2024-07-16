from functools import wraps
from flask_api import status
from c3papplication.common import Connections
from c3papplication.conf.springConfig import springConfig
from flask import url_for, request, render_template, jsonify
from jproperties import Properties
import logging
import hashlib
from datetime import datetime, timedelta
import hashlib
from Crypto.Cipher import AES
import base64
import jwt

configs = springConfig().fetch_config()

logger = logging.getLogger(__name__)

c3p_user_schema_hostname = (configs.get("C3P_User_Schema_hostname")).strip()
c3p_user_schema = (configs.get("C3P_User_Schema")).strip()
secret_key = (configs.get("secret_key")).strip()
user = (configs.get("c3p_usrdb_usernm")).strip()
password = (configs.get("c3p_usrdb_pass_word")).strip()
block_size: int = 16

# User Configs for feting data from userDB
user_config = {
    'user': user,
    'password': password,
    'host': c3p_user_schema_hostname,
    'database': c3p_user_schema,
    'raise_on_warnings': True
}


def pad(byte_array: bytearray):
    """
    pkcs5 padding
    """
    pad_len = block_size - len(byte_array) % block_size
    return byte_array + (bytes([pad_len]) * pad_len)


def setKey(key: str):
    # # convert to bytes
    # key = key.encode('utf-8')
    # # From Google
    # # Use a stronger key derivation function (KDF) instead of SHA-1
    # # key = hashlib.pbkdf2_hmac('sha256', key, salt, iterations)
    # return hashlib.sha256(key).digest()
    # convert to bytes
    key = key.encode('utf-8')
    # get the sha1 method - for hashing
    sha1 = hashlib.sha1
    # and use digest and take the last 16 bytes
    key = sha1(key).digest()[:16]
    # now zero pad - just incase
    key = key.zfill(16)
    return key

key = setKey(secret_key)

def encrypt(message: str) -> str:
    # convert to bytes
    byte_array = message.encode("UTF-8")
    # pad the message - with pkcs5 style
    padded = pad(byte_array)
    # new instance of AES with encoded key
    #cipher = AES.new(key, AES.MODE_CBC)
    cipher = AES.new(key, AES.MODE_ECB)
    # now encrypt the padded bytes
    encrypted = cipher.encrypt(padded)
    # base64 encode and convert back to string
    return base64.b64encode(encrypted).decode('utf-8')


def authorize_user(username, password):
    try:
        mydb = Connections.create_connection(user_config)
        mycursor = mydb.cursor(buffered=True)
        sql = "SELECT user_name, current_password from c3p_t_user_mgt where user_name=%s and current_password=%s"
        try:
            mycursor.execute(sql, (username, password,))
            result = mycursor.fetchall()
        except Exception as err:
            logger.error("basicauth:Jwt_auth::authorize_user: %s", err)
            result = None
    except Exception as err:
        logger.error("basicauth:Jwt_auth::authorize_user: %s", err)
    finally:
        mydb.close
    return True if result else False


def user_access(credentials):
    try:
        username = credentials["username"]
        password = credentials["password"]
        encrypted_password = encrypt(password)

        mydb = Connections.create_connection(user_config)
        mycursor = mydb.cursor(buffered=True)
        sql = "SELECT user_name, current_password,account_expiry from c3p_t_user_mgt where user_name=%s and current_password=%s and account_expiry < %s"
        try:
            mycursor.execute(sql, (username, encrypted_password, datetime.now(),))
            result = mycursor.fetchone()
        except Exception as err:
            logger.error("basicauth:Jwt_auth::user_access: %s", err)
            result = None
    except Exception as err:
        logger.error("basicauth:Jwt_auth::user_access: %s", err)
    finally:
        mydb.close
    return True if result else False


def verify_credentials(credentials):
    try:
        username = credentials["username"]
        password = credentials["password"]
        encrypted_password = encrypt(password)

        if not authorize_user(username, encrypted_password):
            # return jsonify({"Error": "User not authorized", "status": status.HTTP_401_UNAUTHORIZED}), status.HTTP_401_UNAUTHORIZED
            return jsonify({"code": "UNAUTHENTICATED", "status": 401,
                            "message": "Authorization failed: ..."}), status.HTTP_401_UNAUTHORIZED


    except:
        # return jsonify({"Error": "User not authorized", "status": status.HTTP_401_UNAUTHORIZED}), status.HTTP_401_UNAUTHORIZED
        return jsonify({"code": "UNAUTHENTICATED", "status": 401,
                        "message": "Authorization failed: ..."}), status.HTTP_401_UNAUTHORIZED


def token_required(f):
    @wraps(f)
    def token_decorator(*args, **kwargs):
        token = None

        if "Authorization" in request.headers:
            value = request.headers["Authorization"]
            token = value.replace("Bearer ", "")
        else:
            # return jsonify({"Error": "Token is required", "status": 401}), status.HTTP_401_UNAUTHORIZED
            return jsonify({"code": "INVALID_ARGUMENT", "status": 400,
                            "message": "Expected property is missing: Bearer Token"}), status.HTTP_400_BAD_REQUEST

        try:
            data = jwt.decode(token, configs.get('token_secret_key'), algorithms=['HS256'])
            if verify_credentials(data):
                raise Exception
        except Exception as err:
            logger.error("jwt_auth:token_decorator: %s", err)
            return jsonify(
                {"code": "UNAUTHENTICATED", "Error": "Invalid Token", "status": 401}), status.HTTP_401_UNAUTHORIZED

        return f(*args, **kwargs)

    return token_decorator


def token_generator(credentials):
    if not credentials or not credentials["username"] or not credentials["password"]:
        # return jsonify({"Error": "Credentials are Required", "status": 401}), status.HTTP_401_UNAUTHORIZED
        return jsonify({"code": "INVALID_ARGUMENT", "status": 400,
                        "message": "Expected property is missing"}), status.HTTP_400_BAD_REQUEST

    verify_credetials = verify_credentials(credentials)
    if verify_credetials:
        return jsonify({"code": "UNAUTHENTICATED", "status": 401,
                        "message": "Authorization failed: ..."}), status.HTTP_401_UNAUTHORIZED
        # jsonify({"Error": "User Not Authorized", "status": status.HTTP_401_UNAUTHORIZED}), status.HTTP_401_UNAUTHORIZED

    user_access_flag = user_access(credentials)
    if user_access_flag:
        return jsonify({"code": "PERMISSION_DENIED", "status": 403,
                        "message": "Operation not allowed: ..."}), status.HTTP_403_FORBIDDEN

    expiry_time = datetime.utcnow() + timedelta(minutes=15)
    token = jwt.encode({"username": credentials["username"], "password": credentials["password"],
                        "exp": expiry_time}, configs.get('token_secret_key'))

    return jsonify({"token_type": "Bearer",
                    "access_token": token,
                    "expires_in": expiry_time})