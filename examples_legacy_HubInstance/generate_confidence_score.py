#!/usr/bin/env python

import argparse
import json
import logging
import sys

from blackduck.HubRestApi import HubInstance

parser = argparse.ArgumentParser("Generate Confidence Score Report")
parser.add_argument("project_name")
parser.add_argument("version")

args = parser.parse_args()


hub = HubInstance()

project = hub.get_project_by_name(args.project_name)
version = hub.get_version_by_name(project, args.version)

matches = hub.get_matched_components(version).get('items', [])
matches = list(filter(lambda f: 'SNIPPET' not in [m['matchType'] for m in f['matches']], matches))
print(json.dumps(matches))


