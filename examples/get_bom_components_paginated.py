#!/usr/bin/env python

import argparse
from datetime import datetime
import json
import logging
import sys

from blackduck.HubRestApi import HubInstance

parser = argparse.ArgumentParser("Retreive BOM component info for the given project and version")
parser.add_argument("project_name")
parser.add_argument("version")
group = parser.add_mutually_exclusive_group()
group.add_argument("-u", "--unreviewed", action='store_true')
group.add_argument("-r", "--reviewed", action='store_true')
parser.add_argument("-v", "--vulnerabilities", action='store_true', help="Get the vulnerability info for each of the components")
parser.add_argument("-c", "--custom_fields", action='store_true', help="Get the custom field info for each of the components")
parser.add_argument("-l", "--limit", type=int, default=1000, help="The number of components to return with each call to the REST API (default: 1000)")
parser.add_argument("-t", "--total", type=int, default=99999, help="The total number of components to retrieve")
args = parser.parse_args()

#logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stderr, level=logging.DEBUG)
logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stderr, level=logging.WARNING)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

hub = HubInstance()

project = hub.get_project_by_name(args.project_name)

version = hub.get_version_by_name(project, args.version)

offset = 0
total_hits = 0

custom_headers = {'Accept': 'application/vnd.blackducksoftware.bill-of-materials-6+json'}

#loop to page through  the bom components returns until none left
while total_hits < args.total:
    logging.debug("Retrieving components from offset {}, limit {}".format( offset, args.limit))

    components_url = hub.get_link(version, "components") + "?limit={}&offset={}".format(args.limit,offset)
    logging.debug("URL:{}".format(components_url))

    response = hub.execute_get(components_url, custom_headers=custom_headers)
    if response.status_code == 200:

       results = response.json().get('items', [])

       if results:
          offset += args.limit
          hits = len(results)
          total_hits += hits
          logging.debug("Found {} hits, total hits now {}".format(hits, total_hits))

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

          if args.custom_fields:
              for component in components:
                  custom_fields_url = hub.get_link(component, "custom-fields")
                  response = hub.execute_get(custom_fields_url, custom_headers=custom_headers)
                  custom_fields = []
                  if response.status_code == 200:
                      custom_fields = response.json().get('items', [])
                  component['custom_fields'] = custom_fields

          print(json.dumps(components))

          if hits < args.limit:
             # at the end?
             logging.debug("Looks like we are at the end, breaking loop")
             break
 
