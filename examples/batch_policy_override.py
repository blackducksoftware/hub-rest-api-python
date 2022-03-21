'''
Created on October 5, 2021
@author: kumykov

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

This scrit will override policies for components that are listed in a CSV or an EXCEL file
Cmponents with status IN_VIOLATION will get policy status to IN_VIOLATION_OVERRIDEN

Note: Override will happen only when the Override Date field is blank.
      Rows with blank Override Date and Ovveride Rationale will be ignored.

Note: EXCEL processing is rather simplistic, it will not process milti-sheet workbooks properly.
      It will skip all the header rows, until it finds "Name of Software Component" header.
      Rows after that will be processed according to abovementioned rules.

identification of a project and cmponent wil be done based n following fields in the input file

        component_name          = field 0  (Column A in Excel lingo)
        component_version       = field 1 (Column B in Excel lingo)
        policy_violation_status = field 8 (Column I in Excel lingo)
        override_rationale      = field 11 (Column L in Excel lingo)
        project_name            = field 13 (Column N in Excel lingo)
        project_version         = field 14 (Column O in Excel lingo)

Usage: 

python3 batch_policy_override.py [OPTIONS]

OPTIONS:
    -h                              Show help
    -u BASE_URL                     URL of a Blackduck system
    -t TOKEN_FILE                   Authentication token file
    -i INPUT_FILE                   Input CSV or EXCEL file
    -nv                             Trust TLS certificate


Below are original script requirements

Script Requirements
The input to the script is the Alteryx report (see enclosed spreadsheet).
If needed, we could produce a separate spreadsheet from the Alteryx report 
that contains ONLY the information the script needs to update BlackDuck (TBD).
Key fields in the Alteryx report that I expect to be relevant to the script:
  Name of Software Component (Column A) - component name as identified by BD
  Version number (Column B) - component version as identified by BD
  Component Policy Status (Column I) - NOT_IN_VIOLATION, IN_VIOLATION, IN_VIOLATION_OVERRIDEN 
                                       as determined by BD (the script would only look for 
                                       components that are shown as “IN_VIOLATION”)
  Override Rationale (Column L) - Alteryx will export whatever Override comment is already in BD.  
                                  For components IN_VIOLATION, this column will be used to work 
                                  iteratively on the draft Override comment.
  project_name (Column N) - Project name used by the product team for the BD scan
  version_number (Column O) - Project version used by the product team for the BD scan

The script would parse the spreadsheet and for each component that has a status of “IN_VIOLATION”, it would:
Upload the Override Rationale (Column L) into the Override Comment field for that component in BD (for that project name/version).
Update the Override Date to “now” (not sure of the best way to get the correct date-stamp).
Update the Overridden Field with the name of the individual running the script (not sure of the best way to get the individual’s identity).
Not sure if the Component Policy Status field needs to be updated to IN_VIOLATION_OVERRIDEN by the script or if BD will do it automatically once the Override Comment has been added.
Since our Alteryx BOMs are multi-level BOMs, the script cannot assume that all the components belong to the same project/version combination (the enclosed example has 2 sub-projects).
If a BOM containing components from more than one sub-project is highly problematic for the script, we could consider limiting the use of the script to a single project at the time.

'''
import csv
import sys
import argparse
import json
import logging
import arrow
import re

from itertools import islice
from datetime  import timedelta
from datetime import datetime
from blackduck import Client

logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stderr, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("blackduck").setLevel(logging.DEBUG)

def override_policy_violaton(project_name, project_version, component_name, component_version, override_rationale):
    params = {"q": f"name:{project_name}"}
    projects = bd.get_resource('projects', params=params)
    for project in projects:
        if project['name'] == project_name:
            versions = bd.get_resource('versions', project)
            for version in versions :
                if version['versionName'] == project_version:
                    params = {"q":f"componentOrVersionName:{component_name}"}
                    components = bd.get_resource('components', version, params=params)
                    for component in components:
                        policy_status = bd.get_resource('policy-status', component, items=False)
                        url = bd.list_resources(policy_status)['href']
                        data = {
                                "approvalStatus" : "IN_VIOLATION_OVERRIDDEN",
                                "comment" : f"{override_rationale}",
                                "updatedAt" : datetime.now().isoformat()
                                }
                        headers = {"Content-Type": "application/vnd.blackducksoftware.bill-of-materials-6+json",
                                    "Accept": "application/vnd.blackducksoftware.bill-of-materials-6+json" }
                        r = bd.session.put(url, headers = headers, json=data)
                        # r.raise_for_status()
                        logging.info(f"Policy status update completion code {r.status_code}")


def parse_command_args():

    parser = argparse.ArgumentParser("Print copyrights for BOM using upstream origin or prior version if not available.")
    parser.add_argument("-u", "--base-url",     required=True, help="Hub server URL e.g. https://your.blackduck.url")
    parser.add_argument("-t", "--token-file",   required=True, help="File containing access token")
    parser.add_argument("-i", "--input-file",   required=True, help="Project Name")
    parser.add_argument("-nv", "--no-verify",   action='store_false', help="Disable TLS certificate verification")

    return parser.parse_args()

def process_csv_file(filename):
    file = open(args.input_file)
    type(file)
    csvreader = csv.reader(file)
    for row in csvreader:
        component_name = row[0]
        component_version = row[1]
        policy_violation_status = row[8]
        override_date = row[10]
        override_rationale = row[11]
        project_name = row[13]
        project_version = row[14]
        if policy_violation_status == 'IN_VIOLATION' and override_rationale and not override_date:
            logging.info(f"Attemting to override policy status for {component_name} {component_version} in {project_name} {project_version} with ''{override_rationale}''")
            override_policy_violaton(project_name, project_version, component_name, component_version, override_rationale)

def process_excel_file(filename):
    import openpyxl
    wb = openpyxl.load_workbook(filename)
    ws = wb.active
    process = False
    for row in ws.values:
        if process:
            component_name = row[0]
            component_version = row[1]
            policy_violation_status = row[8]
            override_date = row[10]
            override_rationale = row[11]
            project_name = row[13]
            project_version = row[14]
            if policy_violation_status == 'IN_VIOLATION' and override_rationale and not override_date:
                print ("overriding")
                logging.info(f"Attemting to override policy status for {component_name} {component_version} in {project_name} {project_version} with ''{override_rationale}''")
                override_policy_violaton(project_name, project_version, component_name, component_version, override_rationale)
        if not process:
            process = (row[0] == "Name of Software Component")

def main():
    args = parse_command_args()
    with open(args.token_file, 'r') as tf:
        access_token = tf.readline().strip()
    global bd
    bd = Client(base_url=args.base_url, token=access_token, verify=args.no_verify, timeout=60.0, retries=4)

    if re.match(".+xlsx?$", args.input_file):
        print (f"Processing EXCEL file {args.input_file}")
        process_excel_file(args.input_file)
    else:
        print ("Processing as CSV")
        process_csv_file(args.input_file)

if __name__ == "__main__":
    sys.exit(main())
