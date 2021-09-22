'''
Created on Sep 22, 2021

@author: gsnyder

Generate Notices report for a given project-version

ref: https://your-blackduck-server/doc/Welcome.htm#reporting/noticesfilereport.htm?Highlight=notice
'''

'''
Copyright (C) 2021 Synopsys, Inc.
http://www.synopsys.com/

Licensed to the Apache Software Foundation (ASF) under one
or more contributor license agreements. See the NOTICE file
distributed with this work for additional information
regarding copyright ownership. The ASF licenses this file
to you under the Apache License, Version 2.0 (the
"License"); you may not use this file except in compliance
with the License. You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
KIND, either express or implied. See the License for the
specific language governing permissions and limitations
under the License.
 
'''

from blackduck import Client
from blackduck.Utils import object_id

import argparse
import json
import logging
import sys
import time

logging.basicConfig(
    level=logging.DEBUG,
    format="[%(asctime)s] {%(module)s:%(lineno)d} %(levelname)s - %(message)s"
)

class FailedReportDownload(Exception):
	pass


parser = argparse.ArgumentParser("A program to create notices report for a given project-version")
parser.add_argument("bd_url", help="Hub server URL e.g. https://your.blackduck.url")
parser.add_argument("token_file", help="containing access token")
parser.add_argument("project_name")
parser.add_argument("version_name")
parser.add_argument('-fnb', "--file_name_base", default="notices_report", help="Base file name to write the report data into. If the report format is TEXT a .zip file will be created, otherwise a .json file")
parser.add_argument('-f', '--format', default='TEXT', choices=["JSON", "TEXT"], help="Report format")
parser.add_argument('-t', '--tries', default=10, type=int, help="How many times to retry downloading the report, i.e. wait for the report to be generated")
parser.add_argument('-s', '--sleep_time', default=5, type=int, help="The amount of time to sleep in-between (re-)tries to download the report")
parser.add_argument('-c', '--include_copyright_info', action='store_true', help="Set this option to have additional copyright information from the Black Duck KB included in the notices file report.")
parser.add_argument('--no-verify', dest='verify', action='store_false', help="disable TLS certificate verification")

args = parser.parse_args()

def download_notification_report(bd, report_location_url):
    '''Download the notices report using the report URL. Inspect the report object to determine
    the format and use the appropriate media header'''

    headers = {'Accept': 'application/vnd.blackducksoftware.report-4+json'}
    response = bd.session.get(report_location_url, headers=headers)
    report_obj = response.json()

    if report_obj['reportFormat'] == 'TEXT':
        download_url = bd.list_resources(report_obj).get("download") + ".json"
        logging.debug(f"downloading report from {download_url}")
        response = bd.session.get(download_url, headers={'Accept': 'application/zip'})
    else:
        # JSON
        contents_url = bd.list_resources(report_obj).get("content")
        logging.debug(f"retrieving report contents from {contents_url}")
        response = bd.session.get(contents_url, headers={'Accept': 'application/json'})
    return response, report_obj['reportFormat']

DOWNLOAD_ERROR_CODES = ['{report.main.read.unfinished.report.contents}', '{report.main.download.unfinished.report}']

def download_report(bd, location, file_name_base, retries=10, sleep_time=5):
	'''This function uses recursion to re-try downloading a report from the given location (URL). The reports take
	some time to be generated so it may take several retries before the report is ready for download. Adjust retries
	and sleep_time accordingly
	'''
    report_id = location.split("/")[-1]

    if retries:
        logging.debug(f"Retrieving generated report from {location}")
        response, report_format = download_notification_report(bd, location)

        if response.status_code == 200:
            if report_format == "TEXT":
                filename = file_name_base + ".zip"
                with open(filename, "wb") as f:
                    f.write(response.content)
            else:
                # JSON format
                filename = file_name_base + ".json"
                with open(filename, "w") as f:
                    json.dump(response.json(), f, indent=3)
            logging.info(f"Successfully downloaded json file to {filename} for report {report_id}")
        elif response.status_code == 412 and response.json()['errorCode'] in DOWNLOAD_ERROR_CODES:
            # failed to download, and report generation still in progress, wait and try again infinitely
            # TODO: is it possible for things to get stuck in this forever?
            logging.warning(f"Failed to retrieve report {report_id} for reason {response.json()['errorCode']}.  Waiting 5 seconds then trying infinitely")
            time.sleep(sleep_time)
            download_report(bd, location, file_name_base, retries)
        else:
            logging.warning(f"Failed to retrieve report, status code {response.status_code}")
            logging.warning(f"Probably not ready yet, waiting 5 seconds then retrying (remaining retries={retries}")
            time.sleep(sleep_time)
            retries -= 1
            download_report(bd, location, file_name_base, retries)
    else:
        raise FailedReportDownload(f"Failed to retrieve report {report_id} after multiple retries")

#
# Connect to Black Duck server and find the project-version
#
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

#
# Generate the notices report and download it
#
post_data = {
        'versionId': object_id(version),
        'reportType': 'VERSION_LICENSE',
        'reportFormat': args.format	
}
license_reports_url = bd.list_resources(version).get('licenseReports')
assert license_reports_url, "Ruh-roh, a version should always have a licenseReports resource under it"

r = bd.session.post(license_reports_url, json=post_data)
r.raise_for_status()
location = r.headers.get('Location')
assert location, "Hmm, this does not make sense. If we successfully created a report then there needs to be a location where we can get it from"

logging.debug(f"Created notices report for project {args.project_name}, version {args.version_name} at location {location}")
download_report(bd, location, args.file_name_base, args.tries, args.sleep_time)

