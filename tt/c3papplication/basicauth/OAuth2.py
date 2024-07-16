import json
from urllib.request import urlopen
from authlib.integrations.flask_oauth2 import ResourceProtector
from authlib.jose.rfc7517.jwk import JsonWebKey
from authlib.oauth2.rfc7523 import JWTBearerTokenValidator
from c3papplication.conf.springConfig import springConfig
from jproperties import Properties
import logging

configs = springConfig().fetch_config()
    
logger = logging.getLogger(__name__)

issuer_realm = (configs.get("C3P_realms_issuer")).strip()

class clientCredsTokenValidator(JWTBearerTokenValidator):
    def __init__(self,issuer):
        jsonurl=urlopen(f"{issuer}/protocol/openid-connect/certs")
        publickey=JsonWebKey.import_key_set(json.loads(jsonurl.read()))
        super(clientCredsTokenValidator,self).__init__(publickey)
        self.claims_options={
            "exp":{"essential":True},
            "iss":{"essential":True,"value":issuer}
        }

requireAuth= ResourceProtector()
validator=clientCredsTokenValidator(issuer_realm)
requireAuth.register_token_validator(validator)