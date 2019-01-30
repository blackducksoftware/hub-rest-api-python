#!/usr/bin/env python

from blackduck.HubRestApi import HubInstance

import argparse
import json

parser = argparse.ArgumentParser()
parser.add_argument("project_name")
parser.add_argument("version_name")
parser.add_argument("--attribute", 
	choices=['createdAt', 'createdBy', 'lastScanDate'],
	help="Select an attribute you want to print instead of the whole JSON payload")
args = parser.parse_args()

hub = HubInstance()

project = hub.get_project_by_name(args.project_name)
if project:
	version = hub.get_version_by_name(project, args.version_name)

	if version:
		if args.attribute:
			print(version[args.attribute])
		else:
			print(json.dumps(version))