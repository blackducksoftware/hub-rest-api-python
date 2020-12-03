#!/usr/bin/env python

import argparse
import json
import logging
import sys

from blackduck.HubRestApi import HubInstance, object_id

usages = [
    'DYNAMICALLY_LINKED',
    'SOURCE_CODE',
    'STATICALLY_LINKED',
    'SEPARATE_WORK',
    'MERELY_AGGREGATED',
    'IMPLEMENTATION_OF_STANDARD',
    'PREREQUISITE',
    'DEV_TOOL_EXCLUDED'
]
parser = argparse.ArgumentParser("Set the Usage for all BOM components in a project version to the specified usage")
parser.add_argument("project")
parser.add_argument("version")
parser.add_argument("new_usage", choices=usages)

args = parser.parse_args()


logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stderr, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("blackduck").setLevel(logging.WARNING)

hub = HubInstance()

version = hub.get_project_version_by_name(args.project, args.version)

if version:
    components_url = hub.get_link(version, "components") + "?limit=9999"
    components = hub.execute_get(components_url).json().get('items', [])
    logging.debug(f"Found {len(components)} components in {args.project}-{args.version}")
    for component in components:
        component_url = component['_meta']['href']
        component['usages'] = [args.new_usage]
        result = hub.execute_put(component_url, data=component)
        # import pdb; pdb.set_trace()
        if result.status_code == 200:
            logging.info(f"Set usage for {component['componentName']}-{component.get('componentVersionName', '?')} to {args.new_usage}")
        else:
            logging.warning(f"Failed to set usage for {component['componentName']}-{component.get('componentVersionName', '?')} to {args.new_usage}. Status code was {result.status_code}")
else:
    logging.error(f"Did not find the project-version: {args.project}-{args.version}")