'''
Created on July 8, 2021

@author: gsnyder

Generate SBOM for a given project-version

'''

from blackduck import Client

import argparse
import json
import logging
import sys
import time

logging.basicConfig(
    level=logging.DEBUG,
    format="[%(asctime)s] {%(module)s:%(lineno)d} %(levelname)s - %(message)s"
)


# version_name_map = {
# 	'version': 'VERSION',
# 	'scans': 'CODE_LOCATIONS',
# 	'components': 'COMPONENTS',
# 	'vulnerabilities': 'SECURITY',
# 	'source':'FILES',
# 	'cryptography': 'CRYPTO_ALGORITHMS',
# 	'license_terms': 'LICENSE_TERM_FULFILLMENT',
# 	'component_additional_fields': 'BOM_COMPONENT_CUSTOM_FIELDS',
# 	'project_version_additional_fields': 'PROJECT_VERSION_CUSTOM_FIELDS',
# 	'vulnerability_matches': 'VULNERABILITY_MATCH'
# }

# all_reports = list(version_name_map.keys())

class FailedReportDownload(Exception):
	pass


parser = argparse.ArgumentParser("A program to create an SBOM for a given project-version")
parser.add_argument("bd_url", help="Hub server URL e.g. https://your.blackduck.url")
parser.add_argument("token_file", help="containing access token")
parser.add_argument("project_name")
parser.add_argument("version_name")
parser.add_argument("-t", "--type", type=str, nargs='?', default="SPDX_23", choices=["SPDX_22", "SPDX_23", "CYCLONEDX_13", "CYCLONEDX_14"], help="Choose the type of SBOM report")
parser.add_argument('-r', '--retries', default=4, type=int, help="How many times to retry downloading the report, i.e. wait for the report to be generated")
parser.add_argument('-s', '--sleep_seconds', default=60, type=int, help="The amount of time to sleep in-between (re-)tries to download the report")
parser.add_argument('--include-subprojects', dest='include_subprojects', action='store_false', help="whether subprojects should be included")
parser.add_argument('--no-verify', dest='verify', action='store_false', help="disable TLS certificate verification")

args = parser.parse_args()

logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stderr, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("blackduck").setLevel(logging.WARNING)


def download_report(bd_client, location, filename, retries=args.retries):
	report_id = location.split("/")[-1]
	if retries:
		logging.debug(f"Retrieving generated report from {location}")
		response = bd.session.get(location)
		report_status = response.json().get('status', 'Not Ready')
		if response.status_code == 200 and report_status == 'COMPLETED':
			response = bd.session.get(location + "/download.zip", headers={'Content-Type': 'application/zip', 'Accept':'application/zip'})
			if response.status_code == 200:
				with open(filename, "wb") as f:
					f.write(response.content)
				logging.info(f"Successfully downloaded zip file to {filename} for report {report_id}")
			else:
				logging.error("Ruh-roh, not sure what happened here")
		else:
			logging.debug(f"Failed to retrieve report {report_id}, report status: {report_status}")
			logging.debug(f"Probably not ready yet, waiting {sleep_seconds} seconds then retrying...")
			time.sleep(args.sleep_seconds)
			retries -= 1
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

post_data = {
        'reportFormat': "JSON",
        'sbomType': args.type,
		'includeSubprojects': args.include_subprojects	
}
sbom_reports_url = version['_meta']['href'] + "/sbom-reports"

bd.session.headers["Content-Type"] = "application/vnd.blackducksoftware.report-4.json"
r = bd.session.post(sbom_reports_url, json=post_data)
if (r.status_code == 403):
	logging.debug("Authorization Error - Please ensure the token you are using has write permissions!")
r.raise_for_status()
location = r.headers.get('Location')
assert location, "Hmm, this does not make sense. If we successfully created a report then there needs to be a location where we can get it from"

logging.debug(f"Created SBOM report of type {args.type} for project {args.project_name}, version {args.version_name} at location {location}")
download_report(bd, location, f"{args.project_name}({args.version_name}).zip")

