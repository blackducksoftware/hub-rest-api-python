#!/usr/bin/env python3
'''
Created: Apr 2, 2024
Author: @kumykov

Copyright (c) 2024, Synopsys, Inc.
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

usage: sbomify.py [-h] -u BASE_URL -t TOKEN_FILE [-nv] -sp SOURCE_PROJECT -sv SOURCE_VERSION -tp TARGET_PROJECT -tv TARGET_VERSION
                  [-tg TARGET_PROJECT_GROUP] [-c] [--sbom-type SBOM_TYPE]

Generate and download SBOM for the source project version 
and upload it to the target project version

options:
  -h, --help            show this help message and exit
  -u BASE_URL, --base-url BASE_URL
                        Hub server URL e.g. https://your.blackduck.url
  -t TOKEN_FILE, --token-file TOKEN_FILE
                        File containing access token
  -nv, --no-verify      Disable TLS certificate verification
  -sp SOURCE_PROJECT, --source-project SOURCE_PROJECT
                        Source Project Name
  -sv SOURCE_VERSION, --source-version SOURCE_VERSION
                        Source Project Version Name
  -tp TARGET_PROJECT, --target-project TARGET_PROJECT
                        Target Project Name
  -tv TARGET_VERSION, --target-version TARGET_VERSION
                        Target Project Version Name
  -tg TARGET_PROJECT_GROUP, --target-project-group TARGET_PROJECT_GROUP
                        Project Group to use for target
  -c, --create-target   Create target project version if does not exist
  --sbom-type {SPDX_22,SPDX_23,CYCLONEDX_13,CYCLONEDX_14}
                        SBOM type to use for transaction
                        
Black Duck examples collection


'''
import argparse
import io
import json
import sys
import logging
import time

from zipfile import ZipFile
from blackduck import Client

logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stderr, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("blackduck").setLevel(logging.WARNING)


def find_project_by_name(bd, project_name):
    params = {
        'q': [f"name:{project_name}"]
    }
    projects = [p for p in bd.get_resource('projects', params=params) if p['name'].casefold() == project_name.casefold()]
    if len(projects) == 1:
        return projects[0]
    else:
        return None

def find_project_version_by_name(bd, project, version_name):
    params = {
        'q': [f"versionName:{version_name}"]
    }
    versions = [v for v in bd.get_resource('versions', project, params=params) if v['versionName'] == version_name]
    if len(versions) == 1:
        return versions[0]
    else:
        return None

def find_or_create_project_group(bd, group_name):
    url = '/api/project-groups'
    params = {
        'q': [f"name:{group_name}"]
    }
    groups = [p for p in bd.get_items(url, params=params) if p['name'] == group_name]
    if len(groups) == 0:
        headers = {
            'Accept': 'application/vnd.blackducksoftware.project-detail-5+json',
            'Content-Type': 'application/vnd.blackducksoftware.project-detail-5+json'
        }
        data = {
            'name': group_name
        }
        response = bd.session.post(url, headers=headers, json=data)
        return response.headers['Location'] 
    else:
        return groups[0]['_meta']['href']

def create_project_version(bd, project_name,version_name,project_group, nickname = None):
    version_data = {"distribution": "EXTERNAL", "phase": "DEVELOPMENT", "versionName": version_name}
    if nickname:
        version_data['nickname'] = nickname
    url = '/api/projects'
    project = find_project_by_name(bd, project_name)
    if project:
        data = version_data
        url = project['_meta']['href'] + '/versions'
    else:
        data = {"name": project_name,
                "projectGroup": find_or_create_project_group(bd, project_group),
                "versionRequest": version_data}
    return bd.session.post(url, json=data)
    
def locate_project_version(bd, project_name, version_name, group="Black Duck Project Groups", create=False):
    project = find_project_by_name(bd, project_name)
    version = None
    if project:
        version = find_project_version_by_name(bd, project, version_name)
        if version:
            pass
        elif create:
            version = create_project_version(bd, project_name, version_name, group)
        else:
            pass
    elif create:
        response = create_project_version(bd, project_name, version_name, group)
        logging.info(f"Project {project_name} : {version_name} creation completed with {response}")
        if response.ok:
            project = find_project_by_name(bd, project_name)
            version = find_project_version_by_name(bd, project, version_name)
    return version

def create_sbom_report(bd, version, type, include_subprojects):
    post_data = {
            'reportFormat': "JSON",
            'sbomType': type,
            'includeSubprojects': include_subprojects	
    }
    sbom_reports_url = version['_meta']['href'] + "/sbom-reports"

    bd.session.headers["Content-Type"] = "application/vnd.blackducksoftware.report-4+json"
    r = bd.session.post(sbom_reports_url, json=post_data)
    if (r.status_code == 403):
        logging.debug("Authorization Error - Please ensure the token you are using has write permissions!")
    r.raise_for_status()
    location = r.headers.get('Location')
    assert location, "Hmm, this does not make sense. If we successfully created a report then there needs to be a location where we can get it from"
    return location

