import json
from c3papplication.common import Connections
from c3papplication.conf.springConfig import springConfig
import logging
from jproperties import Properties
import random,string
from datetime import datetime

configs = springConfig().fetch_config()

logger = logging.getLogger(__name__)

def incidntRaise(inpt_json):
    mydb = Connections.create_connection()

    try:
        version=inpt_json["version"]
        version = version.replace('\r\n','').replace('\n','') 

        logger.debug("tmf:c3p_tmf_incident_raise::incidntRaise:version %s", version)
        requestID=inpt_json["requestID"]
        requestID = requestID.replace('\r\n','').replace('\n','') 
        logger.debug("tmf:c3p_tmf_incident_raise::incidntRaise:requestID %s", requestID)
        sourcesystem = inpt_json["sourcesystem"]
        sourcesystem = sourcesystem.replace('\r\n','').replace('\n','') 
        logger.debug("tmf:c3p_tmf_incident_raise::incidntRaise:sourcesystem %s", sourcesystem)

        mycursor = mydb.cursor(buffered=True)

        reqtbl_query="SELECT r_hostname,r_management_ip,r_vendor,r_siteid,r_siten_ame,r_status FROM c3p_t_request_info where r_alphanumeric_req_id=%s and r_request_version=%s"
        logger.debug("tmf:c3p_tmf_incident_raise::incidntRaise:reqtbl_query %s", reqtbl_query)
        mycursor.execute(reqtbl_query, (requestID,version, version,))
        data_reqtbl= mycursor.fetchone()
        logger.debug("tmf:c3p_tmf_incident_raise::incidntRaise:data_reqtbl %s", data_reqtbl)

        dvctbl_query="SELECT d_id FROM c3p_deviceinfo where d_mgmtip='"+ data_reqtbl[1] +"' and d_hostname='"+ data_reqtbl[0] +"'"
        logger.debug("tmf:c3p_tmf_incident_raise::incidntRaise:dvctbl_query %s", dvctbl_query)
        mycursor.execute(dvctbl_query)
        data_dvctbl= mycursor.fetchone()
        logger.debug("tmf:c3p_tmf_incident_raise::incidntRaise:data_dvctbl %s", data_dvctbl)

        csttbl_query="SELECT c_cust_id,c_site_region,c_site_name FROM c3p_cust_siteinfo where c_site_id='"+ data_reqtbl[3] +"' and c_site_name='"+ data_reqtbl[4] +"'"
        logger.debug("tmf:c3p_tmf_incident_raise::incidntRaise:csttbl_query %s", csttbl_query)
        mycursor.execute(csttbl_query)
        data_csttbl=mycursor.fetchone()
        logger.debug("tmf:c3p_tmf_incident_raise::incidntRaise:data_csttbl %s", data_csttbl)

        mycursor.execute("SELECT ss_id FROM c3p_m_source_system where ss_code =%s", (sourcesystem,))
        ss_id=mycursor.fetchone()
        logger.debug("tmf:c3p_tmf_incident_raise::incidntRaise:ss_id %s", ss_id)

        extnltbl_query="SELECT es_name,es_description,es_ticket_type,es_correlation_display,es_assignment_group,es_category,es_sub_category FROM externalsystem_params where es_destination_system='"+ ss_id[0] +"'"
        mycursor.execute(extnltbl_query)
        data_extnltbl = mycursor.fetchone()
        logger.debug("tmf:c3p_tmf_incident_raise::incidntRaise:data_extnltbl %s", data_extnltbl)

        res={}
        channel={}
        site_data=[]
        reltdEnt={}
        reldEnt2={}
        res["name"]=data_extnltbl[0]
        res["description"]=data_extnltbl[1]
        res["impact"]= 1
        res["urgency"]=1
        res["status"] = "new"
        res["ticketType"] = data_extnltbl[2]
        res["correlationID"] = requestID
        res["correlationDisplay"] = data_extnltbl[3]
        res["assignmentGroup"] = data_extnltbl[4]
        res["category"] = data_extnltbl[5]
        res["subCategory"] = data_extnltbl[6]
        res["vendor"] = data_reqtbl[2]
        channel["name"] = "alert"
        res["channel"]=channel
        reltdEnt["id"]=data_csttbl[0]
        reltdEnt["name"]=data_reqtbl[3]
        reldEnt2["id"]=data_csttbl[1]
        reldEnt2["name"]="market"
        site_data.append(reltdEnt)
        site_data.append(reldEnt2)
        res["relatedEntity"] = site_data

        logger.debug("tmf:c3p_tmf_incident_raise::incidntRaise:res %s", res)


        #pending code for service now connection and response

        id_temp=create_rfo_id()
        dt = datetime.now()

        rf_odr_sql =  "INSERT INTO c3p_rf_orders(rfo_id,rfo_apibody,rfo_apioperation,rfo_apiurl,rfo_status,rfo_created_date) VALUES (%s,%s,%s,%s,%s,%s)"
        rf_odr_val = (id_temp, json.dumps(res),"POST", "update_from_snow", "InProgress",dt)
        logger.debug("tmf:c3p_tmf_incident_raise::incidntRaise:rf_odr_val %s", rf_odr_val)
        mycursor.execute(rf_odr_sql, rf_odr_val)
        mydb.commit()

        rfo_dcmps_sql = "INSERT INTO c3p_rfo_decomposed(od_rfo_id,od_rf_taskname,od_req_resource_id,od_request_id,od_requeststatus,od_created_date,od_created_by) VALUES (%s,%s,%s,%s,%s,%s,%s)"
        rfo_dcmps_val = (id_temp, "incidentCreation", data_dvctbl[0],requestID,"Completed", dt,"system")
        logger.debug("tmf:c3p_tmf_incident_raise::incidntRaise:rfo_dcmps_val %s", rfo_dcmps_val)
        mycursor.execute(rfo_dcmps_sql, rfo_dcmps_val)
        mydb.commit()

        respnse = res

    except Exception as err:
        respnse={"status":"failure"} # json Format-- create var for it
        logger.error("tmf:c3p_tmf_incident_raise::incidntRaise:err - %s", err)

    finally:
        mydb.close
        return respnse


def create_rfo_id():
    return ("INCWLS"+ "".join(random.choices(string.digits, k=7)))