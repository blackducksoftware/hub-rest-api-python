#!/usr/bin/env python

# updates 'usage' for a list of components on a given project and version.  Component list file must be one component per line

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


def readComponentList(compFile):
    compList = []
    try:
        fp = open(compFile, 'r')
        line =  fp.readline()
        while line:
              compList.append(line.strip() )
              line = fp.readline()
        fp.close()
    except:
         logging.error(f"Could not open component list file: {compFile}")
         sys.exit(-1)

     
    return compList



parser = argparse.ArgumentParser("Set the Usage for a component list read from file in a project version to the specified usage")
parser.add_argument("project")
parser.add_argument("version")
parser.add_argument("new_usage", choices=usages)
parser.add_argument("component_list_file")

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
    change_comps = readComponentList(args.component_list_file)
    for change in change_comps:
       for component in components:
           if change == component['componentName']:
              #logging.info(f"Change component: {change} matches {component['componentName']}")
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
