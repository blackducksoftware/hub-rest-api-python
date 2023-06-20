'''
Created on April 13, 2023
@author: kumykov

##################### DISCLAIMER ##########################
##  This script was created for a specific purpose and   ##
##   SHOULD NOT BE USED as a general purpose utility.    ##
##   For general purpose utility use                     ##
##      /examples/client/generate_sbom.py                ##
###########################################################

Copyright (C) 2023 Synopsys, Inc.
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

This script will trigger SBOM report generation, wait for
completion and then download SBOM report.
Project version will be selected from an EXCEL file.
Each row of a file is expected to contain a field for 
Project Name and Project Version.
Script will iterate through the rows of a spreadsheet and 
process report generation sequentially, one at a time.

Requirements

- python3 version 3.8 or newer recommended
- the following packages are used by the script and should be installed 
  prior to use:	
    argparse
    blackduck
    csv
    logging
    re
    openpyxl
    sys
    time
- Blackduck instance
- API token with sufficient privileges to perform project version phase 
  change.

Install python packages with the following command:

 pip3 install argparse blackduck csv logging re openpyxl sys time

Using

place the token into a file (token in this example) then execute:

 python3 batch_generate_version_details_report -u https://blackduck-host -t token -nv -i excel-file-with-data

Projects and project versions that are listed in the file but are not 
present on the blackduck instance will be skipped.

Report filename will be generated as a combination of project name and version name

usage: Generate and download reports for projets in a spreadsheet 

python3 batch_generate_sbom.py [-h] -u BASE_URL -t TOKEN_FILE -i INPUT_FILE [-nv] 
                [-rt [{SPDX_22,CYCLONEDX_13,CYCLONEDX_14}]] [-tr TRIES] [-s SLEEP_TIME]

options:
  -h, --help            show this help message and exit
  -u BASE_URL, --base-url BASE_URL
                        Hub server URL e.g. https://your.blackduck.url
  -t TOKEN_FILE, --token-file TOKEN_FILE
                        File containing access token
  -i INPUT_FILE, --input-file INPUT_FILE
                        Project Name
  -nv, --no-verify      Disable TLS certificate verification
  -rt [{SPDX_22,CYCLONEDX_13,CYCLONEDX_14}], --type [{SPDX_22,CYCLONEDX_13,CYCLONEDX_14}]
                        Choose the type of SBOM report
  -tr TRIES, --tries TRIES
                        How many times to retry downloading the report, i.e. wait for the report to be generated
  -s SLEEP_TIME, --sleep_time SLEEP_TIME
                        The amount of time to sleep in-between (re-)tries to download the report


'''

import csv
import sys
import argparse
import logging
import re
import openpyxl
import time

from blackduck import Client
from blackduck.constants import VERSION_PHASES

logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stderr, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("blackduck").setLevel(logging.DEBUG)

# Values for the variables below should match corresponding column headers
project_name_column = 'Project Name'
project_version_column = 'Version Name'

summary_report = '''

Summary

'''

class FailedReportDownload(Exception):
	pass

def append_to_summary(message):
    global summary_report
    summary_report += message + '\n'

def process_csv_file(args):
    file = open(args.input_file)
    type(file)
    csvreader = csv.reader(file)
    project_name_idx = None
    project_version_idx = None
    for row in csvreader:
        row_number = csvreader.line_num
        if not (project_name_idx and project_version_idx):
            project_name_idx = row.index(project_name_column)
            project_version_idx = row.index(project_version_column)
        elif project_name_idx and project_version_idx:
            project_name = row[project_name_idx].strip() if project_name_idx < len(row) else ''
            version_name = row[project_version_idx].strip() if project_version_idx < len(row) else ''
            if project_name and version_name:    
                logging.info(f"Processing row {row_number:4}: {row[project_name_idx]} : {row[project_version_idx]}")
                process_project_version(project_name, version_name, args)
            else:
                message = f"Processing row {row_number:}. Invalid data: Project '{project_name}' version '{version_name}', skipping"
                logging.info(message)
                append_to_summary(message)
                continue
        else:
            logging.info("Could not parse input file")
            sys.exit(1)
 
def process_excel_file(args):
    wb = openpyxl.load_workbook(args.input_file)
    ws = wb.active
    project_name_idx = None
    project_version_idx = None
    row_number = 0
    for row in ws.values:
        row_number += 1
        if not (project_name_idx and project_version_idx):
            project_name_idx = row.index(project_name_column)
            project_version_idx = row.index(project_version_column)
        elif project_name_idx and project_version_idx:
            project_name = row[project_name_idx] if project_name_idx < len(row) else ''
            version_name = row[project_version_idx] if project_version_idx < len(row) else ''
            if project_name and version_name:   
                logging.info(f"Processing row {row_number:4}: {row[project_name_idx]} : {row[project_version_idx]}")
                process_project_version(project_name.strip(), version_name.strip(), args)
            else:
                message = f"Processing row {row_number:}. Invalid data: Project '{project_name}' version '{version_name}', skipping"
                logging.info(message)
                append_to_summary(message)
                continue
        else:
            logging.info("Could not parse input file")
            sys.exit(1)
            
