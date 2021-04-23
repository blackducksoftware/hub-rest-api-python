#!/usr/bin/env python

import argparse
import json
import logging
import math
import sys
import urllib
from blackduck.HubRestApi import HubInstance

parser = argparse.ArgumentParser("Retrieve the source files - matched, unmatched, all - for a given project and version")
parser.add_argument("project_name")
parser.add_argument("version")
parser.add_argument("-l", "--limit", type=int, default=100, help="Set the limit on the amount of matches to retrieve per call to the server")

args = parser.parse_args()

logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stderr, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

hub = HubInstance()

version = hub.get_project_version_by_name(args.project_name, args.version)

if not version:
    raise Exception(f"Did not find {args.version} in project {args.project_name}")
    
everything = {'all_files': []}
base_url = version['_meta']['href'] + "/matched-files"

keys_and_parms = {
    'matched_files': {},
    'un_matched_files': {'filter':'bomMatchType:unmatched'}
}

for key, parameters in keys_and_parms.items():
    num_results_found = math.inf
    first = True
    offset = 0

    while offset < num_results_found:
        parameters.update({
            'limit': args.limit,
            'offset': offset
            })
        parameter_string = "&".join([f"{k}={urllib.parse.quote(str(v))}" for k,v in parameters.items()])
        url = base_url + f"?{parameter_string}"
        results = hub.execute_get(url).json()

        if first:
            first = False
            num_results_found = results['totalCount']

        if key in everything:
            everything[key].extend(results.get('items', []))
        else:
            everything[key] = results.get('items', [])

        offset += args.limit

    # Extend the list of all_files to include all the files in the set just created
    everything['all_files'].extend(everything[key].copy())

print(json.dumps(everything))
