#!/usr/bin/env python

'''
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
import argparse
import csv
import json
import logging
import sys

# pip install xlwt
import xlwt
from xlwt import Workbook

from blackduck import Client

FORMAT_CHOICES=["JSON", "CSV", "XSL"]
DEFAULT_OUTPUT_BASE="inuse_licenses"

parser = argparse.ArgumentParser("Get licenses that are in-use.\nWARNING: This program using internal, unsupported REST API endpoints and could break in future releases of the product.\n")
parser.add_argument("--base-url", required=True, help="Hub server URL e.g. https://your.blackduck.url")
parser.add_argument("--token-file", dest='token_file', required=True, help="containing access token")
parser.add_argument("--no-verify", dest='verify', action='store_false', help="disable TLS certificate verification")
parser.add_argument(
    "-f", "--format", 
    default="JSON", 
    choices=FORMAT_CHOICES, 
    help=f"Choose the output format. Must be one of {', '.join(FORMAT_CHOICES)}")
parser.add_argument(
    "-o", "--output-file-base", 
    dest="output_file_base", 
    default=DEFAULT_OUTPUT_BASE, 
    help=f"Set the base name for the output file (default: {DEFAULT_OUTPUT_BASE}. The format will determine the file extension (e.g. format=JSON means file will end with .json)")
# parser.add_argument("-u", "--usage-details", dest="usage_details", action='store_true', help="Use this option to retrieve license usage details which will show what project-versions and components are using the license")
args = parser.parse_args()


logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stderr, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("blackduck").setLevel(logging.WARNING)

with open(args.token_file, 'r') as tf:
    access_token = tf.readline().strip()

bd = Client(
    base_url=args.base_url,
    token=access_token,
    verify=args.verify
)

# WARNING:
#   This uses an internal, un-supported API endpoint (see below) 
#   and therefore could break in future versions of Black Duck. 
#   This script was tested with BD v2021.8.2. 
#
# An ER has been filed in Synopsys Jira ticket HUB-26144 to make a 
# in-use filter part of a public endpoint for retrieving licenses

inuse_licenses_url = f"{bd.base_url}/api/internal/composite/licenses?filter=inUse:true"

headers={'Accept':'application/vnd.blackducksoftware.internal-1+json'}
inuse_licenses_d = {l['name']:l for l in bd.get_items(inuse_licenses_url, headers=headers)}

columns = [
    'License Name',
    'License Family',
    'License Approval Status',
    'License Source',
    'License Ownership',
    'Components Using License'
]

if args.format == "JSON":
    with open(f"{args.output_file_base}.json", "w") as f:
        json.dump(inuse_licenses_d, f, indent=4)
elif args.format == "CSV":
    with open(f"{args.output_file_base}.csv", "w") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for lic_name, lic_info in inuse_licenses_d.items():
            row = {
                'License Name': lic_name,
                'License Family': lic_info['licenseFamily']['name'],
                'License Approval Status': lic_info['licenseStatus'],
                'License Source': lic_info['licenseSource'],
                'License Ownership': lic_info['ownership'],
                'Components Using License': lic_info['bomComponentCount']
            }
            writer.writerow(row)
elif args.format == "XSL":
    data_to_write = list()
    wb = Workbook()
    inuse_licenses_sheet = wb.add_sheet('In-use licenses')

    xls_columns = [
        (0,i,col) for i,col in enumerate(columns)
    ]
    data_to_write.extend(xls_columns)

    row = 1
    for lic_name, lic_info in inuse_licenses_d.items():
        data_to_write.extend([
                (row, 0, lic_name),
                (row, 1, lic_info['licenseFamily']['name']),
                (row, 2, lic_info['licenseStatus']),
                (row, 3, lic_info['licenseSource']),
                (row, 4, lic_info['ownership']),
                (row, 5, lic_info['bomComponentCount']),
            ])
        row += 1
    for d in data_to_write:
        inuse_licenses_sheet.write(d[0], d[1], d[2])

    wb.save(f"{args.output_file_base}.xls")
else:
    print("Unsupported output format, hmmm")







