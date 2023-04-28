'''
Created on April 26, 2023
@author: kumykov

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

This script will read the content of the job page from diagnostic section 
in Blackduck.

Data will be written into a file named bd-stats-<isotamestamp>.txt

Requirements

- python3 version 3.8 or newer recommended
- the following packages are used by the script and should be installed 
  prior to use:	
    argparse
    blackduck
    logging
    datetime

- Blackduck instance
- API token with sufficient privileges to perform project version phase 
  change.

Install python packages with the following command:

 pip3 install argparse blackduck logging datetime

Using

place the token into a file (token in this example) then execute:

 python3 get_debug_page.py -u $BD_URL -t token -nv


usage: python3 get_debug_page.py [-h] -u BASE_URL -t TOKEN_FILE [-nv] [-o OUTPUT_FILE] [--stdout]

options:
  -h, --help            show this help message and exit
  -u BASE_URL, --base-url BASE_URL
                        Hub server URL e.g. https://your.blackduck.url
  -t TOKEN_FILE, --token-file TOKEN_FILE
                        containing access token
  -nv, --no-verify      disable TLS certificate verification
  -o OUTPUT_FILE, --output-file OUTPUT_FILE
                        Output file name pattern
  --stdout              Output to stdout, instead of the file

'''

from blackduck import Client

import argparse
import logging
from pprint import pprint
from datetime import datetime

logging.basicConfig(
    level=logging.DEBUG,
    format="[%(asctime)s] {%(module)s:%(lineno)d} %(levelname)s - %(message)s"
)

parser = argparse.ArgumentParser("Get a job stats from debug page")
parser.add_argument("-u", "--base-url", required=True, help="Hub server URL e.g. https://your.blackduck.url")
parser.add_argument("-t", "--token-file", dest='token_file', required=True, help="containing access token")
parser.add_argument("-nv", "--no-verify", dest='verify', action='store_false', help="disable TLS certificate verification")
parser.add_argument("-o", "--output-file", dest='output_file', default='bd-stats', help="Output file name pattern")
parser.add_argument("--stdout", dest='stdout', action='store_true', help='Output to stdout, instead of the file')
args = parser.parse_args()

with open(args.token_file, 'r') as tf:
    access_token = tf.readline().strip()

bd = Client(base_url=args.base_url, token=access_token, verify=args.verify)

url = "https://ec2-44-202-86-163.compute-1.amazonaws.com/debug?job=true"

result = bd.session.get(url)

if args.stdout:
    print(result.text)

else:
    timestamp = datetime.now().isoformat()
    filename = f"{args.output_file}-{timestamp}.txt"
    f = open(filename,"w")
    f.write(result.text)
    f.close()