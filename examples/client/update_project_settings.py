'''
Created on Jan 18, 2024

@author: kumykov

Update project settings script.

This script will modify project settings accessible via API

Parameter list and their default values:
    "customSignatureEnabled" : false,
    "customSignatureDepth" : "5",
    "unmatchedFileRetentionEnabled" : false,

'''

from blackduck import Client

import argparse
import json
import logging
import sys
import time
from pprint import pprint

logging.basicConfig(
    level=logging.DEBUG,
    format="[%(asctime)s] {%(module)s:%(lineno)d} %(levelname)s - %(message)s"
)

parser = argparse.ArgumentParser(sys.argv[0])
parser.add_argument("-u", "--bd-url", help="Hub server URL e.g. https://your.blackduck.url")
parser.add_argument("-t", "--token-file", help="File name of a file containing access token")
parser.add_argument("-nv", '--no-verify', dest='verify', action='store_false', help="disable TLS certificate verification")
parser.add_argument("-cse", '--custom-signature-enabled', dest='cs_enable', action='store_true', help="enable custom signature flag")
parser.add_argument("-csd", '--custom-signature-depth', dest='cs_depth', required=False, default="5", help="set custom signature depth")
parser.add_argument("-ruf", '--retain-unmatched-files', dest='retain_uf', action='store_true', help="set retain unmatched files flag")
parser.add_argument("project_name")

args = parser.parse_args()

logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stderr, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("blackduck").setLevel(logging.WARNING)

with open(args.token_file, 'r') as tf:
	access_token = tf.readline().strip()

bd = Client(base_url=args.bd_url, token=access_token, verify=args.verify)
pprint (args.project_name)
params = {
    'q': [f"name:{args.project_name}"]
}
projects = [p for p in bd.get_resource('projects', params=params) if p['name'] == args.project_name]
assert len(projects) == 1, f"There should be one, and only one project named {args.project_name}. We found {len(projects)}"
project = projects[0]

url = project['_meta']['href']
project['customSignatureEnabled'] = args.cs_enable
project['customSignatureDepth'] = args.cs_depth
project['unmatchedFileRetentionEnabled'] = args.retain_uf

response = bd.session.put(url, json=project)
logging.info(f"Project setting update status {response}")