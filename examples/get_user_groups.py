'''
Created on Dec 4, 2018

@author: gsnyder

Get a list of user objects

'''
import json

from blackduck.HubRestApi import HubInstance

hub = HubInstance()

user_groups = hub.get_user_groups()

if 'totalCount' in user_groups and user_groups['totalCount'] > 0:
	print(json.dumps(user_groups))
else:
	print("No user_groups found")