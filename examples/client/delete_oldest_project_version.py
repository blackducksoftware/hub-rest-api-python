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

usage: Get all the users [-h] -u BASE_URL -t TOKEN_FILE [-nv] -pn PROJECT_NAME [-mv MAX_VERSIONS] [--dry-run]

options:
  -h, --help            show this help message and exit
  -u BASE_URL, --base-url BASE_URL
                        Hub server URL e.g. https://your.blackduck.url
  -t TOKEN_FILE, --token-file TOKEN_FILE
                        containing access token
  -nv, --no-verify      disable TLS certificate verification
  -pn PROJECT_NAME, --project-name PROJECT_NAME
                        Project name to be processed
  -mv MAX_VERSIONS, --max-versions MAX_VERSIONS
                        Max versions to allow
  --dry-run             Dry run, do not delete

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
parser.add_argument("-pn", "--project-name", dest='project_name', required=True, help='Project name to be processed')
parser.add_argument("-mv", "--max-versions", default=10, type=int, dest="max_versions", help="Max versions to allow")
parser.add_argument("--dry-run", dest='dry_run', action='store_true', help="Dry run, do not delete")
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

# Locate project of interest

params = {
    'q': [f"name:{args.project_name}"]
}
projects = bd.get_resource('projects', params=params, items=False)
num_projects = len(projects['items'])
if not num_projects == 1:
    logging.info (f"Project name {args.project_name} is not specific enough to identify a single project")
    sys.exit(1)

# Analyze versions

versions = bd.get_resource('versions', projects['items'][0], items=False)
num_versions = len(versions['items'])
if (num_versions < args.max_versions):
    logging.info(f"Number of versions {num_versions} is less than maximum {args.max_versions}, No deletion necessary")
    sys.exit()
else:
    num_versions_to_delete = num_versions - args.max_versions + 1
    logging.info(f"Found {num_versions} which is greater or equal to maximum allowed: {args.max_versions}")
    logging.info(f"Have to delete {num_versions_to_delete} project version(s)")
    sorted_version_list = sorted(versions['items'], key=lambda s: arrow.get(s['createdAt']))
    logging.info("List of versions in chronological order")
    for version in sorted_version_list:
        logging.info (f"Version {version['versionName']}  created at  {version['createdAt']}")
    versions_to_delete = sorted_version_list[-num_versions_to_delete:]
    logging.info("List of versions to delete")
    for version in versions_to_delete:
        logging.info (f"Version {version['versionName']}  created at  {version['createdAt']}")
        version_url = version['_meta']['href']
        logging.info(f"Version URL {version_url}")
        if not args.dry_run:
            # Deleting older versions
            logging.info(f"Deleting {version['versionName']}  created at  {version['createdAt']}")
            result = bd.session.delete(version_url)
            logging.info(f"Delete request completed with {result}")