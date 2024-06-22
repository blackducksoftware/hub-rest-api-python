#!/usr/bin/env python

'''
Copyright (C) 2024 Synopsys, Inc.
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

usage: match_snippets.py [-h] --base-url BASE_URL --token-file TOKEN_FILE [--no-verify] [--input INPUT]

options:
  -h, --help            show this help message and exit
  --base-url BASE_URL   Hub server URL e.g. https://your.blackduck.url
  --token-file TOKEN_FILE
                        containing access token
  --no-verify           disable TLS certificate verification
  --input INPUT         File containing code snippet or stdin

Match a snippet of a code.
This functionality requires 'Generative AI Compliance' option licenses


Examples:

Curl file content from github and match it against Black Duck KB
and format the output using jq utility
    curl https://raw.githubusercontent.com/apache/kafka/trunk/shell/src/main/java/org/apache/kafka/shell/state/MetadataShellState.java | \
    python3 examples/client/match_snippet.py --base-url=$BD_URL --token-file=<(echo $API_TOKEN) --no-verify | \
    jq .

This will produce something like:
{
  "snippetMatches": {
    "PERMISSIVE": [
      {
        "projectName": "Apache Kafka",
        "releaseVersion": "3.5.0",
        "licenseDefinition": {
          "name": "Apache License 2.0",
          "spdxId": "Apache-2.0",
          "ownership": "OPEN_SOURCE",
          "licenseDisplayName": "Apache License 2.0"
. . .
    
'''
import argparse
import json
import logging
import sys

from blackduck import Client

parser = argparse.ArgumentParser('match_snippets.py')
parser.add_argument("--base-url", required=True, help="Hub server URL e.g. https://your.blackduck.url")
parser.add_argument("--token-file", dest='token_file', required=True, help="containing access token")
parser.add_argument("--no-verify", dest='verify', action='store_false', help="disable TLS certificate verification")
parser.add_argument("--input", required=False, help="File containing code snippet or stdin")
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

if args.input:
    with open(args.input, 'r') as content_file:
        content = content_file.read()
else:
    with sys.stdin as content_file:
        content = content_file.read()

endpoint='/api/snippet-matching'
headers = {"Content-Type": "text/plain"}

response = bd.session.post(url=endpoint, headers=headers, data=content)
if response.ok:
    data = response.json()
    import json
    print(json.dumps(data))