#!/usr/bin/env python

import argparse
import json
import logging
import sys

from blackduck.HubRestApi import HubInstance


parser = argparse.ArgumentParser("Retreive license search results, i.e. --detect.blackduck.signature.scanner.license.search=true")
parser.add_argument("project_name")
parser.add_argument("version")

args = parser.parse_args()

logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stderr, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

hub = HubInstance()

project = hub.get_project_by_name(args.project_name)
version = hub.get_version_by_name(project, args.version)

version_id = version['_meta']['href'].split("/")[-1]

codelocations_url = hub.get_link(version, "codelocations")
codelocations = hub.execute_get(codelocations_url).json().get('items', [])

# all the results will be stored here using the code location
# name as the key and the value will include all the licenses, files
# found to have license info in them
#
license_search_results = {}

for codeloc in codelocations:
	license_search_results.update({
			codeloc['name']: {
				'codeloc_info': codeloc
			}
		})

	codeloc_id = codeloc['_meta']['href'].split("/")[-1]
	scans_url = hub.get_link(codeloc, "scans")
	scans = hub.execute_get(scans_url).json().get('items', [])
	latest_scan_url = hub.get_link(codeloc, "latest-scan")
	latest_scan = hub.execute_get(latest_scan_url).json()

	all_scans = []

	# TODO: Do I need to trim to the latest FS scan? Leaving it as list for now
	fs_scans = list(filter(lambda s: s['scanType'] == "FS", scans))

	for fs_scan in fs_scans:
		scan_id = fs_scan['_meta']['href'].split("/")[-1]
		lic_summary_url = version['_meta']['href'] + f"/scans/{scan_id}/license-search-summary"
		custom_headers = {'Accept':'*/*'}
		lic_search_summary = hub.execute_get(lic_summary_url, custom_headers=custom_headers).json().get('items', [])

		file_bom_entries = []
		for license_d in lic_search_summary:
			logging.debug(f"Getting {license_d['fileCount']} files where {license_d['licenseName']} was referenced.")
			file_bom_entries_url = hub.get_apibase() + f"/internal/releases/{version_id}/scans/{scan_id}/nodes/0/file-bom-entries?offset=0&limit=100&sort=&allDescendants=true&filter=stringSearchLicense:{license_d['vsl']}"
			file_bom_entries.extend(hub.execute_get(file_bom_entries_url).json().get('items', []))
		all_scans.append({
				'scan_info': fs_scan,
				'lic_search_summary': lic_search_summary,
				'file_bom_entries': file_bom_entries
			})
	license_search_results[codeloc['name']].update({
			'scans': all_scans
		})

print(json.dumps(license_search_results))






