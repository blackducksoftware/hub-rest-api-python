#!/usr/bin/env python

import argparse
import json
import logging
import sys

from blackduck.HubRestApi import HubInstance


parser = argparse.ArgumentParser("Retreive BOM component license information for the given project and version")
parser.add_argument("project_name")
parser.add_argument("version")

args = parser.parse_args()


hub = HubInstance()

project = hub.get_project_by_name(args.project_name)
version = hub.get_version_by_name(project, args.version)

bom_components = hub.get_version_components(version)

all_licenses = dict()

logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stderr, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

for bom_component in bom_components['items']:
	# Retrieve the licenses and license text for this bom component and insert the license info along with the bom component info
	# into the all_licenses dictionary
	component_licenses = hub.get_license_info_for_bom_component(bom_component)
	all_licenses.update({"{}, {}".format(bom_component['componentName'], bom_component['componentVersionName']): {
			"component_info": bom_component,
			"component_licenses": component_licenses
		}
	})

print(json.dumps(all_licenses))