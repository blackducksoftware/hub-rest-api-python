#!/usr/bin/env python

'''
Copyright (C) 2021 Synopsys, Inc.
http://www.blackducksoftware.com/

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
import argparse
from datetime import datetime
import json
import logging
import requests
import sys
import time

from dateutil.parser import parse # for parsing of input date/time strings

from blackduck import Client

# TODO: Refactor and put these contants into blackduck/constants in a new version of the Client lib
remediation_types = [
    'DUPLICATE',
    'IGNORED',
    'MITIGATED',
    'NEEDS_REVIEW',
    'NEW',
    'PATCHED',
    'REMEDIATION_COMPLETE',
    'REMEDIATION_REQUIRED'
]

DEFAULT_OUTPUT_FILE="vuln_remediation_report.json"

parser = argparse.ArgumentParser("Generate a vulnerability remediation report")
parser.add_argument("base_url", help="Hub server URL e.g. https://your.blackduck.url")
parser.add_argument("token_file", help="containing access token")
parser.add_argument("projects", nargs="+", help="The list of projects to include in the report")
parser.add_argument("-s", "--start-date", dest="start_date", required=True, help="The start date for the report (required)")
parser.add_argument("-e", "--end-date", 
    dest="end_date", 
    help="The end date for the report. Default is today/now")
parser.add_argument("-f", "--format", 
    choices=['JSON', 'CSV'], 
    default='JSON',
    help="The report format (either CSV or JSON, default: JSON)")
parser.add_argument("-r", "--remediation-types", 
    dest="remediation_types", 
    default = remediation_types,
    nargs="+", 
    help=f"The remediation types which can be one or more of the following: {remediation_types}. The default is all remediation types")
parser.add_argument('-t', '--tries', default=10, type=int, help="How many times to retry downloading the report, i.e. wait for the report to be generated")
parser.add_argument("-o", "--output-file-name", 
    dest="file_name", 
    default=DEFAULT_OUTPUT_FILE, 
    help=f"Name of the output file (default: {DEFAULT_OUTPUT_FILE})")
parser.add_argument("--no-verify", 
    dest='verify', 
    action='store_false', 
    help="disable TLS certificate verification")
args = parser.parse_args()


logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stdout, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("blackduck").setLevel(logging.WARNING)

class FailedReportDownload(Exception):
    pass

def download_vuln_report(bd_client, location, filename, report_format, retries=args.tries):
    if retries:
        report_status = bd_client.session.get(location).json()
        if report_status['status'] == 'COMPLETED':
            download_url = bd_client.list_resources(report_status)['download']
            contents_url = download_url + "/contents"
            report_contents = bd_client.session.get(contents_url).json()
            if report_format == 'JSON':
                with open(filename, 'w') as f:
                    json.dump(report_contents, f, indent=3)
                    logging.info(f"Wrote vulnerability remediation report contents to {filename}")
            elif report_format == 'CSV':
                csv_data = report_contents['reportContent'][0]['fileContent']
                with open(filename, 'w') as f:
                    f.write(csv_data)
                    logging.info(f"Wrote vulnerability remediation report contents to {filename}")
            else:
                logging.error(f"Unrecognized format ({report_format}) given. Exiting")

        else:
            sleep_time = 5
            retries -= 1
            logging.debug(f"Report is not ready to download yet, waiting {sleep_time} seconds and then retrying {retries} more times")
            time.sleep(sleep_time)
            download_vuln_report(bd_client, location, filename, report_format, retries)
    else:
        raise FailedReportDownload(f"Failed to retrieve report from {location} after {retries} attempts")


def get_projects(client, project_names):
    '''Given a list of project names return a list of the corresponding project URLs'''
    project_urls = list()
    for project in client.get_items("/api/projects"):
        if project['name'] in project_names:
            project_urls.append(project['_meta']['href'])
    return project_urls

with open(args.token_file, 'r') as tf:
    access_token = tf.readline().strip()

bd = Client(
    base_url=args.base_url,
    token=access_token,
    verify=args.verify
)

start_date = parse(args.start_date)
end_date = parse(args.end_date) if args.end_date else datetime.now()
project_urls = get_projects(bd, args.projects)

logging.debug(f"Generating vulnerability remediation report for the following projects: {args.projects}")
logging.debug(f"start date: {start_date}, end date: {end_date}")
post_data = {
    'startDate': start_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
    'reportFormat': args.format,
    'projects': project_urls,
    'locale': 'en_US'
}

if end_date:
    post_data.update({
        'endDate': end_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
        })

try:
    r = bd.session.post("/api/vulnerability-remediation-reports", json=post_data)
    r.raise_for_status()
    report_url = r.headers['Location']
    logging.debug(f"created vulnerability remediation report {report_url}")
except requests.HTTPError as err:
    # more fine grained error handling here; otherwise:
    bd.http_error_handler(err)
    logging.error("Failed to generate the report")
    sys.exit(1)

download_vuln_report(bd, report_url, args.file_name, args.format, retries=args.tries)









