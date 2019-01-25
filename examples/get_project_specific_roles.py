'''
Created on January 25, 2019

@author: gsnyder

Get the list of project specific roles as shown in the GUI when you assign a user or user group to a project

'''
import json

from blackduck.HubRestApi import HubInstance

hub = HubInstance()

project_specific_roles = hub.get_project_roles()

print(json.dumps(project_specific_roles))