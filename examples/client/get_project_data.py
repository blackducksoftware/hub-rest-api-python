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

usage: get_project_data.py [-h] -u BASE_URL -t TOKEN_FILE [-nv] -p SOURCE_PROJECT -v SOURCE_VERSION

options:
  -h, --help            show this help message and exit
  -u BASE_URL, --base-url BASE_URL
                        Hub server URL e.g. https://your.blackduck.url
  -t TOKEN_FILE, --token-file TOKEN_FILE
                        File containing access token
  -nv, --no-verify      Disable TLS certificate verification
  -p SOURCE_PROJECT, --project SOURCE_PROJECT
                        Project Name
  -v SOURCE_VERSION, --version SOURCE_VERSION
                        Project Version Name

Black Duck examples collection


'''
import argparse
import io
import json
import sys
import logging
import time

from blackduck import Client
from pprint import pprint

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

def get_project_data(bd, args):
    project  = find_project_by_name(bd, args.project)
    version = find_project_version_by_name(bd, project, args.version)
    if not version:
        logging.error(f"Source project {args.project} : {args.version} not found. Exiting.")
        sys.exit(1)
    logging.info(f"Located source project {args.project} : {args.version}")
    return bd.get_resource('components', version)


def parse_command_args():
    parser = argparse.ArgumentParser(prog = "get_project_data.py", description="Generate and download SBOM and upload to the target project version", epilog="Blackduck examples collection")
    parser.add_argument("-u", "--base-url", required=True, help="Hub server URL e.g. https://your.blackduck.url")
    parser.add_argument("-t", "--token-file", required=True, help="File containing access token")
    parser.add_argument("-nv", "--no-verify", action='store_false', help="Disable TLS certificate verification")
    parser.add_argument("-p", "--project", required=True, help="Project Name")
    parser.add_argument("-v", "--version", required=True, help="Project Version Name")
    
    return parser.parse_args()

def main():
    args = parse_command_args()
    with open(args.token_file, 'r') as tf:
       access_token = tf.readline().strip()
    bd = Client(base_url=args.base_url, token=access_token, verify=args.no_verify, timeout=60.0, retries=4)
    components = get_project_data(bd, args)
    for component in components:
        # pprint (component)
        print (f"{component['componentName']} {component['componentVersionName']} {component['licenses'][0]['licenseDisplay']}")

if __name__ == "__main__":
        sys.exit(main())
