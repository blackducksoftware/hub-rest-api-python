#!/usr/bin/env python


# this script will fetch the list of components in a project version and identify their matching Protex IDs

import argparse
import json
import logging
import sys

from blackduck.HubRestApi import HubInstance, object_id



parser = argparse.ArgumentParser("get the component suite ids in project / version")
parser.add_argument("project")
parser.add_argument("version")

args = parser.parse_args()


logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stderr, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("blackduck").setLevel(logging.WARNING)

hub = HubInstance()
headers = hub.get_headers()
headers['Accept'] = '*/*'

version = hub.get_project_version_by_name(args.project, args.version)

if version:
    components_url = hub.get_link(version, "components") + "?limit=9999"
    components = hub.execute_get(components_url).json().get('items', [])
    logging.debug(f"Found {len(components)} components in {args.project}-{args.version}")
    for component in components:
              component_url = component['_meta']['href']
              #logging.info(f"Component: {component['componentName']} , Version: {component.get('componentVersionName', '?')} URL: {component_url}")
              suite_url =  "{}/{}/".format(component['component'], "legacy-suite-ids")
              suite_json = hub.execute_get(suite_url,custom_headers=headers).json().get('items',[])
              logging.info(f"Component: {component['componentName']} - Protex Ids: {suite_json}")
else:
    logging.error(f"Did not find the project-version: {args.project}-{args.version}")
