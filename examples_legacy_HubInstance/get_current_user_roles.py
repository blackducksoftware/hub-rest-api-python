'''
Created on January 16, 2019

@author: gsnyder

Get the (global) roles for the current user
'''

import json


from blackduck.HubRestApi import HubInstance

hub = HubInstance()

current_user_roles = hub.get_roles_for_user_or_group(hub.get_current_user())

print(json.dumps(current_user_roles))