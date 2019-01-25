#!/usr/bin/env python

import argparse
import json

from blackduck.HubRestApi import HubInstance


parser = argparse.ArgumentParser()
parser.add_argument("project_name")
parser.add_argument("version")

args = parser.parse_args()


hub = HubInstance()

project = hub.get_project_by_name(args.project_name)
version = hub.get_version_by_name(project, args.version)

project_id = project['_meta']['href'].split("/")[-1]
version_id = version['_meta']['href'].split("/")[-1]

snippet_bom_entries = hub.get_snippet_bom_entries(project_id, version_id)
if snippet_bom_entries:
	print(json.dumps(snippet_bom_entries))