def download_report(bd, location, retries):
    report_id = location.split("/")[-1]
    if retries:
        logging.debug(f"Retrieving generated report from {location}")
        response = bd.session.get(location)
        report_status = response.json().get('status', 'Not Ready')
        if response.status_code == 200 and report_status == 'COMPLETED':
            response = bd.session.get(location + "/download.zip", headers={'Content-Type': 'application/zip', 'Accept':'application/zip'})
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

def produce_online_sbom_report(bd, project_name, project_version_name, sbom_type):
    project = find_project_by_name(bd, project_name)
    logging.debug(f"Project {project['name']} located")
    version = find_project_version_by_name(bd, project, project_version_name)
    logging.debug(f"Version {version['versionName']} located")
    location = create_sbom_report(bd, version, sbom_type, True)
    logging.debug(f"Created SBOM report of type {sbom_type} for project {project_name}, version {project_version_name} at location {location}")
    sbom_data_zip = download_report(bd, location, 60)
    logging.debug(f"Deleting report from Black Duck {bd.session.delete(location)}")
    zip=ZipFile(io.BytesIO(sbom_data_zip), "r")
    sbom_data = {name: zip.read(name) for name in zip.namelist()}
    filename = [i for i in sbom_data.keys() if i.endswith(".json")][0]
    return json.loads(sbom_data[filename])

def upload_sbom_file(bd, project_name, version_name, sbom_data):
    if sbom_data.get('bomFormat', None) == "CycloneDX":
        mime_type = 'application/vnd.cyclonedx'
    elif sbom_data.get('spdxVersion', None):
        mime_type = 'application/spdx'
    else:
        mime_type = None
    if not mime_type:
        logging.error(f"Could not identify file content for SBOM")
        sys.exit(1)
    logging.info(f"Mime type {mime_type} will be used for SBOM upload")
    files = {"file": ('sbom.json', json.dumps(sbom_data).encode('utf-8'), mime_type)}
    fields = {"projectName": project_name, "versionName": version_name}
    response = bd.session.post("/api/scan/data", files = files, data=fields)
    logging.info(f"SBOM Upload completed with {response}")
    if response.status_code == 409:
        logging.info(f"File  SBOM is already mapped to a different project version")
        
def sbomify(bd, args):
    source = locate_project_version(bd, args.source_project, args.source_version)
    if not source:
        logging.error(f"Source project {args.source_project} : {args.source_version} not found. Exiting.")
        sys.exit(1)
    logging.info(f"Located source project {args.source_project} : {args.source_version}")
    sbom = produce_online_sbom_report(bd, args.source_project, args.source_version, args.sbom_type)
    bd.session.headers.pop('Content-Type')    
    target = locate_project_version(bd, args.target_project, args.target_version, group=args.target_project_group, create=args.create_target)
    if not target:
        logging.error(f"Target project {args.target_project} : {args.target_version} not found. Exiting.")
        sys.exit(1)
    logging.info(f"Located target project {args.target_project} : {args.target_version}")
    upload_sbom_file(bd, args.target_project, args.target_version, sbom)

def parse_command_args():
    parser = argparse.ArgumentParser(prog = "sbomify.py", description="Generate and download SBOM and upload to the target project version", epilog="Blackduck examples collection")
    parser.add_argument("-u", "--base-url", required=True, help="Hub server URL e.g. https://your.blackduck.url")
    parser.add_argument("-t", "--token-file", required=True, help="File containing access token")
    parser.add_argument("-nv", "--no-verify", action='store_false', help="Disable TLS certificate verification")
    parser.add_argument("-sp", "--source-project", required=True, help="Source Project Name")
    parser.add_argument("-sv", "--source-version", required=True, help="Source Project Version Name")
    parser.add_argument("-tp", "--target-project", required=True, help="Target Project Name")
    parser.add_argument("-tv", "--target-version", required=True, help="Target Project Version Name")
    parser.add_argument("-tg", "--target-project-group", required=False, default='Black Duck Project Groups', help="Project Group to use for target")
    parser.add_argument("-c", "--create-target", action='store_true', help="Create target project version if does not exist")
    parser.add_argument("--sbom-type", required=False, default='SPDX_23', choices=["SPDX_22", "SPDX_23", "CYCLONEDX_13", "CYCLONEDX_14"], help="SBOM type to use for transaction")
    
    return parser.parse_args()

def main():
    args = parse_command_args()
    with open(args.token_file, 'r') as tf:
       access_token = tf.readline().strip()
    bd = Client(base_url=args.base_url, token=access_token, verify=args.no_verify, timeout=60.0, retries=4)
    sbomify(bd, args)

if __name__ == "__main__":
        sys.exit(main())
