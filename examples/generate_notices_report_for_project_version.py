'''
Created on Dec 19, 2018

@author: gsnyder

Generate notices report for a given project-version
'''

from blackduck.HubRestApi import HubInstance

import argparse
import json
import time
import zipfile

parser = argparse.ArgumentParser("A program to generate the notices file for a given project-version")
parser.add_argument("project_name")
parser.add_argument("version_name")
parser.add_argument("--zip_file_name", default="notices_report.zip")
parser.add_argument("--reports",
	default="version,scans,components,vulnerabilities,source", 
	help="Comma separated list (no spaces) of the reports to generate - version, scans, components, vulnerabilities, source, and cryptography reports (default: all, except cryptography")
parser.add_argument('--format', default='TEXT', choices=["HTML", "TEXT"], help="Report format - choices are TEXT or HTML")

args = parser.parse_args()

hub = HubInstance()

# TODO: Promote this to the API?
class FailedReportDownload(Exception):
	pass

def download_report(location, filename, retries=4):
	report_id = location.split("/")[-1]

	if retries:
		print("Retrieving generated report from {}".format(location))
		response = hub.download_report(report_id)
		if response.status_code == 200:
			with open(filename, "wb") as f:
				f.write(response.content)
			print("Successfully downloaded zip file to {} for report {}".format(filename, report_id))
		else:
			print("Failed to retrieve report {}".format(report_id))
			print("Probably not ready yet, waiting 5 seconds then retrying...")
			time.sleep(5)
			retries -= 1
			download_report(location, filename, retries)
	else:
		raise FailedReportDownload("Failed to retrieve report {} after multiple retries".format(report_id))

project = hub.get_project_by_name(args.project_name)

if project:
	version = hub.get_version_by_name(project, args.version_name)

	response = hub.create_version_notices_report(version, args.format)

	if response.status_code == 201:
		print("Successfully created reports ({}) for project {} and version {}".format(
			args.reports, args.project_name, args.version_name))
		location = response.headers['Location']
		download_report(location, args.zip_file_name)

		# Showing how you can interact with the downloaded zip and where to find the
		# output content. Uncomment the lines below to see how it works.

		# with zipfile.ZipFile(zip_file_name, 'r') as zipf:
		# 	with zipf.open("{}/{}/version-license.txt".format(args.project_name, args.version_name), "r") as license_file:
		# 		print(license_file.read())
	else:
		print("Failed to create reports for project {} version {}, status code returned {}".format(
			args.project_name, args.version_name, response.status_code))
else:
	print("Did not find project with name {}".format(args.project_name))