def download_report(location, filename, retries, sleep_time):
    report_id = location.split("/")[-1]
    base_url = bd.base_url if bd.base_url.endswith("/") else bd.base_url + "/"
    download_url = f"{base_url}api/reports/{report_id}"

    logging.info(f"Retrieving report status for {location}")

    if retries:
        response = bd.session.get(location)
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
            logging.debug(f"Will retry {retries} more times. Sleeping for {sleep_time} second(s)")
            time.sleep(sleep_time)
            download_report(location, filename, retries, sleep_time)
    else:
        # raise FailedReportDownload(f"Failed to retrieve report {report_id} after multiple retries")
        message = f"Failed to retrieve {filename} for report {report_id} after multiple retries"
        logging.error(message)
        append_to_summary (message)

def process_project_version(project_name, version_name, args):
    params = {
        'q': [f"name:{project_name}"]
    }
    try:
        projects = [p for p in bd.get_resource('projects', params=params) if p['name'] == project_name]
        assert len(projects) == 1, f"There should be one, and only one project named {project_name}. We found {len(projects)}"
        project = projects[0]
    except AssertionError:
        message = f"Project named '{project_name}' not found. Skipping"
        logging.warning(message)
        append_to_summary(message)
        return
    
    params = {
        'q': [f"versionName:{version_name}"]
    }
    
    try:
        versions = [v for v in bd.get_resource('versions', project, params=params) if v['versionName'] == version_name]
        assert len(versions) == 1, f"There should be one, and only one version named {version_name}. We found {len(versions)}"
        version = versions[0]
    except AssertionError:
        message = f"Version name '{version_name}' for project {project_name} was not found, skipping"
        logging.warning(message)
        append_to_summary(message)
        return
    logging.debug(f"Found {project['name']}:{version['versionName']}")

    post_data = {
            'reportFormat': "JSON",
            'reportType': 'SBOM',
            'sbomType': args.type,	
    }
    sbom_reports_url = version['_meta']['href'] + "/sbom-reports"

    r = bd.session.post(sbom_reports_url, json=post_data)
    r.raise_for_status()
    location = r.headers.get('Location')
    assert location, "Hmm, this does not make sense. If we successfully created a report then there needs to be a location where we can get it from"

    logging.debug(f"Created SBOM report of type {args.type} for project {project_name}, version {version_name} at location {location}")
    report_file_name = project_name + "-" + version_name + "-sbom.zip"
    download_report(location, sanitize_filename(report_file_name), args.tries, args.sleep_time)

def sanitize_filename(filename):
    forbidden = '/<>:"\|?*'
    for c in forbidden:
        filename = filename.replace(c,'-')
    return filename


def parse_command_args():

    parser = argparse.ArgumentParser("Generate and download reports for projets in a spreadsheet")
    parser.add_argument("-u", "--base-url",     required=True, help="Hub server URL e.g. https://your.blackduck.url")
    parser.add_argument("-t", "--token-file",   required=True, help="File containing access token")
    parser.add_argument("-i", "--input-file",   required=True, help="Project Name")
    parser.add_argument("-nv", "--no-verify",   action='store_false', help="Disable TLS certificate verification")
    parser.add_argument("-rt", "--type", type=str, nargs='?', default="SPDX_22", choices=["SPDX_22", "CYCLONEDX_13", "CYCLONEDX_14"], help="Choose the type of SBOM report")
    parser.add_argument('-tr', '--tries', default=30, type=int, help="How many times to retry downloading the report, i.e. wait for the report to be generated")
    parser.add_argument('-s', '--sleep_time', default=10, type=int, help="The amount of time to sleep in-between (re-)tries to download the report")
    
    return parser.parse_args()

def main():
    args = parse_command_args()
    with open(args.token_file, 'r') as tf:
        access_token = tf.readline().strip()
    global bd
    bd = Client(base_url=args.base_url, token=access_token, verify=args.no_verify, timeout=60.0, retries=4)

    if re.match(".+xlsx?$", args.input_file):
        logging.info(f"Processing EXCEL file {args.input_file}")
        process_excel_file(args)
    else:
        logging.info(f"Processing CSV file {args.input_file}")
        process_csv_file(args)

    print (summary_report)

if __name__ == "__main__":
    sys.exit(main())
