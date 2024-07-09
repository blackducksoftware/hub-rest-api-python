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
import io
import time
import json
import traceback
from blackduck import Client
from zipfile import ZipFile
from pprint import pprint

program_description = \
'''Generate version detail reports (source and components) and consolidate information on source matches, with license 
and component matched.  Removes matches found underneath other matched components in the source tree (configurable).

This script assumes a project version exists and has scans associated with it (i.e. the project is not scanned as part of this process).

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

def find_project_by_name(bd, project_name):
    params = {
        'q': [f"name:{project_name}"]
    }
    projects = [p for p in bd.get_resource('projects', params=params) if p['name'] == project_name]
    assert len(projects) == 1, f"Project {project_name} not found."
    return projects[0]

def find_project_version_by_name(bd, project, version_name):
    params = {
        'q': [f"versionName:{version_name}"]
    }
    versions = [v for v in bd.get_resource('versions', project, params=params) if v['versionName'] == version_name]
    assert len(versions) == 1, f"Project version {version_name} for project {project['name']} not found"
    return versions[0]

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

def create_version_details_report(bd, version):
    version_reports_url = bd.list_resources(version).get('versionReport')
    post_data = {
        'reportFormat' : 'JSON',
        'locale' : 'en_US',
        'versionId': version['_meta']['href'].split("/")[-1],
        'categories' : [ 'COMPONENTS', 'FILES' ] # Generating "project version" report including components and files
    }

    bd.session.headers["Content-Type"] = "application/vnd.blackducksoftware.report-4+json"
    r = bd.session.post(version_reports_url, json=post_data)
    if (r.status_code == 403):
        logging.debug("Authorization Error - Please ensure the token you are using has write permissions!")
    r.raise_for_status()
    location = r.headers.get('Location')
    assert location, "Hmm, this does not make sense. If we successfully created a report then there needs to be a location where we can get it from"
    return location

def download_report(bd, location, retries):
    report_id = location.split("/")[-1]
    logging.debug(f"Report location {location}")
    url_data = location.split('/')
    url_data.pop(4)
    url_data.pop(4)
    download_link = '/'.join(url_data)
    logging.debug(f"Report Download link {download_link}")
    if retries:
        logging.debug(f"Retrieving generated report for {location}  via  {download_link}")
        response = bd.session.get(location)
        report_status = response.json().get('status', 'Not Ready')
        if response.status_code == 200 and report_status == 'COMPLETED':
            response = bd.session.get(download_link, headers={'Content-Type': 'application/zip', 'Accept':'application/zip'})
            if response.status_code == 200:
                return response.content
            else:
                logging.error("Ruh-roh, not sure what happened here")
                return None
        else:
            logging.debug(f"Report status request {response.status_code} {report_status} ,waiting {retries} seconds then retrying...")
            time.sleep(60)
            retries -= 1
            return download_report(bd, location, retries)
    else:
        logging.debug(f"Failed to retrieve report {report_id} after multiple retries")
        return None

def get_blackduck_version(hub_client):
    url = hub_client.base_url + BLACKDUCK_VERSION_API
    res = hub_client.session.get(url)
    if res.status_code == 200 and res.content:
        return json.loads(res.content)['version']
    else:
        sys.exit(f"Get BlackDuck version failed with status {res.status_code}")

def parse_command_args():
    parser = argparse.ArgumentParser(description=program_description, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("-u", "--base-url",     required=True, help="Hub server URL e.g. https://your.blackduck.url")
    parser.add_argument("-t", "--token-file",   required=True, help="File containing access token")
    parser.add_argument("-nv", "--no-verify",   action='store_false', help="Disable TLS certificate verification")
    parser.add_argument("-d", "--debug", action='store_true', help="Set debug output on")
    parser.add_argument("-pn", "--project-name", required=True, help="Project Name")
    parser.add_argument("-pv", "--project-version-name", required=True, help="Project Version Name")
    parser.add_argument("-kh", "--keep_hierarchy", action='store_true', help="Set to keep all entries in the sources report. Will not remove components found under others.")
    parser.add_argument("--report-retries", metavar="", type=int, default=RETRY_LIMIT, help="Retries for receiving the generated BlackDuck report. Generating copyright report tends to take longer minutes.")
    parser.add_argument("--timeout", metavar="", type=int, default=60, help="Timeout for REST-API. Some API may take longer than the default 60 seconds")
    parser.add_argument("--retries", metavar="", type=int, default=4, help="Retries for REST-API. Some API may need more retries than the default 4 times")
    return parser.parse_args()

def main():
    args = parse_command_args()
    with open(args.token_file, 'r') as tf:
        token = tf.readline().strip()
    try:
        log_config(args.debug)    
        hub_client = Client(token=token,
                            base_url=args.base_url,
                            verify=args.no_verify,
                            timeout=args.timeout,
                            retries=args.retries)
        
        project = find_project_by_name(hub_client, args.project_name)
        version = find_project_version_by_name(hub_client, project, args.project_version_name)
        location = create_version_details_report(hub_client, version)
        report_zip = download_report(hub_client, location, args.report_retries)
        logging.debug(f"Deleting report from Black Duck {hub_client.session.delete(location)}")
        zip=ZipFile(io.BytesIO(report_zip), "r")
        pprint(zip.namelist())
        report_data = {name: zip.read(name) for name in zip.namelist()}
        filename = [i for i in report_data.keys() if i.endswith(".json")][0]
        version_report = json.loads(report_data[filename])
        # TODO items
        # Process file section of report data to identify primary paths
        # Combine component data with selected file data
        # Output result with CSV anf JSON as options.


    except (Exception, BaseException) as err:
        logging.error(f"Exception by {str(err)}. See the stack trace")
        traceback.print_exc()

if __name__ == '__main__':
    sys.exit(main())