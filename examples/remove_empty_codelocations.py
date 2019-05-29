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

print(hub.delete_unmapped_codelocations())