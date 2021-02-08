#!/usr/bin/env python

'''
Created on July 27, 2020

@author: gsnyder

Set (or clear) the component adjustments flag on projects

'''

import argparse
import json
import logging
import sys

from blackduck.HubRestApi import HubInstance, object_id

parser = argparse.ArgumentParser("Set (or clear) the component adjustments flag on project(s)")
parser.add_argument("-p", "--project", help="If supplied, set (or clear) the component adjustments flag for a specific project. Otherwise, perform the action on all projects on the system.")
parser.add_argument("-c", "--clear", action='store_true', help="Default action is to set the component adjustments flag on the project (or all projects). Use this flag to clear the component adjustments flag")
parser.add_argument("-t", "--test", action='store_true', help="Test mode. Will only list the projects and action to be taken")

args = parser.parse_args()

logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stderr, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

hub = HubInstance()

if args.project:
    projects = [hub.get_project_by_name(args.project)]
else:
    projects = hub.get_projects().get('items', [])

action = "Setting" if not args.clear else "Clearing"
project_names = ",".join([p['name'] for p in projects])
logging.debug(f"{action} the following projects: {project_names}")

component_adjustments = not args.clear
status = "set" if not args.clear else "cleared"
for project in projects:
    if project['projectLevelAdjustments'] == component_adjustments:
        logging.debug(f"Project {project['name']}'s component adjustment flag is already {status}")
    else:
        project['projectLevelAdjustments'] = component_adjustments
        url = project['_meta']['href']

        if not args.test:
            response = hub.execute_put(url, data=project)
            if response.status_code == 200:
                logging.info(f"Successfully {status} projectLevelAdjustments for project {project['name']}")
            else:
                logging.error(f"Failed to {status} projectLevelAdjustments for project {project['name']}, status code returned was {response.status_code}")
        else:
            logging.debug(f"Test mode: Would have {status} projectLevelAdjustments for project {project['name']}")
