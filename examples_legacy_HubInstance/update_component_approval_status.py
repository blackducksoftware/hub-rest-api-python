#!/usr/bin/env python

'''
Created on Oct 14, 2018

@author: gsnyder

Updates the approval status for a component given it's component ID

'''
from blackduck.HubRestApi import HubInstance
from pprint import pprint
from sys import argv

hub = HubInstance()

component_id = argv[1]
component_info = hub.get_component_by_id(component_id)

if "approvalStatus" in component_info:
	print("Component data before update:")
	pprint(component_info)
	update_body = component_info
	update_body["approvalStatus"] = "APPROVED"
	try:
		hub.update_component_by_id(component_id, update_body)
	except:
		print("Failed to update approval status for component ({})".format(component_id))
	print("\n\nComponent data after update:")
	pprint(hub.get_component_by_id(component_id))
