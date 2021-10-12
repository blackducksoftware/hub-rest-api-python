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
import csv

from blackduck import Client

import argparse

import logging
import json

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] {%(module)s:%(lineno)d} %(levelname)s - %(message)s"
)

parser = argparse.ArgumentParser("Get the BOM components for a given project-version and the license details for each BOM component")
parser.add_argument("--base-url", required=True, help="Hub server URL e.g. https://your.blackduck.url")
parser.add_argument("--token-file", dest='token_file', required=True, help="containing access token")
parser.add_argument("--project", dest='project_name', required=True, help="Project that contains the BOM components")
parser.add_argument("--version", dest='version_name', required=True, help="Version that contains the BOM components")
parser.add_argument("--no-verify", dest='verify', action='store_false', help="disable TLS certificate verification")
args = parser.parse_args()

with open(args.token_file, 'r') as tf:
    access_token = tf.readline().strip()

bd = Client(base_url=args.base_url, token=access_token, verify=args.verify)

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

all_bom_components_lic_info = dict()

for bom_component in bd.get_resource('components', version):
    if 'componentVersionName' in bom_component:
        bom_component_name = f"{bom_component['componentName']}:{bom_component['componentVersionName']}"
    else:
        # version unknown, so we default to the component name
        bom_component_name = f"{bom_component['componentName']}"

    license_info = bom_component.get('licenses', [])
    for license in license_info:
        license_details = list()
        if 'license' in license:
            license_details.append(bd.session.get(license['license']).json())
        elif 'licenses' in license:
            for lic in license['licenses']:
                if 'license' in lic:
                    license_details.append(bd.session.get(lic['license']).json())
                else:
                    logging.warning(f"License {license.get('licenseDisplay', 'Unknown')} had no 'license' key (aka link)")
        else:
            logging.warning(f"License {license.get('licenseDisplay', 'Unknown')} had no 'license' key (aka link)")
        license['license_details'] = license_details

    all_bom_components_lic_info.update({bom_component_name: license_info})

print(json.dumps(all_bom_components_lic_info))