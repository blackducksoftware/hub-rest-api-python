#$!/usr/bin/env python3
#

'''
Created on Sep 23, 2024
@author: kumykov

Net Add Components.

This script will extract components form a source project and add them as 
Manually Added components to the target project

'''
from blackduck import Client

import argparse
import logging
import sys
from pprint import pprint

logging.basicConfig(
    level=logging.DEBUG,
    format="[%(asctime)s] {%(module)s:%(lineno)d} %(levelname)s - %(message)s"
)

def find_project_by_name(bd, project_name):
    params = {
        'q': [f"name:{project_name}"]
    }
    projects = [p for p in bd.get_resource('projects', params=params) if p['name'] == project_name]
    assert len(projects) == 1, f"Project {project_name} not found."
    return projects[0]

def find_project_version_by_name(bd, project, version_name):
    params = {
        'q': [f"versionName:{version_name}"]
    }
    versions = [v for v in bd.get_resource('versions', project, params=params) if v['versionName'] == version_name]
    assert len(versions) == 1, f"Project version {version_name} for project {project['name']} not found"
    return versions[0]

def parse_command_args():

    parser = argparse.ArgumentParser("Extract components form a source project and add them to the target project as manual components.\n")
    parser.add_argument("-u", "--base-url",     required=True, help="Hub server URL e.g. https://your.blackduck.url")
    parser.add_argument("-t", "--token-file",   required=True, help="File containing access token")
    parser.add_argument("-nv", "--no-verify",   action='store_false', help="Disable TLS certificate verification")
    parser.add_argument('-sp', '--source-project', help="Source Project")
    parser.add_argument('-sv', '--source-version', help="Source Project Version")
    parser.add_argument('-tp', '--target-project', help="Target Project")
    parser.add_argument('-tv', '--target-version', help="Target Project Version")
    
    return parser.parse_args()

def add_component_to_a_project_version(bd, component, components_url):
    headers = {
        "Content-Type": "application/vnd.blackducksoftware.bill-of-materials-6+json"
    }
    data = dict()
    component_version = component.get('componentVersion', component.get('component'))
    component_origins = component['origins']
    component_license = component['licenses'][0]['license']
    if len(component_origins) > 0:
        for origin in component_origins:
            origin_url = origin['origin']
            payload = {"component": origin_url}
            payload['license'] = component_license
            result = bd.session.post(components_url, json=payload, headers=headers)
            pprint(result)
    else:
        data['component'] = component_version
        data['license'] = component_license
        result = bd.session.post(components_url, json=data, headers=headers)
        pprint(result) 


def main():
    args = parse_command_args()
    with open(args.token_file, 'r') as tf:
        access_token = tf.readline().strip()
    global bd
    bd = Client(base_url=args.base_url, token=access_token, verify=args.no_verify, timeout=60.0, retries=4)

    project = find_project_by_name(bd, args.source_project)
    version = find_project_version_by_name(bd, project, args.source_version)

    target_project = find_project_by_name(bd, args.target_project)
    target_version = find_project_version_by_name(bd, target_project, args.target_version)

    dict = bd.list_resources(target_version)
    components_url = dict['components']
    
    components = bd.get_resource('components', version)
    for component in components:
        add_component_to_a_project_version(bd, component, components_url)


if __name__ == "__main__":
    sys.exit(main())
