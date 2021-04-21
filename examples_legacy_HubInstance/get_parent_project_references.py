#!/usr/bin/env python

from blackduck.HubRestApi import HubInstance

import argparse
import json

parser = argparse.ArgumentParser("Get parent project references to this project-version")
parser.add_argument("project_name")
parser.add_argument("version_name")
args = parser.parse_args()

hub = HubInstance()

project_version = hub.get_project_version_by_name(args.project_name, args.version_name)

parent_references_url = project_version['_meta']['href'].replace('projects', 'components') + "/references"
parent_references = hub.execute_get(parent_references_url).json().get('items', [])

print(json.dumps(parent_references))