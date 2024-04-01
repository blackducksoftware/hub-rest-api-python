'''
Created on Jan 18, 2024

@author: kumykov

Unmap codelocations from a project version

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
parser.add_argument("project_name")
parser.add_argument("version_name")

args = parser.parse_args()

logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stderr, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("blackduck").setLevel(logging.WARNING)

with open(args.token_file, 'r') as tf:
	access_token = tf.readline().strip()

bd = Client(base_url=args.bd_url, token=access_token, verify=args.verify)

params = {
    'q': [f"name:{args.project_name}"]
}
projects = [p for p in bd.get_resource('projects', params=params) if p['name'] == args.project_name]
assert len(projects) == 1, f"There should be one, and only one project named {args.project_name}. We found {len(projects)}"
project = projects[0]

params = {
    'q': [f"versionName:{args.version_name}"]
}
versions = [v for v in bd.get_resource('versions', project, params=params) if v['versionName'] == args.version_name]
assert len(versions) == 1, f"There should be one, and only one version named {args.version_name}. We found {len(versions)}"
version = versions[0]

logging.debug(f"Found {project['name']}:{version['versionName']}")

codelocations = bd.get_resource('codelocations', version)

for codelocation in codelocations:
	logging.debug(f"Un-mapping code location {codelocation['name']}")
	url = codelocation['_meta']['href']
	codelocation['mappedProjectVersion'] = None
	result = bd.session.put(url, json=codelocation)
	logging.info(f"Code location '{codelocation['name']}' unmap status {result}")