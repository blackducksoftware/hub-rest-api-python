#!/usr/bin/env python

import argparse
import json
import csv
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

all_origins = dict()

logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stderr, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

all_origin_info = {}
components_info = [["Component Name", "Component Version" ,"Homepage", "Approval Status", "Component ID", "Component Version ID", "License"]]

for bom_component in bom_components['items']:
	component_url = bom_component['component']
	response = hub.execute_get(component_url)

	# Component details include the home page url and additional home pages
	logging.debug("Retrieving component home page info for {}:{}".format(
		bom_component.get("componentName"), bom_component.get("componentVersionName")))
	component_details = None
	if response.status_code == 200:
		component_details = response.json()

	for origin in bom_component.get('origins', []):
		logging.debug("Retrieving origin details for origin {}".format(origin['name']))
		origin_url = hub.get_link(origin, 'origin')
		response = hub.execute_get(origin_url)
		origin_details = None
		if response.status_code == 200:
			origin_details = response.json()

		all_origin_info.update({
				"{}:{}".format(bom_component['componentName'], bom_component['componentVersionName']): {
					"component_details": component_details,
					"component_home_page": component_details.get("url"),
					"additional_home_pages": component_details.get("additionalHomepages"),
					"origin_details": origin_details,
				}
			})
		#component_info = [bom_component['componentName'], bom_component['componentVersionName'], component_details.get("url"), component_details['approvalStatus'], bom_component['component'], bom_component['componentVersion'], origin_details['license']['licenseDisplay']]
		component_info = [bom_component.get("componentName"), bom_component.get("componentVersionName"), component_details.get("url"), bom_component.get("approvalStatus"), bom_component.get("component"), bom_component.get("componentVersion"), origin_details.get('license').get("licenseDisplay")]
		components_info.append(component_info)

mycsv = csv.writer(open(r'Report.csv', 'w'), lineterminator='\n')
for row in components_info:
    if any(row):
        mycsv.writerow(row)
print("Report.csv is successfully generated")
#print(json.dumps(all_origin_info))

