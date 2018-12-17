'''
Created on Nov 20, 2018

@author: gsnyder

Find all project-versions that have a given word in their notes field
'''

import argparse
import csv

from blackduck.HubRestApi import HubInstance


parser = argparse.ArgumentParser(description="A program to find all project-versions with a given word in their Notes field and write the project, version names to a file")
parser.add_argument("file", help="The file to write the project and version names into")
parser.add_argument("word", help="The project-version phase")
args = parser.parse_args()

hub = HubInstance()

projects = hub.get_projects()

if 'items' in projects:
	with open(args.file, 'w', newline='') as csvfile:
		project_versions_writer = csv.writer(csvfile)
		for project in projects['items']:
			versions = hub.get_project_versions(project)
			if 'totalCount' in versions and versions['totalCount'] > 0:
				for version in versions['items']:
					if 'releaseComments' in version and args.word.lower() in version['releaseComments'].lower():
						project_versions_writer.writerow([
							project['name'], 
							version['versionName']
						])
