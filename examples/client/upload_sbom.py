#!/usr/bin/env python

'''
Created on Friday, January 13th, 2023
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

usage: upload_sbom [-h] [-pg PROJECT_GROUP] -u BASE_URL -t TOKEN_FILE [-nv] filename project version

Uploads SBOM file to a Blackduck server

positional arguments:
  filename              SBOM file to upload
  project               Project to associate SBOM with
  version               Project Version to associate SBOM with

options:
  -h, --help            show this help message and exit
  -pg PROJECT_GROUP, --project_group PROJECT_GROUP
                        Project Group to be used
  -u BASE_URL, --base-url BASE_URL
                        Hub server URL e.g. https://your.blackduck.url
  -t TOKEN_FILE, --token-file TOKEN_FILE
                        File containing access token
  -nv, --no-verify      Disable TLS certificate verification

Blackduck examples collection

'''


import sys
import argparse
import logging

from blackduck import Client

logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stderr, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("blackduck").setLevel(logging.WARNING)

def find_project_by_name(project_name):
    params = {
        'q': [f"name:{project_name}"]
    }
    projects = [p for p in bd.get_resource('projects', params=params) if p['name'] == project_name]
    if len(projects) == 1:
        return projects[0]
    else:
        return None

def find_project_version_by_name(project, version_name):
    params = {
        'q': [f"versionName:{version_name}"]
    }
    versions = [v for v in bd.get_resource('versions', project, params=params) if v['versionName'] == version_name]
    if len(versions) == 1:
        return versions[0]
    else:
        return None

def find_or_create_project_group(group_name):
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

def create_project_version(project_name,version_name,project_group, nickname = None):
    version_data = {"distribution": "EXTERNAL", "phase": "DEVELOPMENT", "versionName": version_name}
    if nickname:
        version_data['nickname'] = nickname
    url = '/api/projects'
    project = find_project_by_name(project_name)
    if project:
        data = version_data
        url = project['_meta']['href'] + '/versions'
    else:
        data = {"name": project_name,
                "projectGroup": find_or_create_project_group(project_group),
                "versionRequest": version_data}
    return bd.session.post(url, json=data)
    
def find_or_create_project_version(project_name, version_name, project_group):
    project = find_project_by_name(project_name)
    if project:
        version = find_project_version_by_name(project, version_name)
        if version:
            pass
        else:
            version = create_project_version(project_name, version_name)
    else:
        version = create_project_version(project_name, version_name, project_group)
    project = find_project_by_name(project_name)
    version = find_project_version_by_name(project, version_name)
    if not version:
        logging.info(f"Project {project_name} with Version {version_name} could not be located or created.")
        sys.exit(1)

def get_sbom_mime_type(filename):
    import json
    with open(filename, 'r') as f:
        data = json.load(f)
    if data.get('bomFormat', None) == "CycloneDX":
        return 'application/vnd.cyclonedx'
    elif data.get('spdxVersion', None):
        return 'application/spdx'
    return None

def upload_sbom_file(filename, project, version, project_group):
    find_or_create_project_version(project, version, project_group)
    mime_type = get_sbom_mime_type(filename)
    if not mime_type:
        logging.error(f"Could not identify file content for {filename}")
        sys.exit(1)
    logging.info(f"Mime type {mime_type} will be used for file {filename}")
    files = {"file": (filename, open(filename,"rb"), mime_type)}
    fields = {"projectName": project, "versionName": version}
    response = bd.session.post("/api/scan/data", files = files, data=fields)
    logging.info(response)
    if response.status_code == 409:
        logging.info(f"File {filename} is already mapped to a different project version")

def main():
    args = parse_command_args()
    with open(args.token_file, 'r') as tf:
       access_token = tf.readline().strip()
    global bd
    bd = Client(base_url=args.base_url, token=access_token, verify=args.no_verify, timeout=60.0, retries=4)
    upload_sbom_file(args.filename, args.project, args.version, args.project_group)

def parse_command_args():
    parser = argparse.ArgumentParser(prog = "upload_sbom", description="Uploads SBOM file to a Blackduck server", epilog="Blackduck examples collection")
    parser.add_argument("filename", help="SBOM file to upload")
    parser.add_argument("project", help="Project to associate SBOM with")
    parser.add_argument("version", help="Project Version to associate SBOM with")
    parser.add_argument("-pg", "--project_group", required=False, default='SBOM-Import', help="Project Group to be used")
    parser.add_argument("-u", "--base-url",     required=True, help="Hub server URL e.g. https://your.blackduck.url")
    parser.add_argument("-t", "--token-file",   required=True, help="File containing access token")
    parser.add_argument("-nv", "--no-verify",     action='store_false', help="Disable TLS certificate verification")
    return parser.parse_args()



if __name__ == "__main__":
        sys.exit(main())
