#!/usr/bin/env python

'''
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

List project versions that are used as subprojects (components)

usage: get_subprojects.py [-h] -u BASE_URL -t TOKEN_FILE [-nv] 

options:
  -h, --help            show this help message and exit
  -u BASE_URL, --base-url BASE_URL
                        Hub server URL e.g. https://your.blackduck.url
  -t TOKEN_FILE, --token-file TOKEN_FILE
                        containing access token
  -nv, --no-verify      disable TLS certificate verification

'''
import argparse
import json
import logging
import sys
import arrow

from blackduck import Client
from pprint import pprint

parser = argparse.ArgumentParser("Get all the users")
parser.add_argument("-u", "--base-url", required=True, help="Hub server URL e.g. https://your.blackduck.url")
parser.add_argument("-t", "--token-file", dest='token_file', required=True, help="containing access token")
parser.add_argument("-nv", "--no-verify", dest='verify', action='store_false', help="disable TLS certificate verification")
args = parser.parse_args()

logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stderr, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("blackduck").setLevel(logging.WARNING)

with open(args.token_file, 'r') as tf:
    access_token = tf.readline().strip()

bd = Client(
    base_url=args.base_url,
    token=access_token,
    verify=args.verify
)

headers = {}
projects = bd.get_resource('projects')

for project in projects:
    project_name = project['name']
    versions = bd.get_resource('versions',project)
    for version in versions:
        version_name = version['versionName']
        version_url = version['_meta']['href']
        references_url = version_url.replace("/projects/","/components/") + "/references"
        references = bd.session.get(references_url)
        json_data = references.json()
        reference_count = json_data['totalCount']
        print (f"{project_name:30} {version_name:30} is used in {reference_count:4} projects")
        if reference_count > 0:
            items = json_data['items']
            for item in items:
                referencing_version = bd.get_resource('href', item, items=False)
                referencing_project = bd.get_resource('project', referencing_version, items=False)
                print (f"           {project_name:30} {version_name:30} is used in {referencing_project['name']} {referencing_version['versionName']}")