'''
Created on January 21, 2019

@author: gsnyder

Assign a user group to a project, providing the project-specific roles the user group should have (on the project)

'''

import argparse
import json
import logging
import sys

from blackduck.HubRestApi import HubInstance


project_roles = [
		"BOM Manager",
		"Policy Violation Reviewer",
		"Project Code Scanner",
		"Project Manager",
		"Security Manager",
	]

project_roles_str = ",".join(project_roles)

parser = argparse.ArgumentParser("Assign a user group to a project along with a list of project roles (optional)")
parser.add_argument("group", help="The name of a user group to assign to the project")
parser.add_argument("project", help="The name of the project you want to assign the group to")
parser.add_argument(
	"--project_roles", help="A file with the project-specific roles ({}) that will be granted to the user group, one per line".format(
		project_roles_str))

args = parser.parse_args()

logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stdout, level=logging.DEBUG)

hub = HubInstance()

if args.project_roles:
	project_roles_l = list()
	with open(args.project_roles) as f:
		project_roles_l = [role.strip() for role in f.readlines()]
else:
	project_roles_l = []

response = hub.assign_user_group_to_project(args.project, args.group, project_roles_l)
if response and response.status_code == 201:
	logging.info("Successfully assigned user group {} to project {} with project-roles {}".format(
		args.group, args.project, project_roles_l))
else:
	logging.warning("Failed to assign group {} to project {}".format(args.group, args.project))