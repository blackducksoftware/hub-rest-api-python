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
import json
import logging
import sys

from blackduck import Client

parser = argparse.ArgumentParser("GET CPE's from a BD server")
parser.add_argument("--base-url", required=True, help="Hub server URL e.g. https://your.blackduck.url")
parser.add_argument("--token-file", dest='token_file', required=True, help="containing access token")
parser.add_argument("--no-verify", dest='verify', action='store_false', help="disable TLS certificate verification")
parser.add_argument("cpe_id", help="Provide a CPE (2.2 or 2.3 xml format) ID - e.g. \"cpe:2.3:a:apache:log4j:2.11.1:-:*:*:*:*:*:*\" To get a complete dictionary of CPE IDs go to the NIST site, https://nvd.nist.gov/products/cpe")
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

cpes = [cpe for cpe in bd.get_items(f"/api/cpes?q={args.cpe_id}")]
if cpes:
    for cpe in cpes:
        cpe['cpe-origins'] = [o for o in bd.get_resource("cpe-origins", cpe)]
        cpe['cpe-versions'] = [v for v in bd.get_resource("cpe-versions", cpe)]
print(json.dumps(cpes)) 