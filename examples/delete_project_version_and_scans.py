'''
Created on Nov 13, 2018

@author: gsnyder

Given a project name, a version name, delete the project-version and any scans associated with it

'''
from blackduck.HubRestApi import HubInstance
from pprint import pprint

import argparse

parser = argparse.ArgumentParser()
parser.add_argument("project_name")
parser.add_argument("version_name")

args = parser.parse_args()

hub = HubInstance()

projects = hub.get_projects(parameters={'q':"name:{}".format(args.project_name)})

if 'totalCount' in projects and projects['totalCount'] > 0:
	project = projects['items'][0]
	project_versions = hub.get_project_versions(
		project, 
		parameters={'q':"versionName:{}".format(args.version_name)}
	)

	project_version_codelocations = None
	if 'totalCount' in project_versions and project_versions['totalCount'] == 1:
		project_version = project_versions['items'][0]
		project_version_codelocations = hub.get_version_codelocations(project_version)

		if 'totalCount' in project_version_codelocations and project_version_codelocations['totalCount'] > 0:
			code_location_urls = [c['_meta']['href'] for c in project_version_codelocations['items']]
			for code_location_url in code_location_urls:
				print("Deleting code location at: {}".format(code_location_url))
				hub.execute_delete(code_location_url)
			print("Deleting project-version at: {}".format(project_version['_meta']['href']))
			hub.execute_delete(project_version['_meta']['href'])
		else:
			print("Did not find any codelocations (scans) in version {} of project {}".format(args.version_name, args.project_name))
	else:
		print("Did not find version with name {} in project {}".format(args.version_name, args.project_name))
else:
	print("Did not find project with name {}".format(args.project_name))