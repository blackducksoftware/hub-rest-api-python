'''
Created on Dec 16, 2018

@author: gsnyder

Add tags to a project

'''
from blackduck.HubRestApi import HubInstance

import argparse

parser = argparse.ArgumentParser("Add tags to a project")
parser.add_argument("project_name")
parser.add_argument("tag")
args = parser.parse_args()

hub = HubInstance()

project_list = hub.get_projects(parameters={"q":"name:{}".format(args.project_name)})

if 'totalCount' in project_list and project_list['totalCount'] > 0:
	project_tags_url = hub.get_tags_url(project_list['items'][0])

	print("Adding tag {} to project {} using tags url: {}".format(args.tag, args.project_name, project_tags_url))
	response = hub.execute_post(project_tags_url, {"name": args.tag})
	if response.status_code == 201:
		print("Successfully added tag {} to project {}".format(args.tag, args.project_name))
	elif response.status_code == 412:
		print("Failed to add tag {} to project {} due to a pre-condition failure, probably due to invalid tag value (e.g. use of special characters) OR the tag already exists".format(
			args.tag, args.project_name))
	else:
		print("Failed to add tag {} to project {} due to unknown reason, response status code was {}".format(
			args.tag, args.project_name, response.status_code))
else:
	print("Count not find project {}".format(args.project_name))
