#!/usr/bin/python3 

import argparse
import json

from blackduck.HubRestApi import HubInstance

# ------------------------------------------------------------------------------
# Parse command line

parser = argparse.ArgumentParser(
    formatter_class=argparse.RawDescriptionHelpFormatter,
    description='Rename user groups on blackduck.com from the Azure UUID to their name',
)


parser.add_argument('--file', '-f', type=str, required=True, help='Export file from Azure with the UUID to group name mapping')

args = parser.parse_args()

# ------------------------------------------------------------------------------
# Functions

azure_map = {}
   
def read_file(filename):
    with open(filename) as file:
        line = file.readline()       
        while line:
            parts = line.split(',')
            if parts[2] == "Security":
                azure_map[parts[0]] = parts[1]
            line = file.readline()  
    
# ------------------------------------------------------------------------------  
# Main code

read_file(args.file)
#print(azure_map)

hub = HubInstance()
user_groups = hub.get_user_groups(parameters = {"limit":"50000"})
for group in user_groups['items']:
    if group.get('externalName') and group['name'] == group['externalName']:
        new_name = azure_map.get(group['name'])
        usergroup_url = group['_meta']['href']
        if new_name:
            #print(group)
            print(f"{group['name']} => {new_name} => {usergroup_url}" )
            json = {
                "name": new_name,
                "active": True,
                "createdFrom": "SAML",
                "default": False,
                "externalName": group['externalName']
            }
            
            #print(json)
            response = hub.execute_put(usergroup_url, json)
            #print(response)
        else:
            print(f"No name found for {group['name']} => {usergroup_url}" )

