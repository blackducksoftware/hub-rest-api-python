#!/usr/bin/env python

import argparse
import json
import logging
import sys

from blackduck.HubRestApi import HubInstance, object_id

parser = argparse.ArgumentParser("Retrieve components that have snippet matches")
parser.add_argument("project_name")
parser.add_argument("version")
parser.add_argument("-u", "--unconfirmed", action='store_true', help="Use this option to list all the components have un-confirmed snippet matches. Without this option only components with confirmed snippet matches will be included.")

args = parser.parse_args()

logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stderr, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

hub = HubInstance()

version = hub.get_project_version_by_name(args.project_name, args.version)

project_id = version['_meta']['href'].split("/")[-3]
version_id = object_id(version)

url = version['_meta']['href'] + "/components?filter=bomMatchType:snippet"
if args.unconfirmed:
    url = url + "&filter=bomMatchReviewStatus:not_reviewed"

response = hub.execute_get(url)

components = response.json().get('items', [])

for component in components:
    matched_files_url = hub.get_link(component, "matched-files")
    response = hub.execute_get(matched_files_url)
    component['matched-files'] = response.json().get('items', [])

print(json.dumps(components))