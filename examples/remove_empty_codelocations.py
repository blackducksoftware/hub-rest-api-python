'''
Created on Jul 19, 2018

@author: kumykov

Removes scanlocation wthat are not mapped to any project

'''
from blackduck.HubRestApi import HubInstance
from sys import argv
#
# main
# 

# TODO: Delete older scans? X oldest?


hub = HubInstance()

codelocations = hub.get_codelocations()
for location in codelocations['items']:
    print (location)
    print (hub.get_codelocation_scan_summaries(location['_meta']['href'].split('/')[5]))
