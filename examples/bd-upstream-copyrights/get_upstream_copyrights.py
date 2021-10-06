#!/usr/bin/env python

'''

Created on October 5, 2021
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

This program will attempt to produce missing Copyright statements 
for BOM entries that do not have orgin associated copyright statements.

The scriot will enumerate BOM entried that appear on NOTICES report 
without copyright and for each of then will try to retrieve 
upstream copyright notices from source origin (github, long_tail)

if that fails, the script will process earlier versions of componets
anf try to fetch copyright statements from there.

Note:  There is still a possibility that there will be no copyright 
       statements present on any version of a component

Once completed a text file will be writtent with the following format:
Optional JSON file can be written

#####
ComponentName ComponentversionName
#####
-----
Statement-1
-----
Statement-1
-----
.....

Usage: Enumerate BOM componets without copyrigth statements. retrieve 
       copyright statements form upstream channel and/or version

python3 get_upstream_copyrights.py [OPTIONS]

OPTIONS:
    [-h]                            Help
    -u BASE_URL                     URL of a Blackduck system
    -t TOKEN_FILE                   Authentication token file
    -p PROJECT_NAME                 Project to process
    -v VERSION_NAME                 Project Version to process
    [-o OUTPUT_FILE]                Output file (default: copyright_data.txt)
    [-jo JSON_OUTPUT_FILE]          Write an optional JSON file with output data
    [-ukc USE_UPDATED_COPYRIGHT]    Use kbCopyright instead of updatedCopyright (default: false)
    [-nv]                           Trust TLS certificate




'''

import argparse
import json
import logging
import sys
from datetime import timedelta
from pprint import pprint

import arrow
from blackduck import Client
from blackduck.Utils import get_resource_name

logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stderr, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("blackduck").setLevel(logging.DEBUG)

def get_project_version_by_name(project_name, version_name):
    params = {
        'q': [f"name:{project_name}"]
    }
    projects = [p for p in bd.get_resource('projects', params=params) if p['name'] == project_name]
    assert len(projects) == 1, f"There should be one, and only one project named {project_name}. We found {len(projects)}"
    project = projects[0]

    params = {
        'q': [f"versionName:{version_name}"]
    }
    versions = [v for v in bd.get_resource('versions', project, params=params) if v['versionName'] == version_name]
    assert len(versions) == 1, f"There should be one, and only one version named {version_name}. We found {len(versions)}"
    version = versions[0]
    return project, version

def find_copyright_for_component(component):
    # Search for copyrights associated with github origin. 
    # If present, search stops here
    if component.get('origins',None):
        copyright_records = find_github_copyrights(component)    
        if len(copyright_records) > 0:
            return copyright_records
    
    # Continue searching in previous versions of a component
    # in reverse chronological order.
    # Skip versions that are newer that one in the BOM
    copyright_records = find_copyrights_in_previous_versions(component)
    return copyright_records

def find_copyrights_in_previous_versions(component):
    release_date = component.get('releasedOn', None)
    component_versions = [version for version in bd.get_resource('versions', bd.get_json(component['component']))]
    copyright_records = []
    for version in sorted(component_versions, key= lambda version: version['releasedOn'], reverse = True) :
        version_release_date = version['releasedOn']
        diff = arrow.get(release_date) - arrow.get(version_release_date)
        if diff < timedelta(0):
            logging.debug(f"Version {version['versionName']} is newer, skipping ...")
            continue
        for origin in bd.get_resource('origins', version):
            origin_copyrights = bd.get_resource('component-origin-copyrights', origin)
            copyright_records += [copyright for copyright in origin_copyrights]
        logging.debug(f"Found {len(copyright_records)} for {component['componentName']} {version['versionName']}")
        if len(copyright_records) > 0:
            break
    return copyright_records

def find_github_copyrights(component):
    origins = bd.get_resource('origins', component)
    github_origins = list(filter(
        lambda origin: origin.get('originName','unknown') == 'github' or origin.get('originName','unknown') == 'long_tail', origins))
    github_copyrights = list()
    for origin in github_origins:
        github_copyrights += [copyright for copyright in bd.get_resource('component-origin-copyrights',origin) if copyright['active']]
    return github_copyrights

