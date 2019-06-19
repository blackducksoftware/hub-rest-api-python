#!/usr/bin/env python

import argparse
from datetime import datetime
import json
import logging
import sys
import timestring

from blackduck.HubRestApi import HubInstance

parser = argparse.ArgumentParser("Retreive BOM component info for the given project and version")
parser.add_argument("project_name")
parser.add_argument("version")
group = parser.add_mutually_exclusive_group()
group.add_argument("-u", "--unreviewed", action='store_true')
group.add_argument("-r", "--reviewed", action='store_true')
parser.add_argument("-v", "--vulnerabilities", action='store_true', help="Get the vulnerability info for each of the components")

args = parser.parse_args()

logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stderr, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

hub = HubInstance()

project = hub.get_project_by_name(args.project_name)

version = hub.get_version_by_name(project, args.version)

components_url = hub.get_link(version, "components")

response = hub.execute_get(components_url)
if response.status_code == 200:
    components = response.json()
    components = components.get('items', [])

    if args.reviewed or args.unreviewed:
        filter_to = 'REVIEWED' if args.reviewed else 'NOT_REVIEWED'

        components = list(filter(lambda c: c['reviewStatus'] == filter_to, components))

    if args.vulnerabilities:
        for component in components:
            vulnerabilities_url = hub.get_link(component, "vulnerabilities")
            response = hub.execute_get(vulnerabilities_url)
            vulnerabilities = []
            if response.status_code == 200:
                vulnerabilities = response.json().get('items', [])
            component['vulnerabilities'] = vulnerabilities
    print(json.dumps(components))