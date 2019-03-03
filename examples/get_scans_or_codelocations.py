'''
Created on February 6, 2019

@author: gsnyder

Get all the scans (aka code locations)

'''

import argparse
import json
from pprint import pprint

from blackduck.HubRestApi import HubInstance

parser = argparse.ArgumentParser("Retrieve scans (aka code locations) from the Black Duck system")
parser.add_argument("--name", type=str, default=None, help="Filter by name")
parser.add_argument("--unmapped", action='store_true', help="Set this to see any scans (aka code locations) that are not mapped to any project-version")

args = parser.parse_args()

hub = HubInstance()

if args.name:
	parameters={'q':'name:{}'.format(args.name)}
else:
	parameters={}

if args.unmapped:
	scans = hub.get_codelocations(limit=10000, unmapped=True, parameters=parameters)
else:
	scans = hub.get_codelocations(limit=10000, parameters=parameters)

print(json.dumps(scans))