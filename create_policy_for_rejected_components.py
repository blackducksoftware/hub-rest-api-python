#!/usr/bin/env python

'''
Created on Oct 14, 2018

@author: gsnyder

Create a policy that prevents use of any rejected component

'''
from bds.HubRestApi import HubInstance
import json
from pprint import pprint
from sys import argv

hub = HubInstance()

policy_json = json.dumps(
	{"enabled":"true",
	"overridable": "true",
	"name":"cannot-use-rejected-component",
	"description":"You cannot use components we have rejected.",
	"severity":"BLOCKER",
	"policyType":"BOM_COMPONENT_DISALLOW",
	"expression":{
		"operator":"AND","expressions":[
			{"name":"COMPONENT_APPROVAL_STATUS","operation":"EQ","parameters":{"values":["REJECTED"]}}
			]
		}
	})

policy_url = hub.create_policy(policy_json)
print("Policy created is located at: {}".format(policy_url))
