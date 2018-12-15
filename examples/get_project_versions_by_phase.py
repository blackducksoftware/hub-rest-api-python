'''
Created on Nov 20, 2018

@author: gsnyder

Find all project-versions in a given phase and write them to a file, or to stdout
'''

import argparse
import csv

from blackduck.HubRestApi import HubInstance


parser = argparse.ArgumentParser(description="A program to find all project-versions given a phase and output the names to a file (or stdout)")
possible_phases = ["In Development", "In Planning", "Pre-release", "Released", "Deprecated", "Archived"]
parser.add_argument("file", help="The file to write the project and version names into")
parser.add_argument("--phase", default="In Development", choices = possible_phases, help="The project-version phase")
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

projects = hub.get_projects()

if 'items' in projects:
	with open(args.file, 'w', newline='') as csvfile:
		project_versions_writer = csv.writer(csvfile)
		for project in projects['items']:
			versions = hub.get_project_versions(project)
			if 'totalCount' in versions and versions['totalCount'] > 0:
				for version in versions['items']:
					if version['phase'] == phase_map[args.phase]:
						project_versions_writer.writerow([
							project['name'], 
							version['versionName']
						])
