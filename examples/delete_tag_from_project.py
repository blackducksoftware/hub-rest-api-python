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

	delete_tag_url = project_tags_url + "/{}".format(args.tag)

	print("Deleting tag {} from project {} using url: {}".format(args.tag, args.project_name, delete_tag_url))
	response = hub.execute_delete(delete_tag_url)

	if response.status_code == 204:
		print("Successfully deleted tag {} from project {}".format(args.tag, args.project_name))
	else:
		print("Failed to delete tag {} from project {} due to unknown reason, response status code was {}".format(
			args.tag, args.project_name, response.status_code))
else:
	print("Count not find project {}".format(args.project_name))
