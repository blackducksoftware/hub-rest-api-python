#!/usr/bin/env python

import argparse
import json

from blackduck.HubRestApi import HubInstance


parser = argparse.ArgumentParser("Retreive BOM component file matches for the given project and version")
parser.add_argument("project_name")
parser.add_argument("version")

args = parser.parse_args()


hub = HubInstance()

project = hub.get_project_by_name(args.project_name)
version = hub.get_version_by_name(project, args.version)

bom_components = hub.get_version_components(version)

project_id = project['_meta']['href'].split("/")[-1]
version_id = version['_meta']['href'].split("/")[-1]

all_matches = dict()

for bom_component in bom_components['items']:
	# Retrieve the file matches for this bom component and insert those matches along with the bom component info
	# into the all_matches dictionary
	component_file_matches = hub.get_file_matches_for_bom_component(bom_component)
	all_matches.update({"{}, {}".format(bom_component['componentName'], bom_component['componentVersionName']): {
			"component_info": bom_component,
			"component_file_matches": component_file_matches
		}
	})

print(json.dumps(all_matches))