#!/usr/bin/env python

import argparse
import json

from blackduck.HubRestApi import HubInstance

hub = HubInstance()

global_roles = [
		"Component Manager",
		"Global Code Scanner",
		"License Manager",
		"Policy Manager",
		"Project Creator",
		"Super User",
		"System Administrator",
		"All"
	]

parser = argparse.ArgumentParser("Assign a global role to a user group")
parser.add_argument("group_name", help="The user group name")
parser.add_argument("role", choices=global_roles, help="Assign a global role to the user group. If you choose 'All' then all global roles will be assigned to the user group")

args = parser.parse_args()

user_groups = hub.get_user_groups(parameters={'q':args.group_name})

if user_groups['totalCount'] == 1:
	user_group = user_groups['items'][0]

if user_group:
	if args.role == 'All':
		roles_to_assign = [r for r in global_roles if r != 'All']
	else:
		roles_to_assign = [args.role]
	for role_to_assign in roles_to_assign:
		response = hub.assign_role_to_user_or_group(role_to_assign, user_group)
		if response.status_code == 201:
			print("Successfully assigned role {} to user group {}".format(role_to_assign, args.group_name))
		elif response.status_code == 412:
			print("Failed to assign role {} to group {} due to status code 412. Has the role already been assigned?".format(role_to_assign, args.group_name))
		else:
			print("Failed to assign role {} to group {}. status code: {}".format(role_to_assign, args.group_name, response.status_code))
