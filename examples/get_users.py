'''
Created on Dec 4, 2018

@author: gsnyder

Get a list of user objects

'''
import json

from blackduck.HubRestApi import HubInstance

hub = HubInstance()

users = hub.get_users()

#
# Note: The HubInstance interface does NOT handle paging of results
#	but the new Client interface does. See https://github.com/blackducksoftware/hub-rest-api-python/blob/master/examples/client/get_users.py
# 	for an example of retrieving users using the new Client interface
#
if 'totalCount' in users and users['totalCount'] > 0:
	print(json.dumps(users))
else:
	print("No users found")
