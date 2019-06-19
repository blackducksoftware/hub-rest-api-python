'''
Created on April 26, 2019

@author: amacdonald

Assign a user to a project, providing the project-specific roles the user group should have (on the project)

Largely taken from assign_user_group_to_project, credit to gsnyder

'''

import argparse
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

parser = argparse.ArgumentParser("Assign a user to a project along with a list of project roles (optional)")
parser.add_argument("user", help="The name of a user to assign to the project")
parser.add_argument("project", help="The name of the project you want to assign the user to")
parser.add_argument(
	"--project_roles", help="A file with the project-specific roles ({}) that will be granted to the user, one per line".format(
		project_roles_str))
parser.add_argument("--roles_list", nargs="+", help="The list of roles user should have.")

args = parser.parse_args()

logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stdout, level=logging.DEBUG)

hub = HubInstance()

if args.project_roles:
	project_roles_l = list()
	with open(args.project_roles) as f:
		project_roles_l = [role.strip() for role in f.readlines()]
elif args.roles_list:
	project_roles_l = args.roles_list
	print('-----------------------')
	print(project_roles_l)
	for role in args.roles_list:
		role = project_roles_l
else:
	project_roles_l = []

response = hub.assign_user_to_project(args.user, args.project, project_roles_l)

if response and response.status_code == 201:
	logging.info("Successfully assigned user {} to project {} with project-roles {}".format(
		args.user, args.project, project_roles_l))
else:
	logging.warning("Failed to assign user {} to project {}".format(args.user, args.project))