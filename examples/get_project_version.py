#!/usr/bin/env python

from blackduck.HubRestApi import HubInstance

import argparse
import json

parser = argparse.ArgumentParser()
parser.add_argument("project_name")
parser.add_argument("version_name")
args = parser.parse_args()

hub = HubInstance()

project = hub.get_project_by_name(args.project_name)
if project:
	version = hub.get_version_by_name(project, args.version_name)

	if version:
		print(json.dumps(version))