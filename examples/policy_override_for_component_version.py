'''
Created on May 20, 2022
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

This scrit will identify project versions that are using specified components
and override policies for that component in each project version.
Status will change from IN_VIOLATION to IN_VIOLATION_OVERRIDEN

identification of a project version is done with componet version url 

'''
import csv
from pprint import pprint
import sys
import argparse
import json
import logging
import arrow
import re
from pprint import pprint

from itertools import islice
from datetime  import timedelta
from datetime import datetime
from blackduck import Client

logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stderr, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("blackduck").setLevel(logging.DEBUG)

def override_policy_violaton(version, component_name, component_version, override_rationale):
    params = {"q":f"componentOrVersionName:{component_name}"}
    components = bd.get_resource('components', version, params=params)
    for component in components:
        policy_status = bd.get_resource('policy-status', component, items=False)
        url = bd.list_resources(policy_status)['href']
        data = {
                "approvalStatus" : "IN_VIOLATION_OVERRIDDEN",
                "comment" : f"{override_rationale}",
                "updatedAt" : datetime.now().isoformat()
                }
        headers = {"Content-Type": "application/vnd.blackducksoftware.bill-of-materials-6+json",
                    "Accept": "application/vnd.blackducksoftware.bill-of-materials-6+json" }
        r = bd.session.put(url, headers = headers, json=data)
        # r.raise_for_status()
        logging.info(f"Policy status update completion code {r.status_code}")

def parse_command_args():

    parser = argparse.ArgumentParser("Print copyrights for BOM using upstream origin or prior version if not available.")
    parser.add_argument("-u", "--base-url",     required=True, help="Hub server URL e.g. https://your.blackduck.url")
    parser.add_argument("-t", "--token-file",   required=True, help="File containing access token")
    parser.add_argument("-cu", "--component-url",   required=True, help="Project Name")
    parser.add_argument("-nv", "--no-verify",   action='store_false', help="Disable TLS certificate verification")
    parser.add_argument("-or", "--override-rationale", required=True, help="Override rationale to dicplay")

    return parser.parse_args()

def main():
    args = parse_command_args()
    with open(args.token_file, 'r') as tf:
        access_token = tf.readline().strip()
    global bd
    bd = Client(base_url=args.base_url, token=access_token, verify=args.no_verify, timeout=60.0, retries=4)

    response = bd.session.get(args.component_url)
    print(response)
    component_version = response.json()
    component = bd.get_resource("component", component_version, items=False)
    component_name = component['name']
    component_version_name = component_version['versionName']
    print(f"processing references for {component_name} version {component_version_name}")
    override_rationale = args.override_rationale

    references = bd.get_resource("references", component_version)
    for project_version in references:
        override_policy_violaton(project_version, component_name, component_version_name, override_rationale )
        # undo_override_policy_violaton(project_version, component_name, component_version_name, override_rationale )

if __name__ == "__main__":
    sys.exit(main())
