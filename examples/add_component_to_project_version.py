#!/usr/bin/env python

import argparse
import logging
import sys

from blackduck.HubRestApi import HubInstance, object_id


parser = argparse.ArgumentParser("Add a Black Duck component to the selected project-version")
parser.add_argument("project_name")
parser.add_argument("version")
parser.add_argument("component_version_url", help="Supply the URL to the component-version")

args = parser.parse_args()

logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stderr, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

hub = HubInstance()

project_version = hub.get_project_version_by_name(args.project_name, args.version)

components_url = hub.get_link(project_version, "components")
post_data = {"component": args.component_version_url}

response = hub.execute_post(components_url, data=post_data)

if response.status_code == 200:
    logging.info(f"Successfully added component to project {args.project_name}, version {args.version}")
else:
    logging.error(f"Failed to add component to project {args.project_name}, version {args.version}. Status code returned was {response.status_code}")
