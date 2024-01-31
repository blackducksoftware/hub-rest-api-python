'''
Created on Jan 22, 2024

@author: pedapati

Update component version info for BOM Components with Unknown Versions based on matched filename in a given project version

'''

from blackduck import Client

import requests
import argparse
import json
import logging
import sys
import time
from pprint import pprint

import urllib3
import urllib.parse

NAME = 'update_component_version.py'
VERSION = '2024-01-22'

print(f'{NAME} ({VERSION}). Copyright (c) 2023 Synopsys, Inc.')


logging.basicConfig(
    level=logging.DEBUG,
    format="[%(asctime)s] {%(module)s:%(lineno)d} %(levelname)s - %(message)s"
)

parser = argparse.ArgumentParser(sys.argv[0])
parser.add_argument("-u", "--bd-url", help="Hub server URL e.g. https://your.blackduck.url")
parser.add_argument("-t", "--token-file", help="File name of a file containing access token")
parser.add_argument("-nv", '--no-verify', dest='verify', action='store_false', help="disable TLS certificate verification")
parser.add_argument("project_name")
parser.add_argument("version_name")

args = parser.parse_args()

logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stderr, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("blackduck").setLevel(logging.WARNING)

with open(args.token_file, 'r') as tf:
	access_token = tf.readline().strip()

bd = Client(base_url=args.bd_url, token=access_token, verify=args.verify)

params = {
    'q': [f"name:{args.project_name}"]
}
projects = [p for p in bd.get_resource('projects', params=params) if p['name'] == args.project_name]
assert len(projects) == 1, f"There should be one, and only one project named {args.project_name}. We found {len(projects)}"
project = projects[0]
project_id = project["_meta"]["href"].split("/")[-1]
print("Project ID: " + project_id)

params = {
    'q': [f"versionName:{args.version_name}"]
}
versions = [v for v in bd.get_resource('versions', project, params=params) if v['versionName'] == args.version_name]
assert len(versions) == 1, f"There should be one, and only one version named {args.version_name}. We found {len(versions)}"
version = versions[0]
version_id = version["_meta"]["href"].split("/")[-1]
print("Version ID: " + version_id)

logging.debug(f"Found {project['name']}:{version['versionName']}")
	
