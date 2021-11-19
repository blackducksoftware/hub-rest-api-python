#!/usr/bin/env python

'''
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
 
'''
import argparse
import json
import logging
import sys

from requests.exceptions import ReadTimeout

from blackduck import Client

parser = argparse.ArgumentParser("Refresh the copyright data for (BOM) components using the old copyright data with the newer copyright 2.0 data")
parser.add_argument("--base-url", required=True, help="Hub server URL e.g. https://your.blackduck.url")
parser.add_argument("--token-file", dest='token_file', required=True, help="containing access token")
parser.add_argument("--no-verify", dest='verify', action='store_false', help="disable TLS certificate verification")
parser.add_argument("-t", "--timeout", default=15, type=int, help="Adjust the (HTTP) session timeout value (default: 15s)")
parser.add_argument("-r", "--retries", default=3, type=int, help="Adjust the number of retries on failure (default: 3)")
parser.add_argument("project_name", help="The BD project containing the components to refresh")
parser.add_argument("version_name", help="The BD version containing the components to refresh")
args = parser.parse_args()


logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stderr, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("blackduck").setLevel(logging.DEBUG)

with open(args.token_file, 'r') as tf:
    access_token = tf.readline().strip()

bd = Client(
    base_url=args.base_url,
    token=access_token,
    verify=args.verify,
    timeout=args.timeout,
    retries=args.retries,
)

params = {
    'q': [f"name:{args.project_name}"]
}
projects = [p for p in bd.get_resource('projects', params=params) if p['name'] == args.project_name]
assert len(projects) == 1, f"There should be one, and only one project named {args.project_name}. We found {len(projects)}"
project = projects[0]

params = {
    'q': [f"versionName:{args.version_name}"]
}
versions = [v for v in bd.get_resource('versions', project, params=params) if v['versionName'] == args.version_name]
assert len(versions) == 1, f"There should be one, and only one version named {args.version_name}. We found {len(versions)}"
version = versions[0]

logging.debug(f"Found {project['name']}:{version['versionName']}")

def component_name_str(bom_component):
    bom_component_name = bom_component['componentName']
    if 'componentVersionName' in bom_component:
        return f"{bom_component_name}:{bom_component['componentVersionName']}"
    else:
        return bom_component_name

# Ref: https://your.blackduck.url/api-doc/public.html#_refreshing_copyrights
headers = {
    'Accept':'application/vnd.blackducksoftware.copyright-4+json',
    'Content-Type': 'application/vnd.blackducksoftware.copyright-4+json'
}

try:
    for bom_component in bd.get_resource('components', version):
        origins = bom_component['origins']
        if origins:
            for origin in origins:
                origin_name = origin['externalNamespace']
                copyright_refresh_url = f"{origin['origin']}/copyrights-refresh"
                logging.debug(f"Refreshing copyright data for component {component_name_str(bom_component)} from origin {origin_name} using URL {copyright_refresh_url}")
                r = bd.session.put(copyright_refresh_url, headers=headers)
                r.raise_for_status()
                logging.info(f"Succeeded in refreshing copyright data for component {component_name_str(bom_component)} from origin {origin_name}")
        else:
            logging.debug(f"Skipping component {component_name_str(bom_component)} cause there was no 'origin' selected for it.")
except ReadTimeout:
    logging.exception(f"A read timeout occurred using timeout value {args.timeout}, retries {args.retries}. This can happen when there is a BOM component having LOTS of copyright data, e.g. Linux kernel. Try increasing the timeout value or number of retries")




