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

The script will enumerate BOM entried that appear on NOTICES report 
without copyright and for each of then will try to retrieve 
upstream copyright notices from source origin (github, long_tail)

if that fails, the script will process earlier versions of componets
anf try to fetch copyright statements from there.

Note:  There is still a possibility that there will be no copyright 
       statements present on any version of a component

Usage: Enumerate BOM componets without copyrigth statements. retrieve 
       copyright statements form upstream channel and/or version

python3 get_upstream_copyrights.py [OPTIONS]

OPTIONS:
    -h                              Show help
    -u BASE_URL                     URL of a Blackduck system
    -t TOKEN_FILE                   Authentication token file
    -p PROJECT_NAME                 Project to process
    -v VERSION_NAME                 Project Version to process
    -nv                             Trust TLS certificate

'''

import argparse
import json
import logging
import sys
import arrow

from itertools import islice
from datetime  import timedelta
from blackduck import Client

logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stderr, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("blackduck").setLevel(logging.DEBUG)

#----------------------------------------------------------------------------

def main():

    args = parse_command_args()
    components_with_no_copyrights = []

    with open(args.token_file, 'r') as tf:
        access_token = tf.readline().strip()

    global bd
    bd = Client(base_url=args.base_url, token=access_token, verify=args.no_verify, timeout=60.0, retries=4)
    project_name, project_version = get_project_version_by_name(args.project_name, args.version_name)

    for component in bd.get_resource("components", project_version):
        try:
            copyrights = find_copyrights_in_bom_component_origins(component)           \
                      or find_copyrights_in_github_origins(component)                  \
                      or find_copyrights_in_previous_component_versions(component)

            if copyrights:
                print_copyrights(component, copyrights)
            else:
                components_with_no_copyrights.append(component)

        except Exception as e:
            logging.debug(f"Component {component['componentName']} failed with {e}")

    if args.report_missing:
        report_components_with_no_copyrights(components_with_no_copyrights)

#----------------------------------------------------------------------------

def parse_command_args():

    parser = argparse.ArgumentParser("Print copyrights for BOM using upstream origin or prior version if not available.")
    parser.add_argument("-u", "--base-url",     required=True, help="Hub server URL e.g. https://your.blackduck.url")
    parser.add_argument("-t", "--token-file",   required=True, help="File containing access token")
    parser.add_argument("-p", "--project-name", required=True, help="Project Name")
    parser.add_argument("-v", "--version-name", required=True, help="Version Name")
    parser.add_argument("-r", "--report-missing", action='store_true',  help="Report components with no copyrights")
    parser.add_argument("-nv", "--no-verify",     action='store_false', help="Disable TLS certificate verification")

    return parser.parse_args()

#----------------------------------------------------------------------------

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

#----------------------------------------------------------------------------

def find_copyrights_in_bom_component_origins(component):

    copyrights = []
    for origin in component['origins']:
        copyrights += list(bd.get_resource('component-origin-copyrights', origin))

    return copyrights

#----------------------------------------------------------------------------

def find_copyrights_in_github_origins(component):

    if not component.get('origins'):
        return []

    def origin_is_lambda_or_long_tail(origin):
        origin_name = origin.get('originName')
        return origin_name == 'github' or origin_name == 'long_tail'

    all_origins = list(bd.get_resource('origins', component))
    github_origins = filter(origin_is_lambda_or_long_tail, all_origins)

    copyrights = []
    for origin in github_origins:
        copyrights += list(bd.get_resource('component-origin-copyrights',origin))

    return copyrights

#----------------------------------------------------------------------------

def find_copyrights_in_previous_component_versions(component):
    
    params = {'sort' : 'releasedOn DESC'}
    component_json = bd.get_json(component['component'])
    all_component_versions_sorted_by_release_date = bd.get_resource('versions', component_json, params=params)

    copyrights = []
    release_date = component.get('releasedOn')

    component_count = 0
    for component_version in all_component_versions_sorted_by_release_date:

            # Skip component versions that are newer than the one we are trying to find copyrights for.
            # This code doesn't currently work because the release_date for a BOM component version
            # is the date of the scan that detected the component. This is probably a bug in the API.
            # diff = arrow.get(release_date) - arrow.get(component_version['releasedOn'])
            # if diff < timedelta(0): continue

            component_count += 1
            if component_count > 10:
                break

            origin_count = 0
            for origin in bd.get_resource('origins', component_version):

                origin_count += 1
                if copyrights or origin_count > 10:
                    break

                copyrights = list(bd.get_resource('component-origin-copyrights', origin))

    return copyrights

#----------------------------------------------------------------------------

def print_copyrights(component, copyrights):

    print(f"\n{component.get('componentName')} {component.get('componentVersionName')}")
    already_printed_copyrights = {}

    for copyright in copyrights:

        # Everything after the first newline is usually junk. So we print only the
        # first line of any copyright statement. Also, we skip any copyright statement
        # that is an exact duplicate or differs only by whitespace or lettercase from
        # one that we've already printed.

        first_line_of_copyright_statement = copyright['updatedCopyright'].splitlines()[0]
        copyright_without_whitespace = "".join(first_line_of_copyright_statement.split()).lower()

        if copyright_without_whitespace in already_printed_copyrights:
            continue

        already_printed_copyrights[copyright_without_whitespace] = None
        print(f"     {first_line_of_copyright_statement}")

#----------------------------------------------------------------------------

def report_components_with_no_copyrights(components):

    print("=" * 80)
    print("No copyrights found for these components")
    for component in components:
        print(f"{component.get('componentName')} {component.get('componentVersionName')}")

    print(f"Total: {len(components)}")

#----------------------------------------------------------------------------

if __name__ == "__main__":
    sys.exit(main())
