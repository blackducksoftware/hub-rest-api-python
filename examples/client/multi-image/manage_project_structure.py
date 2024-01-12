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

This script will scan a multi-container project into 
hierarchical structure.

Project Name
      Project Version
           Subproject Name
                Subproject Vesrsion
                    Base Image
                        Base Image Version
                    Add on Image
                        Add on Image Version

usage: python3 manage_project_structure.py [-h] -u BASE_URL -t TOKEN_FILE [-pg PROJECT_GROUP] -p PROJECT_NAME -pv VERSION_NAME
                                           [-sp SUBPROJECT_LIST] [-nv] [-rm] [--clone-from CLONE_FROM] [--dry-run]

options:
  -h, --help            show this help message and exit
  -u BASE_URL, --base-url BASE_URL
                        Hub server URL e.g. https://your.blackduck.url
  -t TOKEN_FILE, --token-file TOKEN_FILE
                        File containing access token
  -pg PROJECT_GROUP, --project_group PROJECT_GROUP
                        Project Group to be used
  -p PROJECT_NAME, --project-name PROJECT_NAME
                        Project Name
  -pv VERSION_NAME, --version-name VERSION_NAME
                        Project Version Name
  -sp SUBPROJECT_LIST, --subproject-list SUBPROJECT_LIST
                        List of subprojects to generate with subproject:container:tag
  -nv, --no-verify      Disable TLS certificate verification
  -rm, --remove         Remove project structure with all subprojects (DANGEROUS!)
  --clone-from CLONE_FROM
                        Main project version to use as template for cloning
  --dry-run             Create structure only, do not execute scans

Subprojects ae specified as subproject:[container]:[tag]
if container name omited it will be set to subproject
if tag omited it would be set to 'latest'

Container image name scanned will be written into project version nickname field

  

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

def remove_project_structure(project_name, version_name):
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
        remove_project_structure(component_name, component_version_name)
    logging.info(f"Removing {project_name}:{version_name}")
    if num_versions > 1:
        response = bd.session.delete(version['_meta']['href'])
    else:
        response = bd.session.delete(project['_meta']['href'])
    logging.info(f"Operation completed with {response}")

def remove_codelocations_recursively(version):
    components = bd.get_resource('components', version)
    subprojects = [x for x in components if x['componentType'] == 'SUB_PROJECT']
    logging.info(f"Found {len(subprojects)} subprojects")
    unmap_all_codelocations(version)
    for subproject in subprojects:
        subproject_name = subproject['componentName']
        subproject_version_name = subproject['componentVersionName']
        project = find_project_by_name(subproject_name)
        if not project:
            logging.info(f"Project {subproject_name} does not exist.")
            return
        subproject_version = find_project_version_by_name(project, subproject_version_name)   
        if not subproject_version:
            logging.info(f"Project {subproject_name} with version {subversion_name} does not exist.")
            return
        remove_codelocations_recursively(subproject_version)

def unmap_all_codelocations(version):
    codelocations = bd.get_resource('codelocations',version)
    for codelocation in codelocations:
        logging.info(f"Unmapping codelocation {codelocation['name']}")
        codelocation['mappedProjectVersion'] = ""
        response = bd.session.put(codelocation['_meta']['href'], json=codelocation)
        pprint (response)


def find_or_create_project_group(group_name):
    url = '/api/project-groups'
    params = {
        'q': [f"name:{group_name}"]
    }
    groups = [p for p in bd.get_items(url, params=params) if p['name'] == group_name]
    if len(groups) == 0:
        headers = {
            'Accept': 'application/vnd.blackducksoftware.project-detail-5+json',
            'Content-Type': 'application/vnd.blackducksoftware.project-detail-5+json'
        }
        data = {
            'name': group_name
        }
        response = bd.session.post(url, headers=headers, json=data)
        return response.headers['Location'] 
    else:
        return groups[0]['_meta']['href']

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

def create_project_version(project_name,version_name,args, nickname = None):
    version_data = {"distribution": "EXTERNAL", "phase": "DEVELOPMENT", "versionName": version_name}
    if nickname:
        version_data['nickname'] = nickname
    url = '/api/projects'
    project = find_project_by_name(project_name)
    if project:
        data = version_data
        url = project['_meta']['href'] + '/versions'
    else:
        data = {"name": project_name,
                "projectGroup": find_or_create_project_group(args.project_group),
                "versionRequest": version_data}
    return bd.session.post(url, json=data)

def add_component_to_version_bom(child_version, version):
    url = version['_meta']['href'] + '/components'
    data = { 'component': child_version['_meta']['href']}
    return bd.session.post(url, json=data)

