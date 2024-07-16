from c3papplication.common import Connections
from gridfs import GridFS
import logging

logger = logging.getLogger(__name__)



def getTreeViewFeatures(input):
    mongodb = Connections.create_mongo_connection()
    try:
        fs = GridFS(mongodb,"featureTree")
        valueToReturn=""
        data=""
        if(fs.exists(filename=input)):
            gout = fs.get_last_version(input)
            print("before new file")
            data = gout.read()
            valueToReturn=data.decode(encoding='UTF-8')
            gout.close()
    except Exception as err:
        logger.error("yang::yangExtractor::getTreeViewFeatures: %s",err)        
    return valueToReturn

def getYang(input):
    try:
        mongodb = Connections.create_mongo_connection()
        fs = GridFS(mongodb,"yang")
        valueToReturn=""
        data=""
        if(fs.exists(filename=input)):
            gout = fs.get_last_version(input)
            logger.debug("yang::yangExtractor::getYang:before new file")
            data = gout.read()
            logger.debug("yang:yangExtractor::getYang:data - %s",data)
            valueToReturn=data.decode(encoding='UTF-8')
            gout.close()
    except Exception as err:
        logger.error("yang::yangExtractor::getYang: %s",err) 
    return valueToReturn

def getScript(content):
    mongodb = Connections.create_mongo_connection()
    try:
        filename  = content['filename']
        response=""
        fs = GridFS(mongodb,"scripts")
        data=""
        if(fs.exists(filename=filename)):
            gout = fs.get_last_version(filename)
            data = gout.read()
            response=data.decode(encoding='UTF-8')
            gout.close()
    except Exception as err:
        logger.error("yang::yangExtractor::getScript: %s",err) 
    return response