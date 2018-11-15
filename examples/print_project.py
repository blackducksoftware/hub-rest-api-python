'''
Created on Nov 14, 2018

@author: gsnyder

Print a project given its name

'''

from blackduck.HubRestApi import HubInstance

import argparse
import json

parser = argparse.ArgumentParser()

parser.add_argument("--limit")
parser.add_argument("project_name")

args = parser.parse_args()

hub = HubInstance()

parameters = {'q':"name:{}".format(args.project_name)}

projects = hub.get_projects(parameters=parameters)

if 'totalCount' in projects and projects['totalCount'] == 1:
	project = projects['items'][0]
else:
	project = {'info': 'project {} not found'.format(args.project_name)}

print(json.dumps(project))