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
import csv

from blackduck import Client

DEFAULT_OUTPUT_FILE="vuln_status_report.csv"

parser = argparse.ArgumentParser("Generate a vulnerability status report")
parser.add_argument("--base-url", help="Hub server URL e.g. https://your.blackduck.url")
parser.add_argument("--token-file", help="containing access token")
parser.add_argument("--projects", nargs="+", help="The list of projects to include in the report")
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
                    logging.info(f"Wrote vulnerability status report contents to {filename}")
            elif report_format == 'CSV':
                csv_data = report_contents['reportContent'][0]['fileContent']
                with open(filename, 'w') as f:
                    f.write(csv_data)
                    logging.info(f"Wrote vulnerability status report contents to {filename}")
            else:
                logging.error(f"Unrecognized format ({report_format}) given. Exiting")

        else:
            sleep_time = 25
            retries -= 1
            logging.debug(f"Report is not ready to download yet, waiting {sleep_time} seconds and then retrying {retries} more times")
            time.sleep(sleep_time)
            download_vuln_report(bd_client, location, filename, report_format, retries)
    else:
        raise FailedReportDownload(f"Failed to retrieve report from {location} after {retries} attempts")


def get_projects(client, project_names):
    print (project_names)
    '''Given a list of project names return a list of the corresponding project URLs'''
    project_urls = list()
    for project in client.get_items("/api/projects"):
        if project['name'] in project_names:
            project_urls.append(project['_meta']['href'])
    return project_urls

def augment_filename(filename):
    if filename.endswith('.csv'):
        index = filename.index('.csv')
        return filename[:index] + '_augmented' + filename[index:]
    else:
        return filename + '_augmented.csv'

def correct_vuln_ids(bd, filename, new_filename):
    logging.debug(f"Generating file with augmented vuln ids as {new_filename}")
    input = open(filename, 'r')
    reader = csv.DictReader(input)
    fieldnames = reader.fieldnames
    rowcount = 0
    with open(new_filename, 'w') as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for row in reader:
            vuln_id = row['Vulnerability id']
            related_vuln_id = get_related_vuln_id(bd, vuln_id)
            if related_vuln_id:
                correct_vuln_id = f"{vuln_id} ({related_vuln_id})"
            else:
                correct_vuln_id = vuln_id
            row['Vulnerability id'] = correct_vuln_id
            writer.writerow(row)
            rowcount+=1
            if rowcount % 100 == 0:
                logging.debug(f"{rowcount:15} rows written into {new_filename}")
        logging.debug(f"Total of {rowcount} rows written into {new_filename}")
    logging.info(f"Wrote vulnerability status report contents to {filename}")

def get_related_vuln_id(bd, vuln_id):
    related_id = None
    if vuln_id.startswith('BDSA') and 'CVE' not in vuln_id:
        vuln_data = bd.get_json(f"/api/vulnerabilities/{vuln_id}")
        vuln_resources = bd.list_resources(vuln_data)
        related_url = vuln_resources.get('related-vulnerability', None)
        if related_url:
            related_id = related_url.split('/')[-1:][0]
    return related_id

with open(args.token_file, 'r') as tf:
    access_token = tf.readline().strip()

bd = Client(
    base_url=args.base_url,
    token=access_token,
    verify=args.verify
)

project_urls = get_projects(bd, args.projects)
logging.debug(f"Generating vulnerability status report for the following projects: {args.projects}")
logging.debug(f"Project list resulted in following project URLs {project_urls}")
post_data = {
    'reportFormat': 'CSV',
    'projects': project_urls,
    'locale': 'en_US'
}

try:
    r = bd.session.post("/api/vulnerability-status-reports", json=post_data)
    r.raise_for_status()
    report_url = r.headers['Location']
    logging.debug(f"created vulnerability status report {report_url}")
except requests.HTTPError as err:
    # more fine grained error handling here; otherwise:
    bd.http_error_handler(err)
    logging.error("Failed to generate the report")
    sys.exit(1)

download_vuln_report(bd, report_url, args.file_name, 'CSV', retries=args.tries)

correct_vuln_ids(bd, args.file_name, augment_filename(args.file_name))









