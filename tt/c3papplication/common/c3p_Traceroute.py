'''
Name    : c3p_traceroute Program histroy
Date    : 23rd Sept 2020
Author  : 
Description  :
'''

from icmplib import ping, multiping, traceroute, Host, Hop
import sys
import socket
import logging, logging.config
from os import path

#log_file_path = path.join(path.dirname(path.abspath(__file__)), 'conf/logging.conf')
#logging.config.fileConfig(log_file_path, disable_existing_loggers=False)
logger = logging.getLogger(__name__)
def get_route(hostname):
    hops = traceroute(dest_addr, max_hops=10, fast_mode=False)
    logger.debug('Distance (ttl)    Address    Average round-trip time')
    last_distance = 0

    for hop in hops:
        if last_distance + 1 != hop.distance:
            logger.debug('Some routers are not responding')
		
        # See the Hop class for details
        print(f'{hop.distance}    {hop.address}    {hop.avg_rtt} ms')
        last_distance = hop.distance	 
	
	
if __name__ == "__main__":
    dest_name = sys.argv[1]
    dest_addr = socket.gethostbyname(dest_name)
    logger.debug ("traceroute to %s (%s)", dest_name, dest_addr)
    get_route(dest_addr)

