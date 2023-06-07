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

def getlicensesfromprojectversion(subproject):
    subprojecturl=subproject['_meta']['href']
    x = subprojecturl.split("/")
    del x[5]
    del x[5]
    del x[5]
    del x[5]
    subprojecturl = "/".join(x)
    version = bd.session.get(subprojecturl).json()
    components = bd.get_resource('components',version)
    licenselist = []
    for component in components:
        for license in component['licenses']:
            if license.get("licenseType",None) :
                for innerlicense in license['licenses']:
                    licenselist.append(innerlicense)
            else:
                licenselist.append(license)
    return licenselist
    

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
    components = [
        c for c in bd.get_resource('components',version) if c['componentType'] == "SUB_PROJECT"
    ]

    for subproject in components:
    
        url = subproject['_meta']['href']
        subprojectlicenses = getlicensesfromprojectversion(subproject)
        print(subprojectlicenses)
        licenseblock = [
        {
            "licenseType": "CONJUNCTIVE",
            "licenses": subproject['licenses'][0]['licenses']}]
        for license in subprojectlicenses:
            pprint(license)
            licenseblock[0]['licenses'].append({"licenseDisplay":license['licenseDisplay'],"license":license['license']})
        subproject['licenses']=licenseblock
        #pprint(subproject)
        r = bd.session.put(url,json=subproject)
        print(r)
        

if __name__ == "__main__":
    sys.exit(main())