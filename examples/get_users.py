'''
Created on Dec 4, 2018

@author: gsnyder

Get a list of user objects

'''
import json

from blackduck.HubRestApi import HubInstance

hub = HubInstance()

users = hub.get_users()

if 'totalCount' in users and users['totalCount'] > 0:
	print(json.dumps(users))
else:
	print("No users found")
