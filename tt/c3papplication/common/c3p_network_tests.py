from datetime import datetime
from flask import jsonify
import json
import concurrent.futures
import ipaddress
import time
from pythonping import ping
import socket
import logging
from c3papplication.ipmanagement import c3p_jumpssh
from c3papplication.common import Connections

logger = logging.getLogger(__name__)

""" Author: Ruchita Salvi"""
""" Date: 13/1/2021"""

""" Function to perfrom the throughput test against any IP Address """

def performThroughputClient(contentJson):
    json_data = {}
    response=""
    count = contentJson.get('packetCount', 30)
    BUFSIZE = contentJson.get('bufferSize', 1024)
    try:
        port = int(contentJson.get('srcMgmtPort', 22))
    except ValueError:
        port = 22
    host = contentJson['srcMgmtIP']
    
    mydb = Connections.create_connection()
    mycursor = mydb.cursor(buffered=True)
    sql = "select d_id,d_connect from c3p_deviceinfo where d_mgmtip = %s"
    logger.debug("c3p_deviceinfo - sql here :: %s", sql)
    mycursor.execute(sql, (host,))
    devinfo = mycursor.fetchone()
    deviceid=devinfo[0]
    if devinfo[1]=="JSSH":
        response=c3p_jumpssh.throughputCalculation(deviceid)
    else:    
        testdata = 'x' * (BUFSIZE-1) + '\n'
        t1 = time.time()
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        t2 = time.time()
        s.connect((host, port))
        try:
            #s.connect((host, port))
            t3 = time.time()
            i = 0
            while i < count:
                try:
                    i = i+1
                    s.send(testdata.encode())
                except socket.error:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.connect((host, port)) 
            s.shutdown(1) # Send EOF
            t4 = time.time()
            data = s.recv(BUFSIZE)
            t5 = time.time()
            #print('count', count)
            #print (data)
            #print ('Raw timers:', t1, t2, t3, t4, t5)
            #print ('Intervals:', t2-t1, t3-t2, t4-t3, t5-t4)
            #print ('Total:', t5-t1)
            #print ('Throughput:', round((BUFSIZE*count*0.001) / (t5-t1), 3),)
            #print ('K/sec.')
    
            throughput=round((BUFSIZE*count*0.001) / (t5-t1), 3)
            logger.debug('common:c3p_network_tests:throughput :: %s', throughput)
            if 'throughputUnit' not in contentJson :
                unit = 'Kbps'
            else : 
                expectedUnit = contentJson['throughputUnit']
                if(len(expectedUnit) == 0) :
                    unit = 'Kbps'
                else :
                    unit = expectedUnit
        
            if 'Mbps' in unit:
                throughput=round(throughput/1000,3)

            json_data['throughput'] = throughput
            json_data['unit'] = unit
            response = jsonify(json_data)
        except Exception as msg:
            logger.error('common:c3p_network_tests:throughput :: %s',msg)
            response = jsonify({"error": "Socket Error"})
    return response


def performPing(contentJson):
    
    """ setup parameters for the ping test """
    rIP = contentJson['ipAddress']
    pSize   =  contentJson['packetSize']
    pCount  = contentJson['packetCount']

    res = []

    pResponse = ping(rIP, size=pSize, count=pCount)

    for m in pResponse:
        res.append(str(m).replace(',',' ',2))
    pRes = {"ipAddress":rIP, "pingReply" : res, "min":pResponse.rtt_min_ms,"avg": pResponse.rtt_avg_ms, "max" : pResponse.rtt_max_ms}

    return pRes

def performLatency(contentJson):
    
    """ setup parameters for the ping test """
    rIP = contentJson['ipAddress']
    pSize   =  contentJson['packetSize']
    pCount  = contentJson['packetCount']
    res = []
    
    mydb = Connections.create_connection()
    mycursor = mydb.cursor(buffered=True)
    sql = "select d_id,d_connect from c3p_deviceinfo where d_mgmtip = %s"
    logger.debug("c3p_deviceinfo - sql here :: %s", sql)
    mycursor.execute(sql, (rIP,))
    devinfo = mycursor.fetchone()
    deviceid=devinfo[0]
    if devinfo[1]=="JSSH":
        command='ping -c '+ str(pCount)+' '+'-s '+str(pSize)+' ' + rIP
        logger.debug("inside JSSH command:%s",command)
        jRes=c3p_jumpssh.connectJumpHost(command,deviceid)
        pRes=c3p_jumpssh.jumpLatencyParser(jRes)
    else: 
        pResponse = ping(rIP, size=pSize, count=pCount)

        for m in pResponse:
            res.append(str(m).replace(',',' ',2))
        pRes = {"ipAddress":rIP, "pingReply" : res, "latency": str(pResponse.rtt_avg_ms) + "ms"}

    return pRes

def performFrameloss(contentJson):
    """ setup parameters for the frameloss test """
    rIP = contentJson['ipAddress']
    pSize   =  contentJson['packetSize']
    pCount  = contentJson['packetCount']

    res = []
    mydb = Connections.create_connection()
    mycursor = mydb.cursor(buffered=True)
    sql = "select d_id,d_connect from c3p_deviceinfo where d_mgmtip = %s"
    logger.debug("c3p_deviceinfo - sql here :: %s", sql)
    mycursor.execute(sql, (rIP,))
    devinfo = mycursor.fetchone()
    deviceid=devinfo[0]
    if devinfo[1]=="JSSH":
        command='ping -c '+ str(pCount)+' '+'-s '+str(pSize)+' ' + rIP
        logger.debug("inside JSSH command:%s",command)
        jRes=c3p_jumpssh.connectJumpHost(command,deviceid)
        pRes=c3p_jumpssh.jumpFramelossParser(jRes)
    else: 
        pResponse = ping(rIP, size=pSize, count=pCount)

        for m in pResponse:
            res.append(str(m).replace(',',' ',2))
        numberOfFramesLost = 0
        for line in res:
            if "Reply from" not in line:
                numberOfFramesLost = numberOfFramesLost + 1
        
        if(numberOfFramesLost != 0):
            percentLoss = (numberOfFramesLost/100)*len(res) 
        else:
            percentLoss = 0

        pRes = {"ipAddress":rIP, "pingReply" : res, "frameloss": str(percentLoss) + "%"}

    return pRes   