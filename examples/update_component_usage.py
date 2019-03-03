#!/usr/bin/env python

import argparse
import logging
import json
import sys

from blackduck.HubRestApi import HubInstance

usages = {
	'static': 'STATICALLY_LINKED',
	'dynamic': 'DYNAMICALLY_LINKED',
	'source': 'SOURCE_CODE',
	'separate_work': 'SEPARATE_WORK',
	'implementation_of_standard': 'IMPLEMENTATION_OF_STANDARD',
	'dev_tool_excluded': 'DEV_TOOL_EXCLUDED'
}

usage_list = list(usages.keys())

parser = argparse.ArgumentParser()
parser.add_argument("project_name")
parser.add_argument("version")
parser.add_argument("component_info", type=str, help="Component name and version separated by colon (:), e.g. ANTLR:2.7.2. Or, use 'ALL' will update the usage for all components in this project/version to the specified usage.")
parser.add_argument("usage", type=str, choices=usage_list, help="Choose the usage from this list")

args = parser.parse_args()

if args.component_info != 'ALL':
	component_name = args.component_info.split(":")[0]
	component_version = args.component_info.split(":")[1]

hub = HubInstance()

project = hub.get_project_by_name(args.project_name)
version = hub.get_version_by_name(project, args.version)

bom_components = hub.get_version_components(version)

logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stdout, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

def _update_component_usage(url, component_info, usage):
	custom_headers = {
		'Content-Type':'application/vnd.blackducksoftware.bill-of-materials-4+json'
	}
	del component_info['_meta']
	component_info['usages'] = [usages[usage]]
	component_info['componentModified'] = True
	response = hub.execute_put(bom_component_url, component_info, custom_headers=custom_headers)
	if response.status_code == 200:
		logging.info("Successfully updated the usage to {} for component {}, version {}".format(
			usage, component_info['componentName'], component_info['componentVersionName']))

logging.debug("Looking through the BOM components for project {}, version {}. Setting usage to {} for component {}".format(
	args.project_name, args.version, args.usage, args.component_info))

for bom_component in bom_components['items']:
	if args.component_info == 'ALL' or (bom_component['componentName'] == component_name and bom_component['componentVersionName'] == component_version):
		bom_component_url = bom_component['_meta']['href']
		_update_component_usage(bom_component_url, bom_component, args.usage)
		if args.component_info != 'ALL':
			break