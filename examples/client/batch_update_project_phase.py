'''
Created on April 4, 2023
@author: kumykov

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

This script will perform bulk update of Project version PHASE based on 
the content of an EXCEL file. Each row of a file is expected to contain 
a field for Project Name Project Version and desired phase.
Script will iterate through the rows of a spreadsheet and issue an API 
call per row.

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
- Blackduck instance
- API token with sufficient privileges to perform project version phase 
  change.

Install python packages with the following command:

 pip3 install argparse blackduck csv logging re openpyxl sys

Using

place the token into a file (token in this example) then execute:

 python3 batch_update_project_phase.py -u https://blackduck-host -t token -nv -i excel-file-with-data

Projects and project versions that are listed in the file but are not 
present on the blackduck instance will be skipped.
If a project version is already at a requested phase, no update will 
be executed.

'''

import csv
import sys
import argparse
import logging
import re
import openpyxl

from blackduck import Client
from blackduck.constants import VERSION_PHASES

logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stderr, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("blackduck").setLevel(logging.DEBUG)

# Values for the variables below should match corresponding column headers
project_name_column = 'Project Name'
project_version_column = 'Version Name'
project_phase_column = 'Version phase'

summary_report = '''

Summary

'''

def append_to_summary(message):
    global summary_report
    summary_report += message + '\n'

def process_csv_file(filename):
    file = open(filename)
    type(file)
    csvreader = csv.reader(file)
    project_name_idx = None
    project_version_idx = None
    project_phase_idx = None
    for row in csvreader:
        row_number = csvreader.line_num
        if (project_name_idx == None and project_version_idx == None and project_phase_idx == None):
            project_name_idx = row.index(project_name_column)
            project_version_idx = row.index(project_version_column)
            project_phase_idx = row.index(project_phase_column)
        elif project_name_idx != None and project_version_idx != None and project_phase_idx != None:
            project_name = row[project_name_idx].strip() if project_name_idx < len(row) else ''
            version_name = row[project_version_idx].strip() if project_version_idx < len(row) else ''
            phase = row[project_phase_idx] if project_phase_idx < len(row) else ''
            if project_name and version_name and phase and phase.strip().upper() in VERSION_PHASES:   
                logging.info(f"Processing row {row_number:4}: {row[project_name_idx]} : {row[project_version_idx]} with {row[project_phase_idx]}")
                process_project_version(project_name, version_name, phase.strip().upper())
            else:
                message = f"Processing row {row_number:}. Invalid data: Project '{project_name}' version '{version_name}' phase '{phase}', skipping"
                logging.info(message)
                append_to_summary(message)
                continue
        else:
            logging.info("Could not parse input file")
            sys.exit(1)

 
def process_excel_file(filename):
    wb = openpyxl.load_workbook(filename)
    ws = wb.active
    project_name_idx = None
    project_version_idx = None
    project_phase_idx = None
    row_number = 0
    for row in ws.values:
        row_number += 1
        if (project_name_idx == None and project_version_idx == None and project_phase_idx == None):
            project_name_idx = row.index(project_name_column)
            project_version_idx = row.index(project_version_column)
            project_phase_idx = row.index(project_phase_column)
        elif project_name_idx != None and project_version_idx != None and project_phase_idx != None:
            project_name = row[project_name_idx] if project_name_idx < len(row) else ''
            version_name = row[project_version_idx] if project_version_idx < len(row) else ''
            phase = row[project_phase_idx] if project_phase_idx < len(row) else ''
            if project_name and version_name and phase and phase.strip().upper() in VERSION_PHASES:   
                logging.info(f"Processing row {row_number:4}: {row[project_name_idx]} : {row[project_version_idx]} with {row[project_phase_idx]}")
                process_project_version(project_name.strip(), version_name.strip(), phase.strip().upper())
            else:
                message = f"Processing row {row_number:}. Invalid data: Project '{project_name}' version '{version_name}' phase '{phase}', skipping"
                logging.info(message)
                append_to_summary(message)
                continue
        else:
            logging.info("Could not parse input file")
            sys.exit(1)
            
def process_project_version(project_name, version_name, phase):
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

    if phase == version['phase' ]:
        logging.info(f"Project {project_name} version {version_name} is already at {phase}. No update")
        return
    
    logging.debug(f"Updating {project['name']}:{version['versionName']} settings to {phase}")
    version['phase'] = phase
    try:
        r = bd.session.put(version['_meta']['href'], json=version)
        r.raise_for_status()
        logging.debug(f"updated version settings to the new phase ({phase})")
    except requests.HTTPError as err:
        bd.http_error_handler(err)


def parse_command_args():

    parser = argparse.ArgumentParser("Print copyrights for BOM using upstream origin or prior version if not available.")
    parser.add_argument("-u", "--base-url",     required=True, help="Hub server URL e.g. https://your.blackduck.url")
    parser.add_argument("-t", "--token-file",   required=True, help="File containing access token")
    parser.add_argument("-i", "--input-file",   required=True, help="Project Name")
    parser.add_argument("-nv", "--no-verify",   action='store_false', help="Disable TLS certificate verification")

    return parser.parse_args()

def main():
    args = parse_command_args()
    with open(args.token_file, 'r') as tf:
        access_token = tf.readline().strip()
    global bd
    bd = Client(base_url=args.base_url, token=access_token, verify=args.no_verify, timeout=60.0, retries=4)

    if re.match(".+xlsx?$", args.input_file):
        logging.info(f"Processing EXCEL file {args.input_file}")
        process_excel_file(args.input_file)
    else:
        logging.info(f"Processing CSV file {args.input_file}")
        process_csv_file(args.input_file)

    print (summary_report)

if __name__ == "__main__":
    sys.exit(main())
