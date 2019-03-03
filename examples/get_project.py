'''
Created on Nov 14, 2018

@author: gsnyder

Print a project given its name

'''

from blackduck.HubRestApi import HubInstance

import argparse
import json

parser = argparse.ArgumentParser()

link_choices = [
	'versions',
	'canonicalVersion',
	'assignable-users',
	'assignable-usergroups',
	'users',
	'usergroups',
	'tags',
	'project-mappings'
]
parser.add_argument("--limit")
parser.add_argument("project_name")
parser.add_argument("--link", default=None, choices = link_choices, help="If provided, will result in a GET on the corresponding project link")

args = parser.parse_args()

hub = HubInstance()

project = hub.get_project_by_name(args.project_name)

print(json.dumps(project))

if args.link:
	print(json.dumps(hub.get_project_info(args.project_name, args.link)))