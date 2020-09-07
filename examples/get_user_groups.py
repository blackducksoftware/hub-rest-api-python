#!/usr/bin/python3

'''
Created on Dec 4, 2018

@author: gsnyder

Get a list of user objects

'''
import json

from blackduck.HubRestApi import HubInstance

hub = HubInstance()

user_groups = hub.get_user_groups(parameters = {"limit":"50000"})

if 'totalCount' in user_groups and user_groups['totalCount'] > 0:
    for group in user_groups['items']:
        if group['createdFrom'] == 'INTERNAL' and not group['name'].endswith("DEPRECATED"):
            #print(json.dumps(group))
            print('---------------------------------------------------------')
            print(f"== {group['name']}")
            usergroup_url = group['_meta']['href'] + '/users?limit=10000'
            response = hub.execute_get(usergroup_url)
            users = response.json()
            #print(users)
            for user in users['items']:
                if user['active'] and user['type'] == 'EXTERNAL':
                    print(user['userName'])

            print('--------')
            projects_url = group['_meta']['href'] + '/projects?limit=10000'
            response = hub.execute_get(projects_url)
            projects = response.json()
            #print(projects)
            for project in projects['items']:
                #project_url = project['project']
                #project_id = project_url.rsplit('/', 1)[-1]
                #print(project_id)
                print(f"'{project['name']}',")
            
            
else:
	print("No user_groups found")