#!/usr/bin/env python

'''
Created on Friday, January 13th, 2023
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

usage: upload_bdio [-h] -u BASE_URL -t TOKEN_FILE [-nv] filename

Uploads BDIO file to a Blackduck server

positional arguments:
  filename              BDIO file to upload

optional arguments:
  -h, --help            show this help message and exit
  -u BASE_URL, --base-url BASE_URL
                        Hub server URL e.g. https://your.blackduck.url
  -t TOKEN_FILE, --token-file TOKEN_FILE
                        File containing access token
  -nv, --no-verify      Disable TLS certificate verification

Blackduck examples collection

'''


import sys
import argparse
import logging

from blackduck import Client

logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stderr, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("blackduck").setLevel(logging.WARNING)


def main():
    args = parse_command_args()
    with open(args.token_file, 'r') as tf:
       access_token = tf.readline().strip()
    global bd
    bd = Client(base_url=args.base_url, token=access_token, verify=args.no_verify, timeout=60.0, retries=4)
    files = {"file": open(args.filename,"rb")}
    response = bd.session.post("/api/scan/data", files = files)
    logging.info(response)
    logging.info(response.headers)

def parse_command_args():
    parser = argparse.ArgumentParser(prog = "upload_bdio", description="Uploads BDIO file to a Blackduck server", epilog="Blackduck examples collection")
    parser.add_argument("filename", help="BDIO file to upload")
    parser.add_argument("-u", "--base-url",     required=True, help="Hub server URL e.g. https://your.blackduck.url")
    parser.add_argument("-t", "--token-file",   required=True, help="File containing access token")
    parser.add_argument("-nv", "--no-verify",     action='store_false', help="Disable TLS certificate verification")
    return parser.parse_args()



if __name__ == "__main__":
        sys.exit(main())
