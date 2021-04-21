#!/usr/bin/env python

import argparse
import json
import logging
import sys

from blackduck.HubRestApi import HubInstance


parser = argparse.ArgumentParser("Retreive BOM component risk profile information for the given project and version")
parser.add_argument("project_name")
parser.add_argument("version")

args = parser.parse_args()


hub = HubInstance()

project = hub.get_project_by_name(args.project_name)
version = hub.get_version_by_name(project, args.version)

bom_components = hub.get_version_components(version)

logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stderr, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

all_risk_profile_info = list()

for bom_component in bom_components['items']:
	all_risk_profile_info.append({
			"{}:{}".format(bom_component['componentName'], bom_component['componentVersionName']):
				{
					'url': bom_component['_meta']['href'],
					'activityRiskProfile': bom_component['activityRiskProfile'],
					'licenseRiskProfile': bom_component['licenseRiskProfile'],
					'operationalRiskProfile': bom_component['operationalRiskProfile'],
					'securityRiskProfile': bom_component['securityRiskProfile'],
					'versionRiskProfile': bom_component['versionRiskProfile'],
					'activityData': bom_component['activityData']
				}
		})
print(json.dumps(all_risk_profile_info))