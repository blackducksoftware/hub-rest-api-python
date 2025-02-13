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

List projects and project owners

usage: list_projects.py [-h] -u BASE_URL -t TOKEN_FILE [-nv] 

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
import csv

from blackduck import Client
from pprint import pprint

parser = argparse.ArgumentParser("List projects and project owners")
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

def get_user_name(url):
    if url:
        data = bd.get_json(url)
        return (data['userName'])
    else:
        return None

fieldnames = ['Project Name',
              'Project Owner',
              'Project Created By',
              'Project Updated By']

file_name = 'projects_by_owners.csv'

with open(file_name, 'w') as output:
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    for project in projects:
        project_name = project['name']
        project_owner = project.get('projectOwner', None)
        project_owner_name = get_user_name(project_owner)
        project_created_by = project.get('createdByUser', None)
        project_created_by_name = get_user_name(project_created_by)
        project_updated_by = project.get('updatedByUser', None)
        project_updated_by_name = get_user_name(project_updated_by)
        project_users = bd.get_resource('users', project)
        row = dict()
        row['Project Name'] = project_name
        row['Project Owner'] = project_owner_name
        row['Project Created By'] = project_created_by_name
        row['Project Updated By'] = project_updated_by_name
        writer.writerow(row)
    
    logging.info(f"Output file {file_name} written")