'''
Created on May 1, 2019

@author: amacdonald

Assign users to a project, providing the project-specific roles the user group should have (on the project) from a CSV file


'''

import csv
import logging
import argparse
import sys

from blackduck.HubRestApi import HubInstance

hub = HubInstance()


project_roles = [
		"BOM Manager",
		"Policy Violation Reviewer",
		"Project Code Scanner",
		"Project Manager",
		"Security Manager",
	]

project_roles_str = ",".join(project_roles)

parser = argparse.ArgumentParser("Add users to project(s) with assigned roles (optional) from CSV file")
parser.add_argument("CSV", help="Location of the CSV file to import")
                    # "CSV File requires three columns titled 'User,' 'Project,' and 'Roles.'",
                    # "In the 'Roles' column, separate the roles to assign with a ',' and no spaces")

args = parser.parse_args()

logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stdout, level=logging.DEBUG)

if args.CSV:
    with open(args.CSV, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            project = (row['Project'])
            user = (row['User'])
            roles = (row['Roles'])
            roles_l = []
            roles = roles.split(',')
            if roles:
                for x in range(len(roles)):
                    project_roles_l = roles

            else:
                project_roles_l = []

            response = hub.assign_user_to_project(user, project, project_roles_l)

            if response and response.status_code == 201:
                 logging.info("Successfully assigned user {} to project {} with project-roles {}".format(user, project, project_roles_l))
            else:
                logging.warning("Failed to assign user {} to project {}".format(user, project))
            print('----------------------')