from c3papplication.common import Connections
from c3papplication.conf.springConfig import springConfig
import io
import logging
import pandas as pd
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import request
from jproperties import Properties
import os
import random
import string

configs = springConfig().fetch_config()

logger = logging.getLogger(__name__)

def ranParaValueUpdate(file,data):
    mydb = Connections.create_connection()
    try:
        importId = create_import_id()
        logger.debug("ran:c3p_ran::ranParaValueUpdate:inside file %s", file )
        file_data=file
        filename = secure_filename(file_data.filename)
        file_path = configs.get("File_Storage_Path")
        file_data.save(os.path.join(file_path, filename))
        file=file_path+filename
        updated_by=data["createdBy"]
        sourceSystem=data["sourceSystem"]
        dtime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        logger.debug("ran:c3p_ran::ranParaValueUpdate:file - %s", file)
        logger.debug("ran:c3p_ran::ranParaValueUpdate:user - %s", updated_by)
        logger.debug("ran:c3p_ran::ranParaValueUpdate:sourceSystem - %s", sourceSystem)
        with open(file, "rb") as f:
            #file_io_obj = io.BytesIO(f.read())
            file_io_obj = f.read()

        mycursor = mydb.cursor(buffered=True)
        if file_io_obj:
            file_status = "Pass"
        else:
            file_status = "Fail"

        if file_status:
            import_type = "RANBaselinePar"
            sql = "INSERT INTO c3p_m_ds_import_detail(id_created_by,id_created_on,id_name,id_status,id_import_id,id_type) VALUES (%s,%s,%s,%s,%s,%s)"
            logger.debug("ran:c3p_ran:createImportRecordTransactionTable::sql - %s", sql)
            val = (updated_by, dtime, filename, file_status, importId,import_type)
            mycursor.execute(sql, val)
            mydb.commit()

        mycursor.execute("Select distinct r4_fbp_exsheet_name from c3p_m_ran_4g_baseparameter")
        all_sheets = mycursor.fetchall()

        for sheet in all_sheets:
            logger.debug("ran:c3p_ran::ranParaValueUpdate:Current Sheet - %s", sheet[0])

            if sheet[0] in ("LNBTS","LNCEL"):
                #conv = {x: str for x in
                #        pd.read_excel(file_io_obj, sheet_name=sheet[0], engine="openpyxl", header=(0, 1)).columns}
                df = pd.read_excel(file_io_obj, sheet[0], engine="openpyxl", header=(0, 1))#,converters=conv)
            else:
                #conv = {x: str for x in
                #        pd.read_excel(file_io_obj, sheet_name=sheet[0], engine="openpyxl", header=(0)).columns}
                df = pd.read_excel(file_io_obj, sheet[0], engine="openpyxl", header=(0))#,converters=conv)

            logger.debug("ran:c3p_ran::ranParaValueUpdate:Data read from excel")
            query1="Select r4_fbp_exsheet_para_name,r4_fbp_exsheet_name,r4_fbp_name,r4_fbp_exsheet_cata,r4_fbp_exsheet_para_value,r4_fbp_value2,r4_fbp_value1,r4_fbp_para_value0 from c3p_m_ran_4g_baseparameter where r4_fbp_exsheet_name= '"+sheet[0]+"'"
            mycursor.execute(query1)
            all_db_val=mycursor.fetchall()
            logger.debug("ran:c3p_ran::ranParaValueUpdate:Data read from excel")

            for i in all_db_val:
                par_val_xl=[]
                if sheet[0] in ("LNBTS","LNCEL"):
                    par_val_xl=list(df.loc[df['Unnamed: 1_level_0','Abbreviated Name'] == i[0],('GUI',str(i[3]))])
                elif sheet[0] in ("QoS"):
                    par_val_xl = list(df.loc[df['Abbreviated Name'] == i[0], (str(i[3]))])
                elif sheet[0] in ("MISC"):
                    par_val_xl = list(df.loc[df['Parameter (Abbreviated Name)'] == i[0], (str(i[3]))])


                #logger.debug("ran:c3p_ran::ranParaValueUpdate:par_val_xl - %s", par_val_xl)
                if par_val_xl != []:
                    if str(par_val_xl[0]) != str(i[4]):
                        dt = datetime.now()
                        dtime = dt.strftime("%Y-%m-%d %H:%M:%S")
                        query2="update c3p_m_ran_4g_baseparameter set r4_fbp_exsheet_para_value = %s, r4_fbp_value2 = %s, r4_fbp_value1 = %s, r4_fbp_para_value0 = %s , r4_fbp_updated_by = %s, r4_fbp_updated_date = %s, r4_fbp_importid = %s, r4_fbp_source_system = %s where r4_fbp_exsheet_para_name=%s and r4_fbp_exsheet_cata=%s"
                        logger.debug("ran:c3p_ran::ranParaValueUpdate:Update query2 %s", query2)
                        mycursor.execute(query2, (str(par_val_xl[0]), str(par_val_xl[0]), str(i[5]), str(i[6]), updated_by, dtime, str(importId), str(sourceSystem), str(i[0]), str(i[3],)))
                        logger.debug("ran:c3p_ran::ranParaValueUpdate:Update Value %s", i[0])
                        mydb.commit()

        feature_respnse=updateFeatureValue()

        if feature_respnse=="0":
            CIRTT_response=createImportRecordTransactionTable(importId)
            if CIRTT_response =="0":
                respnse = {"importId": importId, "status": "success"}
            else:
                respnse = {"importId": importId, "status": "failure"}
        else:
            respnse = {"importId": importId, "status": "failure"}

        logger.debug("ran:c3p_ran::ranParaValueUpdate:respnse - %s", respnse)
    except Exception as err:
        respnse={"importId":importId,"status":"failure"} # json Format-- create var for it
        logger.error("ran:c3p_ran::ranParaValueUpdate:err - %s", err)

    finally:
        mydb.close
        return respnse


