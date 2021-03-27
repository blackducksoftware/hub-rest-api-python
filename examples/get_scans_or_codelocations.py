'''
Created on February 6, 2019

@author: gsnyder

Get all the scans (aka code locations)

'''

import argparse
import json
import logging
from pprint import pprint
import sys

from blackduck.HubRestApi import HubInstance, object_id

parser = argparse.ArgumentParser("Retrieve scans (aka code locations) from the Black Duck system")
parser.add_argument("-n", "--name", type=str, default=None, help="Filter by name")
parser.add_argument("--unmapped", action='store_true', help="Set this to see any scans (aka code locations) that are not mapped to any project-version")
parser.add_argument("-s", "--scan_summaries", action='store_true', help="Set this option to include scan summaries")
parser.add_argument("-d", "--scan_details", action='store_true')

args = parser.parse_args()

logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stderr, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

hub = HubInstance()

if args.name:
	parameters={'q':'name:{}'.format(args.name)}
else:
	parameters={}

if args.unmapped:
	code_locations = hub.get_codelocations(limit=10000, unmapped=True, parameters=parameters)
else:
	code_locations = hub.get_codelocations(limit=10000, parameters=parameters)

# code_locations = code_locations.get('items', [])

if args.scan_summaries:
    for code_location in code_locations:
        scan_summaries = hub.get_codelocation_scan_summaries(code_location_obj=code_location).get('items', [])
        code_location['scan_summaries'] = scan_summaries
        if args.scan_details:
            for scan in scan_summaries:
                scan_id = object_id(scan)
                # This uses a private API endpoint that can, and probably will, break in the future
                # HUB-15330 is the (internal) JIRA ticket # asking that the information in this endpoint
                # be made part of the public API
                url = hub.get_apibase() + "/v1/scans/{}".format(scan_id)
                scan_details = hub.execute_get(url).json()
                scan['scan_details'] = scan_details

print(json.dumps(code_locations))