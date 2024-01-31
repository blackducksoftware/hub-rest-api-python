'''
Created on Jan 29, 2024
@author: pedapati

Copyright (C) 2024 Synopsys, Inc.
https://www.synopsys.com

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

This program will Export KB & KB Modified Component Status updates from one Black Duck Server and Import onto another Black Duck Server
'''

from blackduck import Client

import requests
import argparse
import json
import logging
import sys
import time
from pprint import pprint


NAME = 'copy_kb_component_status_updates.py'
VERSION = '2024-01-29'

print(f'{NAME} ({VERSION}). Copyright (c) 2023 Synopsys, Inc.')


logging.basicConfig(
    level=logging.DEBUG,
    format="[%(asctime)s] {%(module)s:%(lineno)d} %(levelname)s - %(message)s"
)


logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stderr, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("blackduck").setLevel(logging.WARNING)


def parse_command_args():

    parser = argparse.ArgumentParser(sys.argv[0])
    parser.add_argument("-su", "--source-bd-url",     required=True, help="Source BD server URL to copy KB component adjustments from e.g. https://your.blackduck.url")
    parser.add_argument("-st", "--source-token-file",   required=True, help="File containing Source BD access token")
    parser.add_argument("-du", "--dest-bd-url",     required=True, help="Destination BD server URL to apply KB component adjustments to e.g. https://your.blackduck.url")
    parser.add_argument("-dt", "--dest-token-file",   required=True, help="File containing Destination BD access token")
    parser.add_argument("-nv", "--no-verify",   action='store_false', help="Disable TLS certificate verification")
    return parser.parse_args()


def main():
    args = parse_command_args()
    ## Step 1 Source Black Duck Server - Authentication
    with open(args.source_token_file, 'r') as tf:
        access_token = tf.readline().strip()
    bd1 = Client(base_url=args.source_bd_url, token=access_token, verify=args.no_verify, timeout=60.0, retries=4)
    ## Step 2 Destination Black Duck Server - Authentication
    with open(args.dest_token_file, 'r') as tf:
        access_token1 = tf.readline().strip()
    bd2 = Client(base_url=args.dest_bd_url, token=access_token1, verify=args.no_verify, timeout=60.0, retries=4)
    ## Step 3 Source Black Duck Server - Get KB Components with Status Updates
    headers = {'Accept': 'application/vnd.blackducksoftware.internal-1+json'}
    get_comp_url = f"{bd1.base_url}/api/components?filter=componentApprovalStatus%3Ain_review&filter=componentApprovalStatus%3Areviewed&filter=componentApprovalStatus%3Aapproved&filter=componentApprovalStatus%3Alimited_approval&filter=componentApprovalStatus%3Arejected&filter=componentApprovalStatus%3Adeprecated&filter=componentSource%3Akb_and_kb_modified&limit=25&offset=0"
    get_comp_json = bd1.session.get(get_comp_url, headers=headers).json()
    total = str(get_comp_json["totalCount"])
    print("Found " + total + " KB components with status updates")
    print()
    for component in get_comp_json["items"]:
        comp_name = component['name']
        # comp_url = component['url']
        comp_status = component['approvalStatus']
        comp_url = component['_meta']['href']
        comp_id = comp_url.split("/")[-1]
        print("Updating KB Component " + comp_name + " status to " + comp_status)
        ## Step 4 Destination Black Duck Server - Update KB Components with Status Updates
        headers = {'Content-Type': 'application/vnd.blackducksoftware.component-detail-4+json', 'Accept': 'application/vnd.blackducksoftware.component-detail-4+json'}
        put_data = {"name": comp_name, "approvalStatus": comp_status}
        put_comp_url = f"{bd2.base_url}/api/components/{comp_id}"
        update_comp_results=bd2.session.put(put_comp_url, headers=headers, data=json.dumps(put_data))
        if update_comp_results.status_code == 200:
            message = f"{update_comp_results}"
            print("Successfully updated status of " + comp_name + " to " + comp_status)
            print()
        else:
            message = f"{update_comp_results.json()}"
            print("Updating status FAILED with error message:")
            print()
            logging.debug({message})
            print()
    
    
if __name__ == "__main__":
    sys.exit(main())