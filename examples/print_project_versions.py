'''
Created on Nov 15, 2018

@author: gsnyder

Print projects

'''

from blackduck.HubRestApi import HubInstance

import argparse
import json

parser = argparse.ArgumentParser()

parser.add_argument("project_name")
parser.add_argument("--version_name")

args = parser.parse_args()

hub = HubInstance()

parameters = {'q':"name:{}".format(args.project_name)}

projects = hub.get_projects(parameters=parameters)

result = {"info": "project {} not found"}

if 'totalCount' in projects and projects['totalCount'] == 1:
	project = projects['items'][0]
	if args.version_name:
		parameters = {'q':'versionName:{}'.format(args.version_name)}

		versions = hub.get_project_versions(project, parameters=parameters)

		if 'totalCount' in versions and versions['totalCount'] == 1:
			result = versions['items'][0]
		else:
			result = {"info": "did not find version {} in project {}".format(args.version_name, args.project_name)}
	else:
		result = hub.get_project_versions(project)


print(json.dumps(result))