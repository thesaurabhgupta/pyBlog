from python_terraform  import *
import logging
from jproperties import Properties
from c3papplication.conf.springConfig import springConfig
import shutil
import os


configs = springConfig().fetch_config()
    
logger = logging.getLogger(__name__)

def deployInstance(path):
    response = {}
    try:
        binarypath=configs.get("terraform_binanary_path")

        base_path = "/opt/jboss/"
        filename = os.path.basename(path)
        path = os.path.normpath(os.path.join(base_path, filename))
        if not path.startswith(base_path):
            logger.error(f"Invalid file path: {path}")
            return jsonify({"error": f"Invalid file path: {path}"})

        if (path.find('/opt/jboss/') != -1):
            dest = path[0:11] + path[-12:]
            path = shutil.copytree(path, dest)   #path used in gke demo
        logger.info("path:::: %s",path)
        tf=Terraform(working_dir=path,terraform_bin_path=binarypath)
        logger.info("Working dir:::%s",tf.working_dir)
        tf.init()
        tf.plan()
        tf.apply(skip_plan=True)
        terrares=tf.cmd('state pull')
        logger.info("terrares:::: %s",terrares)
        res=terrares[1]
        jsonres=json.loads(res)
        logger.info("jsonres:::: %s",jsonres)
        response={
                "output":jsonres
                }
        response=json.dumps(response)
    except Exception as err:
        logger.error("Exception in instance creation: %s",err)
    return str(response)
    