def updateFeatureValue():
    mydb = Connections.create_connection()

    try:
        mycursor = mydb.cursor(buffered=True)

        mycursor.execute("Select  distinct r4_fbp_exsheet_cata, r4_fbp_family,r4_fbp_exsheet_name from c3p_m_ran_4g_baseparameter ")
        all_values = mycursor.fetchall()

        for value in all_values:
            # if value[2]=="LNBTS":
            #     last_var=str(value[0]).split()
            #     feature = str(value[1]) + "_" + str(value[2]) + "_" + str(" ".join(last_var[1:]))
            # else:
            #     feature=str(value[1])+"_"+str(value[2])+"_"+str(value[0])
            feature = str(value[1]) + "_" + str(value[2]) + "_" + str(value[0])
            logger.debug("ran:c3p_ran::updateFeatureValue:feature - %s", feature)
                #continue

            mycursor.execute("Select f_id from c3p_m_features where f_name = %s",(feature,))
            fId = mycursor.fetchone()
            logger.debug("ran:c3p_ran::updateFeatureValue:fId - %s", fId)

            if fId != None :
                mycursor.execute("Select command_value from c3p_template_master_command_list where master_f_id = %s",(fId[0],))
                all_command_values = mycursor.fetchall()

                for command in all_command_values:
                    #logger.debug("ran:c3p_ran::ranParaValueUpdate:command - %s", command)
                    cmd_val=str(command).split(">")
                    #logger.debug("ran:c3p_ran::ranParaValueUpdate:cmd_val - %s", cmd_val)

                    if "<p name" in cmd_val[0]:
                        abv_name=cmd_val[0].split('"')
                        #logger.debug("ran:c3p_ran::ranParaValueUpdate:abv_name[1] - %s", abv_name[1])
                        val = cmd_val[1].split("<")
                        #logger.debug("ran:c3p_ran::ranParaValueUpdate:val[0] - %s", val[0])
                        mycursor.execute("Select r4_fbp_exsheet_para_value from c3p_m_ran_4g_baseparameter where r4_fbp_exsheet_para_name= %s and r4_fbp_exsheet_cata = %s",(abv_name[1],value[0],))
                        para_val_db = mycursor.fetchone()

                        #if para_val_db==None: # para != None
                        #    continue
                        #logger.debug("ran:c3p_ran::ranParaValueUpdate:paraval - %s", para_val_db[0])

                        if para_val_db != None:
                            if para_val_db[0] != val[0] :
                                new_val = '\n<p name="'+abv_name[1]+'">'+para_val_db[0]+'</p>\n'
                                #logger.debug("ran:c3p_ran::ranParaValueUpdate:Inside paraval db method
                                query="update c3p_template_master_command_list set command_value = '"+new_val+"' where command_value = '"+command[0]+"' and  master_f_id ='"+fId[0]+"'"
                                logger.debug("ran:c3p_ran::updateFeatureValue:Updated Value %s",abv_name[1])
                                logger.debug("ran:c3p_ran::updateFeatureValue:query %s",query)
                                mycursor.execute(query)
                                mydb.commit()

                            #createImportRecordTransactionTable(importid)---

        respns="0"


    except Exception as err:
        respns="1"
        logger.error("ran:c3p_ran:Update_Features:updateFeatureValue::Error - %s", err)
    finally:
        mydb.close
        return respns



