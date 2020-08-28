#!/usr/bin/env python

import argparse
import json
import logging
import sys

from blackduck.HubRestApi import HubInstance


parser = argparse.ArgumentParser("Retrieve licenses from the Black Duck KB")
parser.add_argument("-k", "--keyword", help="Find licenses whose name include the keyword (case-insensitive)")
parser.add_argument("-l", "--limit", type=int, help="Set a limit on the number of licenses to retrieve (default: 10)")

args = parser.parse_args()

logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stderr, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

hub = HubInstance()

parameters = {}

if args.keyword:
    parameters.update({"q": f"name:{args.keyword}"})

if args.limit:
    parameters.update({"limit": args.limit})

logging.debug(f"Retrieving licenses using parameters={parameters}")
licenses = hub.get_licenses(parameters=parameters).get('items', [])

logging.debug(f"Found {len(licenses)} licenses")

for license in licenses:
    logging.debug(f"Retrieving license text, terms, and obligations info for license \"{license['name']}\"")
    text_url = hub.get_link(license, "text")
    license['text'] = hub.execute_get(text_url).json().get('text')

    terms_url = hub.get_link(license, 'license-terms')
    license['terms'] = hub.execute_get(terms_url).json().get('items', [])

    obligations_url = hub.get_link(license, 'license-obligations')
    license['obligations'] = hub.execute_get(obligations_url).json().get('items', [])

print(json.dumps(licenses))
