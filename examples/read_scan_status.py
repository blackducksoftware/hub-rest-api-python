'''
Created on Jan 13, 2021

@author: kumykov
'''
from blackduck.HubRestApi import HubInstance
import json
import os
import requests


hub=HubInstance()

batch_size=500

codelocations = hub.get_codelocations(limit=1)
total_count = codelocations['totalCount']

status = {"in_progress": 0, "unstarted": 0, "completed": 0, "error": 0, "skipped": 0}

for i in status.keys():
    codelocations = hub.get_codelocations_internal(limit=1, parameters={"filter": "codeLocationStatus:{}".format(i)})
    status[i] = codelocations['totalCount']
    
print (total_count, status)

