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


cleanup = len(argv) > 1
hub = HubInstance()

response = hub.get_codelocations(limit=5000)
totalCount=response['totalCount']
locationlist=response['items']

print (totalCount)

scanned = 0
notmapped = 0

for location in locationlist:
    href = location['_meta']['href']
    name = location['name']
    mappedTo = location.get('mappedProjectVersion', None)
    if not mappedTo:
        notmapped += 1
        print ("Location {} has no mapping".format(name))
        if cleanup:
            print (hub.execute_delete(href))
    scanned += 1

print ("Scanned {} codelocations, {} have no mapped project".format(scanned, notmapped))     
    
