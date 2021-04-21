'''
Created on Aug 1, 2018

@author: kumykov

Execute batch request  
'''
from sys import argv,exit
from blackduck.HubRestApi import HubInstance

def print_usage():
    print("\n\n\t python3 {} urllist ".format(argv[0]))


#
# main
# 

if (len(argv) < 2):
    print_usage()
    exit()

with open(argv[1], "r") as f:
    urllist = [x.strip() for x in f.readlines()]
     
hub = HubInstance()

for url in urllist:
    print ("Processing {} ".format(url))
    print(hub.execute_get(url))
    print(hub.execute_delete(url))