def update_bom_unknown_versions(bd, project_id, version_id):
	limit = 1000
	offset = 0
	paginated_url = f"{bd.base_url}/api/projects/{project_id}/versions/{version_id}/components?limit={limit}&offset={offset}&filter=unknownVersion:true"
	print("Looking for BOM Components with Unknown Versions: " + paginated_url)
	print()
	components_json = bd.session.get(paginated_url).json()
	total = str(components_json["totalCount"])
	print("Found " + total + " components with unknown versions")
	print()
	for component in components_json["items"]:
		comp_name =component["componentName"]
		print("Processing Component: " + comp_name)
		comp_url = component["component"]
		comp_bom_url = component["_meta"]["href"]
		matched_files_url = component["_meta"]["href"] + "/matched-files"
		matched_file_json = bd.session.get(matched_files_url).json()
		archivecontext = matched_file_json["items"][0]["filePath"]["archiveContext"]
		filename = matched_file_json["items"][0]["filePath"]["fileName"]
		## Extract Component Name and Version from archivecontext to do a KB lookup
		archive_strip = archivecontext.strip("/,!")
		archive_partition = archive_strip.rpartition("-")
		archive_final_list = archive_partition[0].rpartition("-")
		kb_file_lookup_name = archive_final_list[0]
		kb_comp_lookup_version = archive_final_list[2]
		print("Processing Component Version: " + kb_comp_lookup_version)
		## KB Lookup via Component Name
		components_url = bd.base_url + "/api/components/autocomplete"
		query = { "q": comp_name,
             "filter": "componentType:kb_component"
    	}
		url = f"{components_url}?{urllib.parse.urlencode(query)}"
		headers = {'Accept': '*/*'}
		name_match = bd.session.get(url, headers=headers).json()
		# Filtering results for exact name match 
		exact_name_match = [x for x in name_match['items'] if x['name']==comp_name]
		if len(exact_name_match) == 0 :
			logging.debug(f"Component {comp_name} is not found in the KB")
			return
		else:
			logging.debug(f"Component {comp_name} is found in the KB")
		if kb_comp_lookup_version:
			first_match_successful = False
			# second_match_successful = False
			for match in exact_name_match:  # handling OSS components that share same name
				url = match['_meta']['href']+'/versions?q=versionName:' + kb_comp_lookup_version
				headers = {'Accept': 'application/vnd.blackducksoftware.summary-1+json'}
				# Producing version matches
				version_match = bd.session.get(url, headers=headers).json()
				if version_match['totalCount'] > 0:
					print(version_match["items"][0]["versionName"])
					print("Found version: " + kb_comp_lookup_version + " in the KB for component " + comp_name)
					print("Updating component version for " + comp_name + " to " + kb_comp_lookup_version )
					# component_url = version_match[]
					# print(version_match)
					component_version_url = version_match['items'][0]['_meta']['href']
					component_url = component_version_url[:component_version_url.index("versions")-1]
					# print(component_url)
					post_data = {"component": component_url, "componentVersion": component_version_url}
					headers = {'Accept': 'application/vnd.blackducksoftware.bill-of-materials-6+json', 'Content-Type': 'application/vnd.blackducksoftware.bill-of-materials-6+json'}
					response = bd.session.put(comp_bom_url, headers=headers, data=json.dumps(post_data))
					# print(response)
					if response.status_code == 200:
						message = f"{response}"
						print("Successfully updated " + comp_name + " with version " + kb_comp_lookup_version)
					else:
						message = f"{response.json()}"
						logging.debug(f"Updating BOM component {comp_name} {kb_comp_lookup_version} failed with: {message}")
					first_match_successful = True
					print("### Proceeding to next component")
					print()
					break
				else:
					print("No matching version " + kb_comp_lookup_version + " found for " + comp_name)
			if not first_match_successful:
				## Trying to locate component name using source archive name
				print("Proceeding to KB lookup via matched file name: " + kb_file_lookup_name)
				components_url = bd.base_url + "/api/components/autocomplete"
				query = { "q": kb_file_lookup_name,
					"filter": "componentType:kb_component"
				}
				url = f"{components_url}?{urllib.parse.urlencode(query)}"
				headers = {'Accept': '*/*'}
				name_match = bd.session.get(url, headers=headers).json()
				# Filtering results for exact name match 
				exact_name_match = [x for x in name_match['items'] if x['name']==kb_file_lookup_name]
				if len(exact_name_match) == 0 :
					logging.debug(f"File Match KB Component {kb_file_lookup_name} is not found in the KB")
					print("### Proceeding to next component")
					print()
					continue
				else:
					logging.debug(f"File Match KB Component {kb_file_lookup_name} is found in the KB")
				if kb_comp_lookup_version:
					for match in exact_name_match:  # handling OSS components that share same name
						url = match['_meta']['href']+'/versions?q=versionName:' + kb_comp_lookup_version
						headers = {'Accept': 'application/vnd.blackducksoftware.summary-1+json'}
						# Producing version matches
						version_match = bd.session.get(url, headers=headers).json()
						if version_match['totalCount'] > 0:
							print(version_match["items"][0]["versionName"])
							print("Found version: " + kb_comp_lookup_version + " in the KB for component " + kb_file_lookup_name)
							print("Updating component version for " + kb_file_lookup_name + " to " + kb_comp_lookup_version )
							# component_url = version_match[]
							# print(version_match)
							component_version_url = version_match['items'][0]['_meta']['href']
							component_url = component_version_url[:component_version_url.index("versions")-1]
							# print(component_url)
							post_data = {"component": component_url, "componentVersion": component_version_url}
							headers = {'Accept': 'application/vnd.blackducksoftware.bill-of-materials-6+json', 'Content-Type': 'application/vnd.blackducksoftware.bill-of-materials-6+json'}
							response = bd.session.put(comp_bom_url, headers=headers, data=json.dumps(post_data))
							# print(response)
							if response.status_code == 200:
								message = f"{response}"
								print("Successfully updated " + kb_file_lookup_name + " with version " + kb_comp_lookup_version)
								# second_match_successful = True
							else:									
								message = f"{response.json()}"
								logging.debug(f"Updating BOM component {kb_file_lookup_name} {kb_comp_lookup_version} failed with: {message}")
							print("### Proceeding to next component")
							print()
							break
						else:
							print("No matching version " + kb_comp_lookup_version + " found for " + kb_file_lookup_name)
				print("### Proceeding to next component")
				print()
			

	
bom = update_bom_unknown_versions(bd, project_id, version_id)

	

