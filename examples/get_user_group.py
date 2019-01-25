#!/usr/bin/env python

import argparse
import json

from blackduck.HubRestApi import HubInstance

hub = HubInstance()


parser = argparse.ArgumentParser("Get a user group")
parser.add_argument("group_name")
parser.add_argument("--add_roles", action='store_true', help="Add the global roles assigned to the user group to the output")

args = parser.parse_args()

usergroup = hub.get_user_group_by_name(args.group_name)

if usergroup:
	print(json.dumps(usergroup))
	if args.add_roles:
		roles_url = hub.get_roles_url_from_user_or_group(usergroup)
		response = hub.execute_get(roles_url)
		if response and response.status_code == 200:
			print(json.dumps(response.json()))
else:
	print("Did not find a user group with the name {}".format(args.group_name))

