#!/usr/bin/env python

"""
Date: 04/07/2020
Requirements:
1. Define a Custom Field at the BOM Component Level from the Black Duck UI under Custom Fields Management.
2. The field type needs to be "Text Area"

Script: Executing the script will write source paths of each component from a Project-Version to the defined Custom Field. 
Executing the script again will simply overwrite the existing values with new ones. This is particularly useful if an end-user 
is using REST APIs and would like to pull file paths.

"""

import argparse
import logging

from blackduck.HubRestApi import HubInstance


parser = argparse.ArgumentParser("Write the complete file path to a custom field  for BOM component file matches for the given project and version")
parser.add_argument("project_name")
parser.add_argument("version")

args = parser.parse_args()

# Set the Custom Field Id
custom_field_id = ""


custom_headers = {'Accept': 'application/vnd.blackducksoftware.bill-of-materials-6+json'}

hub = HubInstance()


project = hub.get_project_by_name(args.project_name)
version = hub.get_version_by_name(project, args.version)

# Custom Field Id Check
if custom_field_id == "":
	print("Set the custom_field_id variable above with the correct Id and try executing the script again.")
	exit()

# Get all BOM Components
bom_components = hub.get_version_components(version)

# Total Components for given project and Version
print("Total Components: ", len(bom_components['items']))

# Iterate through each Bom Component
for bomComponent in bom_components['items']:

	# Parse the JSON to build the custom field URL
	customFieldURL = bomComponent['_meta']['href'] + "/custom-fields/"+custom_field_id

	# Check no of Origins per component
	if len(bomComponent['origins']) == 0:

		pass

	else:

		for origin in bomComponent['origins']:

			matched_files_url = origin['_meta']['links'][1]['href']
			matched_files_json = hub.execute_get(matched_files_url).json()

			# Iterate through each components matched files to build a comma separated string of source paths

			if matched_files_json['totalCount'] > 0:

				component_source_paths = ''

				for file_path in range(0, len(matched_files_json['items'])):
					path = matched_files_json['items'][file_path]['filePath']['path']
					code_location = matched_files_json['items'][file_path]['_meta']['links'][0]['href']
					archive_Context = (matched_files_json['items'][file_path]['filePath']['archiveContext']).replace("!", '')
					code_location_json = hub.execute_get(code_location).json()
					code_location_name = code_location_json['name']
					component_source_paths = component_source_paths + ',' + code_location_name+"/"+(archive_Context)[:-1]+path

				# Wrapping component_source_paths in double quotes 	
				component_source_paths = '"'+component_source_paths[1::]+'"'

				# Creating a dictionary to save component_source_paths to key "values"
				data = {"values": [component_source_paths]}

				# Execute PUT call
				response = hub.execute_put(customFieldURL, data, custom_headers)

				# Logging
				if response.status_code != 200:
					print(bomComponent['componentName'] + ' | ' + bomComponent['componentVersionName'] + ' | '+ 'No of Origins: '+str(len(bomComponent['origins'])) + ' failed to write to the custom field \n' )
				else:
					logging.info("Successfully updated custom field for bom component  {} , version {}".format(
						bomComponent['componentName'], bomComponent['componentVersionName']))
