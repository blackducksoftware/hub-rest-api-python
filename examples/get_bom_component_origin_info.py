#!/usr/bin/env python

import argparse
import json
import logging
import sys

from blackduck.HubRestApi import HubInstance


parser = argparse.ArgumentParser("Retreive BOM component license information for the given project and version")
parser.add_argument("project_name")
parser.add_argument("version")
parser.add_argument("-l", "--deep_license_info", action="store_true")
parser.add_argument("-c", "--copyright_info", action="store_true")
parser.add_argument("-m", "--matched_files", action="store_true")
parser.add_argument("-u", "--un_matched_files", action="store_true")


args = parser.parse_args()


hub = HubInstance()

project = hub.get_project_by_name(args.project_name)
version = hub.get_version_by_name(project, args.version)

bom_components = hub.get_version_components(version).get('items', [])

all_origins = dict()

logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stderr, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

all_origin_info = {}

scan_cache = {}

for bom_component in bom_components:
	if 'componentVersionName' in bom_component:
		bom_component_name = f"{bom_component['componentName']}:{bom_component['componentVersionName']}"
	else:
		bom_component_name = f"{bom_component['componentName']}"

	# Component details include the home page url and additional home pages
	component_url = bom_component['component']
	component_details = hub.execute_get(component_url).json()

	#
	# Grab origin info, file-level license info, and file-level copyright info
	#
	all_origin_details = list()
	for origin in bom_component.get('origins', []):
		logging.debug(f"Retrieving origin details for {bom_component_name} and origin {origin['name']}")
		origin_url = hub.get_link(origin, 'origin')
		origin_details = hub.execute_get(origin_url).json()

		#
		# Add deep license info and copyright info, as appropriate
		#
		info_to_get = []
		if args.deep_license_info:
			info_to_get.extend([
					("file-licenses", "file_licenses"),
					("file-licenses-fuzzy", "file_licenses_fuzzy")
				])

		if args.copyright_info:
			info_to_get.extend([
					("file-copyrights", "file_copyrights"),
					("component-origin-copyrights", "component_origin_copyrights")
				])
		for link_t in info_to_get:
			link_name = link_t[0]
			k = link_t[1]
			logging.debug(f"Retrieving {link_name} for {bom_component_name}")
			url = hub.get_link(origin_details, link_name)
			info = hub.execute_get(url).json().get('items', [])
			origin_details[k] = info

		all_origin_details.append(origin_details)

	all_origin_info.update({
			bom_component_name: {
				"bom_component_info": bom_component,
				"component_details": component_details,
				"component_home_page": component_details.get("url"),
				"additional_home_pages": component_details.get("additionalHomepages"),
				"all_origin_details": all_origin_details,
			}
		})

	if args.matched_files:
		logging.debug(f"Retrieving matched files for {bom_component_name}")
		matched_files_url = hub.get_link(bom_component, "matched-files") + "?limit=99999"
		matched_files = hub.execute_get(matched_files_url).json().get('items', [])
		# Get scan info
		for matched_file in matched_files:
			scan_url = hub.get_link(matched_file, "codelocations")
			if scan_url in scan_cache:
				scan = scan_cache[scan_url]
			else:
				scan = hub.execute_get(scan_url).json()
				scan_cache[scan_url] = scan
			matched_file['scan'] = scan
		all_origin_info[bom_component_name].update({
				'matched_files': matched_files
			})

if args.un_matched_files:
	# TODO: Probably need to loop on this with smaller page sizes to handle very large
	# project-versions with many (signature) scans mapped to it
	#
	logging.debug(f"Retrieving un-matched files for project {project['name']}, version {version['versionName']}")
	un_matched_files_url = f"{version['_meta']['href']}/matched-files?limit=99999&filter=bomMatchType:unmatched"
	un_matched_files = hub.execute_get(un_matched_files_url).json().get('items', [])
	logging.debug(f"Adding {len(un_matched_files)} un-matched files to the output")
	all_origin_info.update({
			'un_matched_files': un_matched_files
		})

print(json.dumps(all_origin_info))