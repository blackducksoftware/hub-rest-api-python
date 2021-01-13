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

codelocations = hub.get_codelocations(limit=1, offset=1)
total_count = codelocations['totalCount']

print("{} codelocations in the database".format(total_count))
#print(json.dumps(codelocations, indent=2))

scan_status = {}

offset=0
while offset < total_count:
    hub = HubInstance()
    codelocations = hub.get_codelocations(limit=batch_size, offset=offset)
    for codelocation in codelocations['items']:
        scan_summaries = hub.get_codelocation_scan_summaries(code_location_obj=codelocation)
        for item in scan_summaries['items']:
            status = item['status']
            if status in scan_status.keys():
                scan_status[status] += 1
            else:
                scan_status[status] = 1
    offset += batch_size
    print (json.dumps(scan_status, indent=2))