def createImportRecordTransactionTable(importId):
    try:
        mydb = Connections.create_connection()
        mycursor = mydb.cursor(buffered=True)

        cols = 'r4_fbp_id,r4_fbp_vendor,r4_fbp_family,r4_fbp_os,r4_fbp_osver,r4_fbp_region,r4_fbp_nf,r4_fbp_techno,r4_fbp_name,r4_feature_id,r4_fbp_para,r4_fbp_para_type,r4_fbp_para_value0,r4_fbp_value1,r4_fbp_value2,r4_fbp_exsheet_name,r4_fbp_exsheet_para_name,r4_fbp_exsheet_cata,r4_fbp_exsheet_para_value,r4_fbp_created_by,r4_fbp_created_date,r4_fbp_updated_by,r4_fbp_updated_date,r4_fbp_importid,r4_fbp_source_system'

        query = "SELECT " + cols + " FROM c3p_m_ran_4g_baseparameter where r4_fbp_importid = '"+ importId +"'"
        logger.debug("ran:c3p_ran:createImportRecordTransactionTable::query - %s", query)
        mycursor.execute(query)
        rows = mycursor.fetchall()


        trns_cols = "ir4_fbp_id,ir4_fbp_vendor,ir4_fbp_family,ir4_fbp_os,ir4_fbp_osver,ir4_fbp_region,ir4_fbp_nf,ir4_fbp_techno,ir4_fbp_name,ir4_feature_id,ir4_fbp_para,ir4_fbp_para_type,ir4_fbp_para_value0,ir4_fbp_value1,ir4_fbp_value2,ir4_fbp_exsheet_name,ir4_fbp_exsheet_para_name,ir4_fbp_exsheet_cata,ir4_fbp_exsheet_para_value,ir4_fbp_created_by,ir4_fbp_created_date,ir4_fbp_updated_by,ir4_fbp_updated_date,ir4_fbp_importid,ir4_fbp_source_system"
        for i in rows:
            val = tuple(i)
            sql = "INSERT INTO c3p_t_imp_ran_4g_baseparameter (" + trns_cols + ")  VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
            logger.debug("ran:c3p_ran:createImportRecordTransactionTable::sql - %s", sql)
            mycursor.execute(sql, val)
            mydb.commit()

        respns="0"

    except Exception as err:

        respns="1"
        logger.error("ran:c3p_ran:createImportRecordTransactionTable::Error - %s", err)
    finally:
        mydb.close
        return respns



def create_import_id():
    #return ("IRBP"+ (datetime.now().strftime('%Y%m%d%H%M%S%f')[0:16]))
    return ("IMRBPR" + (datetime.now().strftime('%Y%m%d%H%M%S%f')[0:14]) + ''.join(
            random.choices(string.ascii_uppercase, k=1)))


def retImportData(input_data):
    try:
        mydb = Connections.create_connection()
        mycursor = mydb.cursor(buffered=True)
        logger.debug("ran:c3p_ran:retImportData::importId - %s", input_data["importId"])
        logger.debug("ran:c3p_ran:retImportData::SourceSystem - %s", input_data["sourceSystem"])
        importId=input_data["importId"]
        logger.debug("ran:c3p_ran:retImportData::importId - %s", importId)

        SourceSystem=input_data["sourceSystem"]
        logger.debug("ran:c3p_ran:retImportData::SourceSystem - %s", SourceSystem)

        cols = 'ir4_fbp_vendor,ir4_fbp_family,ir4_fbp_techno,ir4_fbp_name,ir4_fbp_para,ir4_fbp_para_type,ir4_fbp_exsheet_cata,ir4_fbp_value1,ir4_fbp_value2,ir4_fbp_created_date,ir4_fbp_created_by,ir4_fbp_updated_by,ir4_fbp_updated_date,ir4_fbp_importid,ir4_fbp_source_system'

        query = "SELECT " + cols + " FROM c3p_t_imp_ran_4g_baseparameter where ir4_fbp_importid = %s and ir4_fbp_source_system = %s"
        logger.debug("ran:c3p_ran:retImportData::query - %s", query)
        mycursor.execute(query, (importId, SourceSystem, ))
        rows = mycursor.fetchall()
        logger.debug("ran:c3p_ran:retImportData::rows - %s", rows)
        response={}
        res=[]
        for i in rows:
          res.append({"vendor":i[0],
            "family": i[1],
            "technology": i[2],
            "name": i[3],
            "parameter": i[4],
            "type": i[5],
            "category": i[6],
            "previousValue": i[7],
            "currentValue": i[8],
            "createdDate": i[9],
            "createdBy": i[10],
            "updatedBy": i[11],
            "updatedDate": i[12],
            "importId": i[13],
            "sourceSystem": i[14]
            })
        response["updatedTempltData"]=res
    except Exception as err:
        logger.error("ran:c3p_ran:retImportData::Error - %s", err)
    finally:
        mydb.close
        return response