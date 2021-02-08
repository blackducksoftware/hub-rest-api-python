#!/usr/bin/env python

import argparse
import json
import logging
import sys

from blackduck.HubRestApi import HubInstance

parser = argparse.ArgumentParser("Retreive a list of un-matched files for the given project and version")
parser.add_argument("project_name")
parser.add_argument("version")

args = parser.parse_args()

logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stderr, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

hub = HubInstance()

version = hub.get_project_version_by_name(args.project_name, args.version)

matched_files_url = version['_meta']['href'] + "/matched-files?limit=99999&filter=bomMatchType:unmatched"

unmatched_files = hub.execute_get(matched_files_url).json().get('items', [])

print(json.dumps(unmatched_files))