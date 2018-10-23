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
	"overridable":"true",
	"name":"cannot-use-reciprocal-with-un-approved-component",
	"description":"Reject use of a component that is governed by a reciprocal license and the approval status is not Approved",
	"severity":"BLOCKER",
	"policyType":"BOM_COMPONENT_DISALLOW",
	"expression":
		{"operator":"AND",
		"expressions":[
				{"name":"LICENSE_FAMILY",
				"operation":"EQ",
				"parameters":{
					"values":[
						"RECIPROCAL"
						]
					}
				},
				{"name":"COMPONENT_APPROVAL_STATUS",
				"operation":"NE",
				"parameters":{
					"values":[
						"APPROVED"
						]
					}
				}
			]
		}
	})

policy_url = hub.create_policy(policy_json)
print("Policy created is located at: {}".format(policy_url))
