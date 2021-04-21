'''
Created on Apr 28, 2020

@author: kumykov
'''

from blackduck.HubRestApi import HubInstance

import argparse
import json

parser = argparse.ArgumentParser()

parser.add_argument("project_name")
parser.add_argument("version_name")

args = parser.parse_args()

hub = HubInstance()

version = hub.get_project_version_by_name(args.project_name, args.version_name)

# print(json.dumps(version, indent=2))

links=version['_meta']['links']

for link in links:
    if link['rel'] == 'vulnerable-components':
        url = link['href']
        
print (url)
positive_filter_string='?filter=ignored:true'
negative_filter_string='?filter=ignored:false'

result = hub.execute_get(url)
#print (json.dumps(result.json(), indent=2))
print ("Total Number of vulnerabilities: {}".format(result.json()['totalCount']))

result = hub.execute_get(url+positive_filter_string)
#print (json.dumps(result.json(), indent=2))
print ("Number of ignored vulnerabilities: {}".format(result.json()['totalCount']))

result = hub.execute_get(url+negative_filter_string)
#print (json.dumps(result.json(), indent=2))
print ("Number of Not ignored vulnerabilities: {}".format(result.json()['totalCount']))

