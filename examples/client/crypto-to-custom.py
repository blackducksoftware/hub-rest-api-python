'''
Created on October 12, 2023
@author: kumykov

Copyright (C) 2023 Synopsys, Inc.
http://www.synopsys.com/

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

This script is provided as an example of populating custom field data 
based on BOM components crypto information. 
The goal is to enable policy functionality that would be triggered by 
cryptographic features of a component.

The scriot will analyze ciphers included in a component and will set 
a BOM Component custom field value to reflec that.

Requirements

- python3 version 3.8 or newer recommended
- the following packages are used by the script and should be installed 
  prior to use:	
    argparse
    blackduck
    logging
    sys
    json
    pprint
- Blackduck instance
- API token with sufficient privileges to perform project version phase 
  change.

Install python packages with the following command:

 pip3 install argparse blackduck logging sys json pprint

Using

Script expects a boolean custom field labeled "BadCrypto" on a BOM Component.
A policy that is triggered by BadCrypto custom field value used to visualise 
results.

usage: crypto-to-custom.py [-h] -u BASE_URL -t TOKEN_FILE -pn PROJECT_NAME -vn VERSION_NAME [-nv] [--reset]

options:
  -h, --help            show this help message and exit
  -u BASE_URL, --base-url BASE_URL
                        Hub server URL e.g. https://your.blackduck.url
  -t TOKEN_FILE, --token-file TOKEN_FILE
                        File containing access token
  -pn PROJECT_NAME, --project-name PROJECT_NAME
                        Project Name
  -vn VERSION_NAME, --version-name VERSION_NAME
                        Version Name
  -nv, --no-verify      Disable TLS certificate verification
  --reset               Undo the changes made by thjis script 


'''

import argparse
from blackduck import Client
from pprint import pprint
import logging
import sys
import json

logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stderr, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.INFO)
logging.getLogger("urllib3").setLevel(logging.INFO)
logging.getLogger("blackduck").setLevel(logging.INFO)

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

    parser = argparse.ArgumentParser("crypto-to-custom.py")
    parser.add_argument("-u", "--base-url",     required=True, help="Hub server URL e.g. https://your.blackduck.url")
    parser.add_argument("-t", "--token-file",   required=True, help="File containing access token")
    parser.add_argument("-pn", "--project-name",   required=True, help="Project Name")
    parser.add_argument("-vn", "--version-name",   required=True, help="Version Name")
    parser.add_argument("-nv", "--no-verify",   action='store_false', help="Disable TLS certificate verification")
    parser.add_argument("--reset",   action='store_true', help="Undo the changes made by thjis script")
    return parser.parse_args()

def set_custom_field(field, url, value):
    payload = {"fields": [{"customField": field['_meta']['href'],"values": value}]}
    headers = {"Accept": "application/vnd.blackducksoftware.bill-of-materials-6+json",
               "Content-Type": "application/vnd.blackducksoftware.bill-of-materials-6+json"}
    response = bd.session.put(url, data=json.dumps(payload), headers=headers)
    print(response)

def process_project_version(args):
    project = find_project_by_name(args.project_name)
    version = find_project_version_by_name(project, args.version_name)

    components = bd.get_resource('components',version)
    for component in components:
        print (component['componentName'], component['componentVersionName'])
        custom_fields = bd.get_resource('custom-fields',component, items=False)
        custom_fields_url = custom_fields['_meta']['href']
        c = [x for x in custom_fields['items'] if x['label'] == 'BadCrypto'][0]
        resources = bd.list_resources(component)
        if 'crypto-algorithms' in resources.keys():
            crypto_algorithms = bd.get_resource('crypto-algorithms', component)
            for crypto in crypto_algorithms:
                if crypto['knownWeaknesses']:
                    pprint('Has Weakness')
                    value = ['true']
                    if args.reset:
                        value = []
                    set_custom_field(c, custom_fields_url, value=value)
                    break

def main():
    args = parse_command_args()
    with open(args.token_file, 'r') as tf:
        access_token = tf.readline().strip()
    global bd
    bd = Client(base_url=args.base_url, token=access_token, verify=args.no_verify, timeout=60.0, retries=4)

    process_project_version(args)

if __name__ == "__main__":
    sys.exit(main())