def create_and_add_child_projects(version, args):
    version_url = version['_meta']['href'] + '/components'
    for child_spec in [x.split(':') for x in args.subproject_list.split(",")]:
        i = iter(child_spec)
        child = next(i)
        repo = next(i, child)
        tag = next(i,'latest')
        container_spec = f"{repo}:{tag}"
        scan_param = {'image': container_spec, 'project': child, 'version': args.version_name, 'project_group': args.project_group}
        if args.clone_from:
            scan_param['clone_from'] = args.clone_from
        project = find_project_by_name(child)
        if project:
            version = find_project_version_by_name(project,args.version_name)
            if version:
                if strict:
                    logging.error(f"Child project {project['name']} with version {args.version_name} exists.")
                    sys.exit(1)
                else:
                    logging.info(f"Child project {project['name']} with version {args.version_name} found.")
                    logging.info(f"Recursively removing codelocations for {project['name']} with version {args.version_name} ")
                    remove_codelocations_recursively(version)
            else:
                response = create_project_version(child,args.version_name, args, nickname=container_spec)
                logging.info(f"Creating project {child} : {args.version_name} completed with {response}")
                if response.ok:
                    child_version = find_project_version_by_name(find_project_by_name(child),args.version_name)
                    child_version_url = child_version['_meta']['href']
                    response = bd.session.post(version_url,json={'component': child_version_url})
                    logging.info(f"Adding {child} : {args.version_name} to parent project completed with {response}")
        else:
            response = create_project_version(child,args.version_name, args, nickname=container_spec)
            logging.info(f"Creating project {child} : {args.version_name} completed with {response}")
            if response.ok:
                child_version = find_project_version_by_name(find_project_by_name(child),args.version_name)
                child_version_url = child_version['_meta']['href']
                response = bd.session.post(version_url,json={'component': child_version_url})
                logging.info(f"Adding {child} : {args.version_name} to parent project completed with {response}")
        scan_params.append(scan_param)

def create_project_structure(args):
    project = find_project_by_name(args.project_name)
    logging.info(f"Project {args.project_name} located")
    if project:
        version = find_project_version_by_name(project,args.version_name)
        if version:
            if strict:
                logging.error(f"Project {project['name']} with version {args.version_name} exists.")
                sys.exit(1) 
            else:
                logging.info(f"Found Project {project['name']} with version {args.version_name}.")
        else:
            response = create_project_version(args.project_name,args.version_name,args)
            if response.ok:
                version = find_project_version_by_name(find_project_by_name(args.project_name),args.version_name)
                logging.info(f"Project {args.project_name} : {args.version_name} created")
            else:
                logging.info(f"Failed to create Project {args.project_name} : {args.version_name} created")
                sys.exit(1)
    else:
        response = create_project_version(args.project_name,args.version_name,args)
        if response.ok:
            version = find_project_version_by_name(find_project_by_name(args.project_name),args.version_name)
            logging.info(f"Project {args.project_name} : {args.version_name} created")
        else:
            logging.info(f"Failed to create Project {args.project_name} : {args.version_name} created")
            sys.exit(1)
    logging.info(f"Checking/Adding subprojects to {args.project_name} : {version['versionName']}")
    create_and_add_child_projects(version, args)

def scan_container_images(scan_params, hub):
    from scan_docker_image_lite import scan_container_image
    for params in scan_params:
        detect_options =    (f"--detect.parent.project.name={params['project']} "
                            f"--detect.parent.project.version.name={params['version']} " 
                            f"--detect.project.version.nickname={params['image']}")
        clone_from = params.get('clone_from', None)
        if clone_from:
            detect_options += f" --detect.clone.project.version.name={clone_from}"
        project_group = params.get('project_group', None)
        if project_group:
            detect_options += f" --detect.project.group.name=\"{project_group}\""
        scan_container_image(
            params['image'], 
            None, 
            None, 
            None, 
            params['project'], 
            params['version'],
            detect_options,
            hub=hub
        )


def parse_command_args():

    parser = argparse.ArgumentParser("python3 manage_project_structure.py")
    parser.add_argument("-u", "--base-url",     required=True, help="Hub server URL e.g. https://your.blackduck.url")
    parser.add_argument("-t", "--token-file",   required=True, help="File containing access token")
    parser.add_argument("-pg", "--project_group", required=False, default='Multi-Image', help="Project Group to be used")
    parser.add_argument("-p", "--project-name",   required=True, help="Project Name")
    parser.add_argument("-pv", "--version-name",   required=True, help="Project Version Name")
    parser.add_argument("-sp", "--subproject-list",   required=False, help="List of subprojects to generate with subproject:container:tag")
    parser.add_argument("-nv", "--no-verify",   action='store_false', help="Disable TLS certificate verification")
    parser.add_argument("-rm", "--remove",   action='store_true', required=False, help="Remove project structure with all subprojects (DANGEROUS!)")
    parser.add_argument("--clone-from", required=False, help="Main project version to use as template for cloning")
    parser.add_argument("--dry-run", action='store_true', required=False, help="Create structure only, do not execute scans")
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

    if args.remove:
        remove_project_structure(args.project_name, args.version_name)
    else:
        create_project_structure(args)
        if args.dry_run:
            logging.info(f"{pformat(scan_params)}")
        else:
            logging.info("Now execution scans")
            from blackduck.HubRestApi import HubInstance
            hub = HubInstance(args.base_url, api_token=access_token, insecure=True, debug=False)
            scan_container_images(scan_params, hub)


if __name__ == "__main__":
    sys.exit(main())
