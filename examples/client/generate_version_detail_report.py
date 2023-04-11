'''
Created on June 11, 2021

@author: gsnyder

Generate Version Details report for a given project-version

ref: https://your-blackduck-server/doc/Welcome.htm#reporting/projectversionreport.htm?Highlight=version details report
'''

# from blackduck.HubRestApi import HubInstance
from blackduck import Client

import argparse
import json
import logging
import sys
import time
from pprint import pprint

logging.basicConfig(
    level=logging.DEBUG,
    format="[%(asctime)s] {%(module)s:%(lineno)d} %(levelname)s - %(message)s"
)


version_name_map = {
	'version': 'VERSION',
	'scans': 'CODE_LOCATIONS',
	'components': 'COMPONENTS',
	'vulnerabilities': 'SECURITY',
	'source':'FILES',
	'cryptography': 'CRYPTO_ALGORITHMS',
	'license_terms': 'LICENSE_TERM_FULFILLMENT',
	'component_additional_fields': 'BOM_COMPONENT_CUSTOM_FIELDS',
	'project_version_additional_fields': 'PROJECT_VERSION_CUSTOM_FIELDS',
	'vulnerability_matches': 'VULNERABILITY_MATCH'
}

all_reports = list(version_name_map.keys())

class FailedReportDownload(Exception):
	pass


parser = argparse.ArgumentParser("A program to create version detail reports for a given project-version")
parser.add_argument("bd_url", help="Hub server URL e.g. https://your.blackduck.url")
parser.add_argument("token_file", help="containing access token")
parser.add_argument("project_name")
parser.add_argument("version_name")
parser.add_argument("-z", "--zip_file_name", default="reports.zip")
parser.add_argument("-r", "--reports",
	default=",".join(all_reports), 
	help=f"Comma separated list (no spaces) of the reports to generate - {list(version_name_map.keys())}. Default is all reports.")
parser.add_argument('--format', default='CSV', choices=["CSV"], help="Report format - only CSV available for now")
parser.add_argument('-t', '--tries', default=30, type=int, help="How many times to retry downloading the report, i.e. wait for the report to be generated")
parser.add_argument('-s', '--sleep_time', default=10, type=int, help="The amount of time to sleep in-between (re-)tries to download the report")
parser.add_argument('--no-verify', dest='verify', action='store_false', help="disable TLS certificate verification")

args = parser.parse_args()

def download_report(bd_client, location, filename, retries=args.tries):
	report_id = location.split("/")[-1]
	base_url = bd_client.base_url if bd_client.base_url.endswith("/") else bd_client.base_url + "/"
	download_url = f"{base_url}api/reports/{report_id}"

	logging.info(f"Retrieving report list for {location}")

	if retries:
		response = bd_client.session.get(location)
		report_status = response.json().get('status', 'Not Ready')
		if response.status_code == 200 and report_status == 'COMPLETED':
			response = bd.session.get(download_url, headers={'Content-Type': 'application/zip', 'Accept':'application/zip'})
			if response.status_code == 200:
				with open(filename, "wb") as f:
					f.write(response.content)
				logging.info(f"Successfully downloaded zip file to {filename} for report {report_id}")
			else:
				logging.error(f"Failed to download report")
		else:	
			retries -= 1
			logging.debug(f"Failed to retrieve report {report_id}, report status: {report_status}")
			logging.debug(f"Will retry {retries} more times. Sleeping for {args.sleep_time} second(s)")
			time.sleep(args.sleep_time)
			download_report(bd_client, location, filename, retries)
	else:
		raise FailedReportDownload(f"Failed to retrieve report {report_id} after multiple retries")

with open(args.token_file, 'r') as tf:
	access_token = tf.readline().strip()

bd = Client(base_url=args.bd_url, token=access_token, verify=args.verify)

params = {
    'q': [f"name:{args.project_name}"]
}
projects = [p for p in bd.get_resource('projects', params=params) if p['name'] == args.project_name]
assert len(projects) == 1, f"There should be one, and only one project named {args.project_name}. We found {len(projects)}"
project = projects[0]

params = {
    'q': [f"versionName:{args.version_name}"]
}
versions = [v for v in bd.get_resource('versions', project, params=params) if v['versionName'] == args.version_name]
assert len(versions) == 1, f"There should be one, and only one version named {args.version_name}. We found {len(versions)}"
version = versions[0]

logging.debug(f"Found {project['name']}:{version['versionName']}")

reports_l = args.reports.split(",")
reports_l = [version_name_map[r.lower()] for r in reports_l]

post_data = {
        'categories': reports_l,
        'versionId': version['_meta']['href'].split("/")[-1],
        'reportType': 'VERSION',
        'reportFormat': "CSV"	
}
version_reports_url = bd.list_resources(version).get('versionReport')
assert version_reports_url, "Ruh-roh, a version should always have a versionReport resource under it"

r = bd.session.post(version_reports_url, json=post_data)
r.raise_for_status()
location = r.headers.get('Location')
assert location, "Hmm, this does not make sense. If we successfully created a report then there needs to be a location where we can get it from"

logging.debug(f"Created version details report for project {args.project_name}, version {args.version_name} at location {location}")
download_report(bd, location, args.zip_file_name)

