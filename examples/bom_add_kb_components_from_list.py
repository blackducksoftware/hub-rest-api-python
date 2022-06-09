'''
Created on June 8, 2022
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


'''
import csv
import sys
import argparse
import json
import logging
from urllib import response
from wsgiref import headers
import arrow
import re
import urllib
from pprint import pprint

from itertools import islice
from datetime  import timedelta
from datetime import datetime
from blackduck import Client

logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stderr, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("blackduck").setLevel(logging.DEBUG)

def find_kb_component(component_name):
    url = bd.base_url + "/api/search/kb-components"
    query = { "q": component_name }
    url = "{}?{}&limit=100".format(url,urllib.parse.urlencode(query))
    print (url)
    headers = {
    "Accept": "application/vnd.blackducksoftware.internal-1+json, application/json, */*;q=0.8"
    }
    response = bd.session.get(url, headers=headers)
    print (response)
    items = response.json()['items']
    hit_counts = dict()
    for item in items:
        for hit in item['hits']:
            aliases = hit.get('fields').get('aliases', None)
            if aliases and component_name.strip() in aliases:
                hit_counts[hit['_meta']['href']] = hit['fields']['release_count']
            elif component_name.strip() in hit['fields']['name']:
                hit_counts[hit['_meta']['href']] = hit['fields']['release_count']
    return hit_counts

def add_component_version(component_version, project_version):
    bom_url = project_version['_meta']['href'] + "/components"
    headers = { "Content-Type": "application/vnd.blackducksoftware.bill-of-materials-6+json" }
    data = {
        "component" : component_version['_meta']['href']
    }
    pprint (data)
    print(bom_url)
    response = bd.session.post(bom_url, json=data, headers=headers)
    print (response)

def get_matching_component_versions(url, component_version):
    print (url)
    response = bd.session.get(url)
    component = response.json()
    params = {"q": [ f"versionName:{component_version}" ]}
    versions = bd.get_resource('versions', component, params=params)
    for version in versions:
        print (url)
        print (version['versionName'])
        if version['versionName'] == component_version:
            add_component_version (version, project_version)

def parse_command_args():

    parser = argparse.ArgumentParser("Print copyrights for BOM using upstream origin or prior version if not available.")
    parser.add_argument("-u", "--base-url",     required=True, help="Hub server URL e.g. https://your.blackduck.url")
    parser.add_argument("-t", "--token-file",   required=True, help="File containing access token")
    parser.add_argument("-nv", "--no-verify",   action='store_false', help="Disable TLS certificate verification")
    parser.add_argument("project_name")
    parser.add_argument("version")
    parser.add_argument("component_input_file", help="Supply a file with components listed as foundry:componentname/version/arch one per line")

    return parser.parse_args()

def main():
    args = parse_command_args()
    with open(args.token_file, 'r') as tf:
        access_token = tf.readline().strip()
    global bd
    bd = Client(base_url=args.base_url, token=access_token, verify=args.no_verify, timeout=60.0, retries=4)

    global project_version

    project_version = None
    params = { "q": f"name:{args.project_name}"}

    project_match = None
    version_match = None
    projects = bd.get_resource('projects', params=params)
    for project in projects:
        print (project['name'])
        if args.project_name == project['name']:
            project_match = project

    if project_match:
        params = {"q": f"versionName{args.version}"}
        versions = bd.get_resource('versions', project, params=params)
        for version in versions:
            if args.version == version['versionName']:
                project_version = version

    if not project_version:
        logging.error (f"Project {args.project_name} version {args.version} not found, exiting")
        sys.exit()
   
    with open(args.component_input_file,"r") as f:
        inputdata = f.readlines()
    for line in inputdata:
        (name,version) = line.strip().split(" ")
        logging.info (f"Processing componemt name {name} version {version}")
        component_hits = find_kb_component(name)        
        for hit in component_hits:
            get_matching_component_versions(hit, version)

if __name__ == "__main__":
    sys.exit(main())
