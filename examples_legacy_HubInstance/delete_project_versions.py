'''
Created on Nov 20, 2018

@author: gsnyder

Delete multiple project-versions, along with their scans, given a input list (file)
'''

import argparse
import csv
import logging
import sys

from blackduck.HubRestApi import HubInstance

parser = argparse.ArgumentParser("A program that will delete multiple project-versions listed in a file")
parser.add_argument("project_versions_file", help="A comma separated list of project-versions, one project-version per line")
parser.add_argument("--keep_scans", action = 'store_true', default=False, help="Use this option if you want to keep scans associated with the project-versions. Default is False, scans will be deleted.")
args = parser.parse_args()

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

hub = HubInstance()

with open(args.project_versions_file) as csvfile:
	project_versions_reader = csv.reader(csvfile)
	for row in project_versions_reader:
		project_name = row[0]
		version_name = row[1]

		hub.delete_project_version_by_name(project_name, version_name, save_scans=args.keep_scans)

