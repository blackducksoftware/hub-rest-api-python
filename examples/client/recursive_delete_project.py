'''
Created: Nov 23, 2023
Author: mkumykov

Copyright (c) 2023 - Synopsys, Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

This script will remove project hierarchies from a Black Duck server.

usage: python3 recursive_delete_project.py [-h] -u BASE_URL -t TOKEN_FILE [-nv] [-p PROJECT_NAME] [-pv VERSION_NAME] [-pl PROJECT_LIST_FILE]

options:
  -h, --help            show this help message and exit
  -u BASE_URL, --base-url BASE_URL
                        Hub server URL e.g. https://your.blackduck.url
  -t TOKEN_FILE, --token-file TOKEN_FILE
                        File containing access token
  -nv, --no-verify      Disable TLS certificate verification
  -p PROJECT_NAME, --project-name PROJECT_NAME
                        Project Name
  -pv VERSION_NAME, --version-name VERSION_NAME
                        Version Name
  -pl PROJECT_LIST_FILE, --project-list-file PROJECT_LIST_FILE
                        File containing project name list

Options -pl and -p  can not be used at the same time

Examples:

remove project with all sub-projects

    python3 recursive_delete_project.py -u BASE_URL -t TOKEN_FILE -nv -p PROJECT_NAME

remove project version with all sub-projects, keep sub-projects still in use intact    

    python3 recursive_delete_project.py -u BASE_URL -t TOKEN_FILE -nv -p PROJECT_NAME -pv VERSION_NAME

remove projects listed in a file    

    python3 recursive_delete_project.py -u BASE_URL -t TOKEN_FILE -nv -pl PROJECT_LIST_FILE

'''

import argparse
import json
import logging
import sys
import arrow

from blackduck import Client
from pprint import pprint,pformat

logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stderr, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.INFO)
logging.getLogger("urllib3").setLevel(logging.INFO)
logging.getLogger("blackduck").setLevel(logging.INFO)

strict = False

def remove_project_structure(project_name):
    project = find_project_by_name(project_name)
    if not project:
        logging.info(f"Project {project_name} does not exist.")
        return
    versions = bd.get_resource('versions', project)
    for version in versions:
        remove_project_version_structure(project_name, version['versionName'])

def remove_project_version_structure(project_name, version_name):
    project = find_project_by_name(project_name)
    if not project:
        logging.info(f"Project {project_name} does not exist.")
        return
    num_versions = bd.get_resource('versions', project, items=False)['totalCount']
    version = find_project_version_by_name(project,version_name)
    if not version:
        logging.info(f"Project {project_name} with version {version_name} does not exist.")
        return
    components = [
        c for c in bd.get_resource('components',version) if c['componentType'] == "SUB_PROJECT"
    ]
    logging.info(f"Project {project_name}:{version_name} has {len(components)} subprojects")
    for component in components:
        component_name = component['componentName']
        component_version_name = component['componentVersionName']
        logging.info(f"Removing subproject {component_name} from {project_name}:{version_name}")
        component_url = component['_meta']['href']
        response = bd.session.delete(component_url) 
        logging.info(f"Operation completed with {response}")
        remove_project_version_structure(component_name, component_version_name)
    logging.info(f"Removing {project_name}:{version_name}")
    if num_versions > 1:
        response = bd.session.delete(version['_meta']['href'])
    else:
        response = bd.session.delete(project['_meta']['href'])
    logging.info(f"Operation completed with {response}")

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



def parse_command_args():

    parser = argparse.ArgumentParser("python3 recursive_delete_project.py")
    parser.add_argument("-u", "--base-url",     required=True, help="Hub server URL e.g. https://your.blackduck.url")
    parser.add_argument("-t", "--token-file",   required=True, help="File containing access token")
    parser.add_argument("-nv", "--no-verify",   action='store_false', help="Disable TLS certificate verification")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-p", "--project-name",   required=False, help="Project Name")
    parser.add_argument("-pv", "--version-name",   required=False, help="Version Name")
    group.add_argument("-pl", "--project-list-file",   required=False, help="File containing project name list")
    return parser.parse_args()

def main():
    args = parse_command_args()
    with open(args.token_file, 'r') as tf:
        access_token = tf.readline().strip()
    global bd
    global scan_params
    scan_params = []
    bd = Client(base_url=args.base_url, token=access_token, verify=args.no_verify, timeout=60.0, retries=4)
    logging.info(f"{args}")

    if not (args.project_list_file or args.project_name):
        logging.error("Project Name or a File containing Project Names should be specified")
        return

    if args.project_list_file:
        with open(args.project_list_file) as file:
            lines = [line.rstrip() for line in file]
        for line in lines:
            remove_project_structure(line)
    elif args.version_name:
        remove_project_version_structure(args.project_name, args.version_name)
    else:
        remove_project_structure(args.project_name)

if __name__ == "__main__":
    sys.exit(main())