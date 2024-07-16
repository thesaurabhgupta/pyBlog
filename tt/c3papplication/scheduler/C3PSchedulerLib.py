
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.combining import AndTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from c3papplication.common import Connections
from c3papplication.conf.springConfig import springConfig
from jproperties import Properties
import time,json,logging
import requests
import pytz
import mysql.connector

configs = springConfig().fetch_config()

logger = logging.getLogger(__name__)

def updateScheduerHistoryTable(scheduleid,statuscode,schd_type):
    mydb = Connections.create_connection()
    try:
        res=""
        mycursor = mydb.cursor(buffered=True)
        now = datetime.today().strftime('%Y-%m-%d %H:%M:%S')
        mycursor.execute("update c3p_scheduler_history set sh_status = '"+statuscode+"', sh_update_by = 'system' ,sh_update_datetime = '"+ now+"'where sh_schedule_id='"+scheduleid+"'")
        mydb.commit()
    except mysql.connector.errors.ProgrammingError as err:
        logger.error('updateScheduerHistoryTable - Error -%s',err)
    finally:
        mydb.close
    return res

def InitiateNewRequest(json,url):
    response = ""
    API_ENDPOINT = url
    HEADERS = {"Content-type": "application/json", "Accept":"application/json"}
    response = requests.post(API_ENDPOINT, data=json, headers=HEADERS)
    logger.debug('c3p service response :: %s', response.text)
    return response

def InitiateCamundaWorkflow(json):
    response = ""
    API_ENDPOINT = configs.get("CAMUNDA_WORKFLOW_NEW_REQUEST_START")
    HEADERS = {"Content-type": "application/json", "Accept":"application/json"}
    response = requests.post(API_ENDPOINT, data=json, headers=HEADERS)
    logger.info('Scheduler flow::::workflow status :: %s', response)
    return response

def startExecution(scheduleID,requestID,creatorName,endDate):
    mydb = Connections.create_connection()
    logger.info('Schedule triggered:: %s', datetime.now())
    #Based on schedule id check for schedule type
    mycursor = mydb.cursor(buffered=True)
    try:
        mycursor.execute("SELECT sh_sch_type,sh_status,sh_rowid,sh_request_id,sh_end_datetime FROM c3p_scheduler_history  where sh_schedule_id='"+scheduleID+"'")
        myresult = mycursor.fetchone()
        schd_type=myresult[0]
        schd_status = myresult[1]
        schd_request_id = myresult[3]
        schd_end_date=myresult[4]
        logger.info("Schdtype::::%s",schd_type)
        if 'O' in schd_type:
        #Form json to start camunda workflow
            workflow_json = json.dumps({'businessKey':schd_request_id,'variables':{'version':{'value':'1.0'},'user':{'value':creatorName},'requestType':{'value':requestID[0:4]}}})
            workflow_start_status = InitiateCamundaWorkflow(workflow_json)
            if workflow_start_status == 200:
                updateScheduerHistoryTable(scheduleID,"Executed",schd_type)
        elif 'R' in schd_type:
            if 'Scheduled' in schd_status:
                workflow_json = json.dumps({'businessKey':schd_request_id,'variables':{'version':{'value':'1.0'},'user':{'value':creatorName},'requestType':{'value':requestID[0:4]}}})
                workflow_start_status = InitiateCamundaWorkflow(workflow_json)
                if workflow_start_status.status_code == 200:
                    updateScheduerHistoryTable(scheduleID,"Executed",schd_type)
            elif 'Executed' in schd_status:
                #now = datetime.today().strftime('%Y-%m-%d %H:%M:%S')
                #dbenddate=schd_end_date.strftime('%Y-%m-%d %H:%M:%S')
                updateScheduerHistoryTable(scheduleID,"Executed",schd_type)
                mycursor.execute("SELECT sh_create_json,sh_create_url FROM c3p_scheduler_history  where sh_schedule_id='"+scheduleID+"'")
                resultforjson = mycursor.fetchone()
                schd_create_json=resultforjson[0]
                schd_create_url=resultforjson[1]
                logger.debug('URL create::%s',schd_create_url)
                c3p_service_status=InitiateNewRequest(schd_create_json,schd_create_url)
    except mysql.connector.errors.ProgrammingError as err:
        logger.error('startExecution - Error -%s',err)
    finally:
        mydb.close    
            #Logic to create new request
    #If it is one time- change schedule status to executed, set updated date time and updated by system, start camunda workflow
    #If it is recurring - if schedule status is scheduled pass request id to camunda workflow and change schedule status to in progress update 
    #                       if schedule status is in progress based to request id fetch info from requestinfo form json and fire /create endpoint

def getFormattedDate(input,inputtz):
    appservertimezone = configs.get('APP_SERVER_TIMEZONE')
    originaltz = pytz.timezone(inputtz)
    appServerTz = pytz.timezone(appservertimezone)
    dateObj = datetime.strptime(str(input),"%Y-%m-%dT%H:%M")
    localized_timestamp = originaltz.localize(dateObj)
    new_timezone_timestamp = localized_timestamp.astimezone(appServerTz)
    logger.debug('finaldate::%s',new_timezone_timestamp)
    return new_timezone_timestamp

