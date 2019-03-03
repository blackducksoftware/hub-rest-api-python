'''
Created on Dec 19, 2018

@author: gsnyder

Get the project versions for a given project with some filtering, sorting, and limit features
'''

import argparse
import csv
from dateutil import parser as dt_parser
import json

from blackduck.HubRestApi import HubInstance


parser = argparse.ArgumentParser(description="A program for obtaining all the versions associated to a given project")
possible_phases = ["In Development", "In Planning", "Pre-release", "Released", "Deprecated", "Archived"]
parser.add_argument("project_name", help="The name of the project. Use 'all' for all projects")
parser.add_argument("--out_file", default=None, help="Write the project and version names out to a CSV-formatted file instead of stdout")
parser.add_argument("--sort_order", default="reverse", choices=["reverse", "forward"], help="The sort order on createdAt - reverse means more recent first, forward means oldest first")
parser.add_argument("--phase", default=None, choices = possible_phases, help="Filter by version phase (default: None")
parser.add_argument("--limit", type=int, default=None, help="Trim the number of versions after doing a reverse sort by createdAt to return the most recently created versions")
parser.add_argument("--remove", type=bool, default=False, help="If True, the program produces a list of project-versions that should be removed based on the 'limit' setting and the sort order")
parser.add_argument("--maxversions", default=9999)
args = parser.parse_args()

phase_map = {
	"In Development": "DEVELOPMENT",
	"In Planning": "PLANNING",
	"Pre-release": "PRERELEASE",
	"Released": "RELEASED",
	"Deprecated": "DEPRECATED",
	"Archived": "ARCHIVED"
}

hub = HubInstance()

if args.project_name == "all":
	project_list = hub.get_projects(limit=99999)
else:
	# the name query returns all projects that begin with the provided name so we have to handle that later
	project_list = hub.get_projects(parameters={"q":"name:{}".format(args.project_name)})

def write_to_csv_file(filename, version_list):
	with open(filename, 'w', newline='') as csvfile:
		project_versions_writer = csv.writer(csvfile)
		for project_name, version in version_list:
			project_versions_writer.writerow([
				project_name, 
				version['versionName']
			])

if 'totalCount' in project_list and project_list['totalCount'] > 0:
	all_versions = list()
	for project in project_list['items']:
		# project = project_list['items'][0]
		if args.project_name != 'all' and project['name'] != args.project_name:
			# skip project unless it's name is same as one we are looking for
			continue
		versions = hub.get_project_versions(project, limit=args.maxversions)
		if 'totalCount' in versions and versions['totalCount'] > 0:
			version_list = versions['items']
			sorted_version_list = sorted(version_list, key=lambda k: dt_parser.parse(k['createdAt']), reverse=(args.sort_order == "reverse"))

			if args.phase:
				new_list = list()
				for version in sorted_version_list:
					if sorted_version_list['phase'] == phase_map[args.phase]:
						new_list.append(version)
				sorted_version_list = new_list
			if args.limit:
				if args.remove:
					sorted_version_list = sorted_version_list[args.limit:]
				else:
					sorted_version_list = sorted_version_list[:args.limit]
			all_versions.extend([(project['name'], v) for v in sorted_version_list])
		else:
			print("No versions found for project {}".format(project['name']))
	if args.out_file:
		write_to_csv_file(args.out_file, all_versions)
	else:
		print(json.dumps(all_versions))
else:
	if args.project_name == "all":
		print("Did not find any projects")
	else:
		print("Did not find any project with name {}".format(args.project_name))



