#!/usr/bin/env python

'''
Purpose: Update project versions with licenses of their subprojects (components)

usage: update_project_with_component_licenses.py [-h] -u BASE_URL -t TOKEN_FILE [-nv] 

options:
  -h, --help            show this help message and exit
  -u BASE_URL, --base-url BASE_URL
                        Hub server URL e.g. https://your.blackduck.url
  -t TOKEN_FILE, --token-file TOKEN_FILE
                        containing access token
  -nv, --no-verify      disable TLS certificate verification
  -p PROJECT_NAME, --project-name PROJECT_NAME
                        Project Name
  -pv VERSION_NAME, --version-name VERSION_NAME
                        Project Version Name
 '''

import argparse
import json
import logging
import sys
import requests

from pprint import pprint
from blackduck import Client
from collections import defaultdict

def parse_command_args():
    parser = argparse.ArgumentParser("update_project_with_component_licenses.py [-h] -u BASE_URL -t TOKEN_FILE [-nv] ")
    parser.add_argument("-u", "--base-url", required=True, help="Hub server URL e.g. https://your.blackduck.url")
    parser.add_argument("-t", "--token-file", dest='token_file', required=True, help="containing access token")
    parser.add_argument("-nv", "--no-verify", dest='no_verify', action='store_false', help="disable TLS certificate verification")
    parser.add_argument("-p", "--project_name", required=True, help="Provide Project Name here")
    parser.add_argument("-v", "--version_name"). help="Provide Project Version here"
    return parser.parse_args()

def main():
    args = parse_command_args()
    with open(args.token_file, 'r') as tf:
        access_token = tf.readline().strip()
    global bd
    bd = Client(base_url=args.base_url, token=access_token, verify=args.no_verify, timeout=60.0, retries=4)
    process_project_version(args.project_name, args.version_name, args)

def process_project_version(project_name, version_name, args):
    #Validating only 1 Project
    params = {
        'q': [f"name:{args.project_name}"]
    }
    projects = [p for p in bd.get_resource('projects', params=params) if p['name'] == args.project_name]
    assert len(projects) == 1, f"There should be one, and only one project named {args.project_name}. We found {len(projects)}"
    project = projects[0]
    
    #Validates only 1 Version
    params = {
        'q': [f"versionName:{args.version_name}"]
    }
    versions = [v for v in bd.get_resource('versions', project, params=params) if v['versionName'] == args.version_name]
    assert len(versions) == 1, f"There should be one, and only one version named {args.version_name}. We found {len(versions)}"
    version = versions[0]
    
    

    #Return only sub-projects, not components
    components = (
        c for c in bd.get_resource('components',version) if c['componentType'] == "SUB_PROJECT"
        )
    for components in components:
        #JSON body
        body =  defaultdict(list)
               
        existing_licenses = []

        #Defining subcomponents 
        body["componentName"]=components['componentName']
        body["componentVersionName"]=components['componentVersionName']
        body["component"]=components['component']
        body["componentVersion"]=components['componentVersion']
        body["componentType"]="SUB_PROJECT"
        pprint(components['componentName'])
        pprint(components['componentVersionName'])
        url = components['_meta']['href']
        #Capture current License statement of components to add to
        if len(components['licenses'][0]['licenses']) > 0:
            for i, v in enumerate(components['licenses'][0]['licenses']):
                parent_license_display = components['licenses'][0]['licenses'][i]['licenseDisplay']
                parent_license = components['licenses'][0]['licenses'][i]['license']
                addlicense ={"licenseDisplay":parent_license_display,"license": parent_license }
                body['licenses'].append(addlicense)
                if parent_license_display not in existing_licenses:
                    existing_licenses.append(parent_license_display)
        else:
            parent_license_display = components['licenses'][0]['licenses'][0]['licenseDisplay']
            parent_license = components['licenses'][0]['licenses'][0]['license']
            addlicense ={"licenseDisplay":parent_license_display,"license": parent_license }
            body['licenses'].append(addlicense)
            if parent_license_display not in existing_licenses:
                existing_licenses.append(parent_license_display)
        #Retrieving componentName values
        subprojects = [p for p in bd.get_resource('projects') if p['name'] == components['componentName']]
        subproject = subprojects[0]
        subversions = [v for v in bd.get_resource('versions', subproject) if v['versionName'] == components['componentVersionName']]
        subversion = subversions[0]
        for subcomponent in bd.get_resource('components',subversion):
            #Parse through multiple licenses
            if len(subcomponent['licenses'][0]['licenses']) > 0:
                for i, v in enumerate(subcomponent['licenses'][0]['licenses']):
                    child_license_display = subcomponent['licenses'][0]['licenses'][i]['licenseDisplay']
                    child_license = subcomponent['licenses'][0]['licenses'][i]['license']
                    addlicense ={"licenseDisplay":child_license_display,"license": child_license }
                    if child_license_display not in existing_licenses:
                        body['licenses'].append(addlicense)
                        existing_licenses.append(child_license_display)
            #When only one license return it
            else:
                child_license_display = subcomponent['licenses'][0]['licenseDisplay']
                child_license = subcomponent['licenses'][0]['license']
                addlicense ={"licenseDisplay":child_license_display,"license": child_license }
                if child_license_display not in existing_licenses:
                        body['licenses'].append(addlicense)
                        existing_licenses.append(child_license_display)
        pprint(dict(body))
        try:
            r = bd.session.put(url,json=(dict(body)))
            if r.status_code == 200:
                print("updated project")
        except requests.HTTPError as err:
            bd.http_error_handler(err)
if __name__ == "__main__":
    sys.exit(main())