#!/usr/bin/env python3
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

Extract application ID if present

usage: python3 get_application_id.py [-h] -u BASE_URL -t TOKEN_FILE [-nv] project_name

positional arguments:
  project_name

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

parser = argparse.ArgumentParser("python3 get_application_id.py")
parser.add_argument("project_name")
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
params = { 'q': [f"name:{args.project_name}"] }
projects = [p for p in bd.get_resource('projects', params=params) if p['name'] == args.project_name]

if not len(projects):
    print (f'No project found for {args.project_name}')

for project in projects:
    project_name = project['name']
    project_mappings = bd.get_resource('project-mappings', project)
    application_id = None
    for mapping in project_mappings:
        application_id = mapping.get('applicationId',None)
    print (f"Project: {project['name']:50} Application ID: {application_id}")
    