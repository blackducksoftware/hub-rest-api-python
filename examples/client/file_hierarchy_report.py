'''
Created on June 25, 2024

@author: dnichol and kumykov

Generate version detail reports (source and components) and consolidate information on source matches, with license 
and component matched.  Removes matches found underneith other matched components in the source tree (configurable).

Copyright (C) 2023 Synopsys, Inc.
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

import argparse
import logging
import sys
import os
import re
import time
import subprocess
import json
import traceback
import copy
import ijson
from blackduck import Client
from zipfile import ZipFile

program_description = \
'''Generate version detail reports (source and components) and consolidate information on source matches, with license 
and component matched.  Removes matches found underneith other matched components in the source tree (configurable).

This script assumes a project version exists and has scans associated with it (i.e. the project is not scanned as part of this process).

Config file:
API Token and Black Duck URL need to be placed in the .restconfig.json file which must be placed in the same folder where this script resides.
    {
      "baseurl": "https://hub-hostname",
      "api_token": "<API token goes here>",
      "insecure": true or false <Default is false>,
      "debug": true or false <Default is false>
    }

Remarks:
This script uses 3rd party PyPI package "ijson". This package must be installed.
'''

# BD report general
BLACKDUCK_REPORT_MEDIATYPE = "application/vnd.blackducksoftware.report-4+json"
blackduck_report_download_api = "/api/projects/{projectId}/versions/{projectVersionId}/reports/{reportId}/download"
# BD version details report
blackduck_create_version_report_api = "/api/versions/{projectVersionId}/reports"
blackduck_version_report_filename = "./blackduck_version_report_for_{projectVersionId}.zip"
# Consolidated report
BLACKDUCK_VERSION_MEDIATYPE = "application/vnd.blackducksoftware.status-4+json"
BLACKDUCK_VERSION_API = "/api/current-version"
REPORT_DIR = "./blackduck_component_source_report"
# Retries to wait for BD report creation. RETRY_LIMIT can be overwritten by the script parameter. 
RETRY_LIMIT = 30
RETRY_TIMER = 30

def log_config(debug):
    if debug:
        logging.basicConfig(format='%(asctime)s:%(levelname)s:%(module)s: %(message)s', stream=sys.stderr, level=logging.DEBUG)
    else:
        logging.basicConfig(format='%(asctime)s:%(levelname)s:%(module)s: %(message)s', stream=sys.stderr, level=logging.INFO)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("blackduck").setLevel(logging.WARNING)

def parse_parameter():
    parser = argparse.ArgumentParser(description=program_description, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("project",
                        metavar="project",
                        type=str,
                        help="Provide the BlackDuck project name.")
    parser.add_argument("version",
                        metavar="version",
                        type=str,
                        help="Provide the BlackDuck project version name.")
    parser.add_argument("-kh",
                        "--keep_hierarchy",
                        action='store_true',
                        help="Set to keep all entries in the sources report. Will not remove components found under others.")
    parser.add_argument("-rr",
                        "--report_retries",
                        metavar="",
                        type=int,
                        default=RETRY_LIMIT,
                        help="Retries for receiving the generated BlackDuck report. Generating copyright report tends to take longer minutes.")
    parser.add_argument("-t",
                        "--timeout",
                        metavar="",
                        type=int,
                        default=15,
                        help="Timeout for REST-API. Some API may take longer than the default 15 seconds")
    parser.add_argument("-r",
                        "--retries",
                        metavar="",
                        type=int,
                        default=3,
                        help="Retries for REST-API. Some API may need more retries than the default 3 times")
    return parser.parse_args()

def get_bd_project_data(hub_client, project_name, version_name):
    """ Get and return project ID, version ID. """
    project_id = ""
    for project in hub_client.get_resource("projects"):
        if project['name'] == project_name:
            project_id = (project['_meta']['href']).split("projects/", 1)[1]
            break
    if project_id == "":
        sys.exit(f"No project for {project_name} was found!")
    version_id = codelocations = ""
    for version in hub_client.get_resource("versions", project):
        if version['versionName'] == version_name:
            version_id = (version['_meta']['href']).split("versions/", 1)[1]
            break
    if version_id == "":
        sys.exit(f"No project version for {version_name} was found!")

    return project_id, version_id

def report_create(hub_client, url, body):
    """ 
    Request BlackDuck to create report. Requested report is included in the request payload.
    """
    res = hub_client.session.post(url, headers={'Content-Type': BLACKDUCK_REPORT_MEDIATYPE}, json=body)
    if res.status_code != 201:
        sys.exit(f"BlackDuck report creation failed with status {res.status_code}!") 
    return res.headers['Location'] # return report_url

def report_download(hub_client, report_url, project_id, version_id, retries):
    """
    Download the generated report after the report completion. We will retry until reaching the retry-limit.
    """
    while retries:
        res = hub_client.session.get(report_url, headers={'Accept': BLACKDUCK_REPORT_MEDIATYPE})
        if res.status_code == 200 and (json.loads(res.content))['status'] == "COMPLETED":
            report_id = report_url.split("reports/", 1)[1]
            download_url = (((blackduck_report_download_api.replace("{projectId}", project_id))
                     .replace("{projectVersionId}", version_id))
                     .replace("{reportId}", report_id))  
            res = hub_client.session.get(download_url, 
                                         headers={'Content-Type': 'application/zip', 'Accept':'application/zip'})
            if res.status_code != 200:
                sys.exit(f"BlackDuck report download failed with status {res.status_code} for {download_url}!")
            return res.content
        elif res.status_code != 200:
            sys.exit(f"BlackDuck report creation not completed successfully with status {res.status_code}")
        else:
            retries -= 1
            logging.info(f"Waiting for the report generation for {report_url} with the remaining retries {retries} times.")
            time.sleep(RETRY_TIMER)
    sys.exit(f"BlackDuck report for {report_url} was not generated after retries {RETRY_TIMER} sec * {retries} times!")

def get_version_detail_report(hub_client, project_id, version_id, retries):
    """ Create and get BOM component and BOM source file report in json. """
    create_version_url = blackduck_create_version_report_api.replace("{projectVersionId}", version_id)
    body = {
        'reportFormat' : 'JSON',
        'locale' : 'en_US',
        'versionId' : f'{version_id}',
        'categories' : [ 'COMPONENTS', 'FILES' ] # Generating "project version" report including components and files
    }
    report_url = report_create(hub_client, create_version_url, body)
    # Zipped report content is received and write the content to a local zip file 
    content = report_download(hub_client, report_url, project_id, version_id, retries)
    output_file = blackduck_version_report_filename.replace("{projectVersionId}", version_id)
    with open(output_file, "wb") as f:
        f.write(content)
        return output_file

def get_blackduck_version(hub_client):
    url = hub_client.base_url + BLACKDUCK_VERSION_API
    res = hub_client.session.get(url)
    if res.status_code == 200 and res.content:
        return json.loads(res.content)['version']
    else:
        sys.exit(f"Get BlackDuck version failed with status {res.status_code}")

def generate_file_report(hub_client, project_id, version_id, keep_hierarchy, retries):
    """ 
    Create a consolidated file report from BlackDuck project version source and components reports.
    Remarks: 
    """
    if not os.path.exists(REPORT_DIR):
        os.makedirs(REPORT_DIR)
    
    # Report body - Component BOM, file BOM with Discoveries data
    version_report_zip = get_version_detail_report(hub_client, project_id, version_id, retries)
    with ZipFile(f"./{version_report_zip}", "r") as vzf:
        vzf.extractall()
    for i, unzipped_version in enumerate(vzf.namelist()):
        if re.search(r"\bversion.+json\b", unzipped_version) is not None:
            break
        if i + 1 >= len(vzf.namelist()):
            sys.exit(f"Version detail file not found in the downloaded report: {version_report_zip}!")
    
    # Report body - Component BOM report
    with open(f"./{unzipped_version}", "r") as uvf:
        for i, comp_bom in enumerate(ijson.items(uvf, 'aggregateBomViewEntries.item')):
            logging.info(f"{comp_bom['componentName']}")
        logging.info(f"Number of the reported components {i+1}")
      

def main():
    args = parse_parameter()
    debug = 0
    try:
        if args.project == "":
            sys.exit("Please set BlackDuck project name!")
        if args.version == "":
            sys.exit("Please set BlackDuck project version name!")

        with open(".restconfig.json", "r") as f:
            config = json.load(f)
            # Remove last slash if there is, otherwise REST API may fail.
            if re.search(r".+/$", config['baseurl']):
                bd_url = config['baseurl'][:-1]
            else:
                bd_url = config['baseurl']
            bd_token = config['api_token']
            bd_insecure = not config['insecure']
            if config['debug']:
                debug = 1
        
        log_config(debug)    

        hub_client = Client(token=bd_token,
                            base_url=bd_url,
                            verify=bd_insecure,
                            timeout=args.timeout,
                            retries=args.retries)
        
        project_id, version_id = get_bd_project_data(hub_client, args.project, args.version)

        generate_file_report(hub_client,
                             project_id,
                             version_id,
                             args.keep_hierarchy,
                             args.report_retries
                             )

    except (Exception, BaseException) as err:
        logging.error(f"Exception by {str(err)}. See the stack trace")
        traceback.print_exc()

if __name__ == '__main__':
    sys.exit(main())