def addJobMtd(data,scheduler):
    triggerType=data.get('trigger')
    requestID=data.get('requestID')
    job = ""
    # codeql [py/log-injection]: Suppressing log injection rule
    logger.info("Trigger type::%s",triggerType) # nosem: python.logging.security.injection
    if 'interval' in triggerType:
        intervalTime = data.get('intervalTime')
        intervalUnit = data.get('intervalTimeUnit')
        startDate = data.get('startDate')
        endDate = data.get('endDate')
        scheduleID = data.get('scheduleID')
        creatorName = data.get('creatorName')
        timezone = data.get('timezone')
        stDateFormatted = getFormattedDate(startDate,timezone)
        endDateFormatted = getFormattedDate(endDate,timezone)
        if 'hour' in intervalUnit:
            job = scheduler.add_job(startExecution, 'interval', hours=intervalTime, start_date=stDateFormatted, end_date=endDateFormatted,args=[scheduleID,requestID,creatorName,endDate])
        elif "second" in intervalUnit:
            job = scheduler.add_job(startExecution, 'interval', seconds=intervalTime, start_date=stDateFormatted, end_date=endDateFormatted,args=[scheduleID,requestID,creatorName,endDate])
        elif "minute" in intervalUnit:
            job = scheduler.add_job(startExecution, 'interval', minutes=intervalTime, start_date=stDateFormatted, end_date=endDateFormatted,args=[scheduleID,requestID,creatorName,endDate])
    elif 'schedulerun' in triggerType:
        startDate = data.get('startDate')
        scheduleID = data.get('scheduleID')
        creatorName = data.get('creatorName')
        endDate = data.get('endDate')
        timezone = data.get('timezone')
        stDateFormatted = getFormattedDate(startDate,timezone)
        job = scheduler.add_job(startExecution, trigger='date', next_run_time=stDateFormatted,args=[scheduleID,requestID,creatorName,endDate])
    elif 'cron' in triggerType:
        scheduleID = data.get('scheduleID')
        creatorName = data.get('creatorName')
        endDate = data.get('endDate')
        bit = ""
        weekdays="0"
        m="0"
        d="0"
        h="0"
        if 'month' in data:
            m="1"
            month = data.get('month')
        if 'day' in data:
            d="1"
            day = data.get('day')
        if 'hour' in data:
            h="1"
            hour = data.get('hour')
        if 'dayOfWeek' in data:
            weekdays = "1"
            dayofweek  = data.get('dayOfWeek')
        bit = m+d+h+weekdays
        if "1111" in bit:
            job = scheduler.add_job(startExecution, 'cron', month=month, day=day, hour=hour, day_of_week=dayofweek,args=[scheduleID,requestID,creatorName,endDate])
        elif "1110" in bit:
            job = scheduler.add_job(startExecution, 'cron', month=month, day=day, hour=hour,args=[scheduleID,requestID,creatorName,endDate])
        elif "0011" in bit:
            job = scheduler.add_job(startExecution, 'cron', hour=hour, day_of_week=dayofweek,args=[scheduleID,requestID,creatorName,endDate])
    elif 'combination' in triggerType:
        scheduleID = data.get('scheduleID')
        intervalTime = data.get('intervalTime')
        intervalUnit = data.get('intervalTimeUnit')
        dayofweek  = data.get('dayOfWeek')
        startDate = data.get('startDate')
        endDate = data.get('endDate')
        timezone = data.get('timezone')
        stDateFormatted = getFormattedDate(startDate,timezone)
        endDateFormatted = getFormattedDate(endDate,timezone)
        creatorName = data.get('creatorName')
        endDate = data.get('endDate')
        if 'hours' in intervalUnit:
            trigger = AndTrigger([IntervalTrigger(hours=intervalTime,start_date=stDateFormatted,end_date=endDateFormatted),
                      CronTrigger(day_of_week=dayofweek)])
            job =scheduler.add_job(startExecution, trigger,args=[scheduleID,requestID,creatorName,endDate])
        elif 'minutes' in intervalUnit:
            trigger = AndTrigger([IntervalTrigger(minutes=intervalTime,start_date=stDateFormatted,end_date=endDateFormatted),
                      CronTrigger(day_of_week=dayofweek)])
           
            job =scheduler.add_job(startExecution, trigger,args=[scheduleID,requestID,creatorName,endDate])
           
        elif 'seconds' in intervalUnit:
            trigger = AndTrigger([IntervalTrigger(seconds=intervalTime,start_date=stDateFormatted,end_date=endDateFormatted),
                      CronTrigger(day_of_week=dayofweek)])
            job =scheduler.add_job(startExecution, trigger,args=[scheduleID,requestID,creatorName,endDate])
 
    return job