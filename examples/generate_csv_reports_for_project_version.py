#!/usr/bin/python3

'''
Created on Dec 19, 2018

@author: gsnyder

Generate CSV reports for a given project-version
'''

from blackduck.HubRestApi import HubInstance

import argparse
import json
import time

version_name_map = {
	'version': 'VERSION',
	'scans': 'CODE_LOCATIONS',
	'components': 'COMPONENTS',
	'vulnerabilities': 'SECURITY',
	'source':'FILES',
    'attachments':'ATTACHMENTS',
    'crypto':'CRYPTO_ALGORITHMS',
    'project_custom':'PROJECT_VERSION_CUSTOM_FIELDS',
    'bom_custom':'BOM_COMPONENT_CUSTOM_FIELDS',
    'license':'LICENSE_TERM_FULFILLMENT',
}

parser = argparse.ArgumentParser("A program to create reports for a given project-version")
parser.add_argument("project_name")
parser.add_argument("version_name")
parser.add_argument("-z", "--zip_file_name", default="reports.zip")
parser.add_argument("-r", "--reports",
	default="version,scans,components,vulnerabilities,source,attachments,project_custom,bom_custom,license", 
	help=f"Comma separated list (no spaces) of the reports to generate - {version_name_map.keys()} (default: all, except cryptography")
parser.add_argument('--format', default='CSV', choices=["CSV"], help="Report format - only CSV available for now")
parser.add_argument('-t', '--tries', default=4, type=int, help="How many times to retry downloading the report, i.e. wait for the report to be generated")
parser.add_argument('-s', '--sleep_time', default=5, type=int, help="The amount of time to sleep in-between (re-)tries to download the report")

args = parser.parse_args()

hub = HubInstance()

class FailedReportDownload(Exception):
	pass

def download_report(location, filename, retries=args.tries):
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
			print(f"Probably not ready yet, waiting {args.sleep_time} seconds then retrying...")
			time.sleep(args.sleep_time)
			retries -= 1
			download_report(location, filename, retries)
	else:
		raise FailedReportDownload("Failed to retrieve report {} after multiple retries".format(report_id))

project = hub.get_project_by_name(args.project_name)

if project:
	version = hub.get_version_by_name(project, args.version_name)
	# reports_json = generate_reports_json(version, args.reports)

	reports_l = args.reports.split(",")
	reports_l = [version_name_map[r.lower()] for r in reports_l]
	response = hub.create_version_reports(version, reports_l, args.format)

	if response.status_code == 201:
		print("Successfully created reports ({}) for project {} and version {}".format(
			args.reports, args.project_name, args.version_name))
		location = response.headers['Location']
		download_report(location, args.zip_file_name)
	else:
		print("Failed to create reports for project {} version {}, status code returned {}".format(
			args.project_name, args.version_name, response.status_code))
else:
	print("Did not find project with name {}".format(args.project_name))