'''
Created on April 25, 2023
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

This script will tally up project version components by license used and produce output as following

{'(BSD 2-clause "Simplified" License OR Creative Commons Zero v1.0 Universal OR Public Domain)': [('HdrHistogram',
                                                                                                   '2.1.9')],
 '(Common Development and Distribution License 1.1 OR Sun GPL With Classpath Exception v2.0)': [('Jersey '
                                                                                                 'Apache '
                                                                                                 'HTTP '
. . .
 '(GNU General Public License v3.0 only OR Common Development and Distribution License 1.0)': [('StAX',
                                                                                                '1.0-2')],
 'ANTLR Software Rights Notice': [('antlr', '2.7.7')],
 'Apache License 2.0': [('Apache Commons BeanUtils', '1.9.4'),
                        ('Apache Commons Codec', '1.10'),
                        ('Apache Commons Collections', '3.1'),
                        ('Apache Commons Configuration', '1.8'),
                        ('Apache Commons Digester', '3.2'),
. . .

'''

import csv
import sys
import argparse
import logging
from pprint import pprint

from blackduck import Client
from blackduck.constants import VERSION_PHASES

logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stderr, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("blackduck").setLevel(logging.DEBUG)

# Values for the variables below should match corresponding column headers
project_name_column = 'Project Name'
project_version_column = 'Version Name'

summary={}

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
                message = f"Processing row {row_number:4}. Project '{project_name}' version '{version_name}' is not present, skipping"
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
                message = f"Processing row {row_number:}. Project '{project_name}' version '{version_name}' is not present, skipping"
                logging.info(message)
                append_to_summary(message)
                continue
        else:
            logging.info("Could not parse input file")
            sys.exit(1)
            
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
    
    num_versions = bd.get_resource('versions', project, items=False)['totalCount']
    print(num_versions)

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
    for component in bd.get_resource('components',version):
        license_display = component['licenses'][0]['licenseDisplay']
        if license_display not in summary:
            summary[license_display] = []
        l = summary[license_display]
        l.append((component['componentName'],component['componentVersionName']))

def parse_command_args():

    parser = argparse.ArgumentParser("batch_delete_project_version.py")
    parser.add_argument("-u", "--base-url",     required=True, help="Hub server URL e.g. https://your.blackduck.url")
    parser.add_argument("-t", "--token-file",   required=True, help="File containing access token")
    parser.add_argument("-nv", "--no-verify",   action='store_false', help="Disable TLS certificate verification")
    parser.add_argument("project_name", help="Name of the project")
    parser.add_argument("version_name", help="Name of the project version")
    return parser.parse_args()

def main():
    args = parse_command_args()

    with open(args.token_file, 'r') as tf:
        access_token = tf.readline().strip()
    global bd
    bd = Client(base_url=args.base_url, token=access_token, verify=args.no_verify, timeout=60.0, retries=4)

    process_project_version(args.project_name, args.version_name, args)

    pprint (summary)

if __name__ == "__main__":
    sys.exit(main())