def write_text_output(output_data, output_file, usekb_copyright=False):
    f = open(output_file, "w")
    hashes = "#"*80
    dashes = "-"*80
    for entry in output_data:
        f.write(f"{hashes}\n")
        f.write(f"{entry['component']['componentName']} {entry['component'].get('componentVersionName', None)}")
        f.write(f"\n{hashes}\n{dashes}\n")
        for copyright in entry['copyrights']:
            if usekb_copyright:
                f.write(copyright['kbCopyright'])
            else:
                f.write(copyright['updatedCopyright'])
            f.write(f"\n{dashes}\n")
        f.write("\n\n")
    f.write("\n")
    f.close()

def main():
    upstream_copyright_data_file='copyright_data.txt'

    parser = argparse.ArgumentParser("Enumerate BOM componets without copyrigth statements. retrieve copyright statements form upstream channel and/or version")
    parser.add_argument("-u", "--base-url", required=True, help="Hub server URL e.g. https://your.blackduck.url")
    parser.add_argument("-t", "--token-file", dest='token_file', required=True, help="containing access token")
    parser.add_argument("-p", "--project-name", dest='project_name', required=True, help="Project Name")
    parser.add_argument("-v", "--version-name", dest='version_name', required=True, help="Version Name")
    parser.add_argument("-o", "--output-file", dest='output_file', default=upstream_copyright_data_file, help=f"TEXT-formatted file with data")
    parser.add_argument("-jo", "--json-output-file", dest='json_output_file', default=None, help='JSON formatted file with data')
    parser.add_argument("-ukc", "--use-kb-copyright", dest='use_kb_copyright', default=False, help='Use KB Copyright vs Updated Copyright')
    parser.add_argument("-nv", "--no-verify", dest='verify', action='store_false', help="disable TLS certificate verification")
    args = parser.parse_args()

    with open(args.token_file, 'r') as tf:
        access_token = tf.readline().strip()

    global bd
    bd = Client(base_url=args.base_url, token=access_token, verify=args.verify, timeout = 60.0)

    project, version = get_project_version_by_name(args.project_name, args.version_name)
    logging.debug(f"Found {project['name']}:{version['versionName']}")

    # retrieve bill of materials and locate entries without copyrights
    bom_components_with_no_copyrights = []
    for component in bd.get_resource("components", version):
        logging.debug(f"Processing component {component['componentName']}")
        #if component['componentName'] != 'musl':
        #    continue
        origins = component['origins']
        if len(origins) == 0:
            bom_components_with_no_copyrights.append(component)
            continue
        copyrights_count = 0
        for origin in origins:
            logging.debug(f"Processing origin {origin['externalNamespace']}  {origin['externalId']}")
            origin_copyrights = [copyright for copyright in bd.get_resource('component-origin-copyrights', origin)]
            copyrights_count += len(origin_copyrights)
            if copyrights_count > 0:
                break
        logging.debug(f"Copyright count = {copyrights_count}")
        if copyrights_count == 0:
            bom_components_with_no_copyrights.append(component)

    logging.debug(f"Found {len(bom_components_with_no_copyrights)} components with no copyright")
    output_data = list()
    for component in bom_components_with_no_copyrights:
        logging.debug(f"Locating copyrights for component {component['componentName']} {component.get('componentVersionName', None)}")
        copyrights = find_copyright_for_component(component)
        logging.debug(f"Found {len(copyrights)} active records")
        output_data.append ({'component': component, 'copyrights': copyrights })

    logging.debug(f"Writing results into {args.output_file} file")
    write_text_output(output_data, args.output_file, args.use_kb_copyright)
    if args.json_output_file:
        logging.debug(f"Writing results into {args.json_output_file} file")
        with open(args.json_output_file, 'w') as f:
            json.dump(output_data, f, indent=2)
        
if __name__ == "__main__":
    sys.exit(main())
