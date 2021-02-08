#!/usr/bin/env python

#
# This script manually adds compnents to an existing project/version.
# The use case is to transfer a BOM from one Black Duck to antoher.  The BOM is read from the JSON
# output of get_bom_components.py.  To avoid changing .restconfig.json when swtiching between
# Black Duck instances, this script takes the Black Duck credentials from the command line.
#
# Example Use case to tansfer a BOM from a source Black Duck to a destination Black Duck.
#   Retrieve BOM for for a project-version on the source Black Duck (.restconfig.json identifies source Black Duck)
#   get_bom_components.py -l <LIMIT> <PROJECT_NAME> <VERSION> > output.json
#
#   If the project-version is not present on the destination Black Duck, create it.
#
#   add_components_to_project_version.py <PROJECT_NAME> <VERSION> output.json <DESTINATION BASE URL> <API_TOKEN>
#       Note: BASE_URL includes https.  For example, https:\\example.blackduck.synopsys.com
#
#


import argparse
import logging
import sys
import json

from blackduck.HubRestApi import HubInstance, object_id

parser = argparse.ArgumentParser("Add components from JSON output of get_bom_components to the selected project-version on the desired Black Duck host")
parser.add_argument("-cp", "--create-project", action="store_true", help="Create project-version if they don't exist")
parser.add_argument("project_name", help="Name of destination project ")
parser.add_argument("version", help="Version of destination project")
parser.add_argument("component_file",help="JSON file with component list from get_bom_components")
parser.add_argument("url_base",help="Base URL of Black Duck host. https://blackduck-hostname")
parser.add_argument("api_token", help="API token for Black Duck host")


args = parser.parse_args()

logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stderr, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

with open(args.component_file) as f:
    components = json.load(f)
f.close()

url_base = args.url_base
api_token = args.api_token

hub = HubInstance(url_base, api_token=api_token, insecure=True, write_config_flag=False)

if (args.create_project):
    project_version = hub.get_or_create_project_version(args.project_name, args.version)
else:
    project_version = hub.get_project_version_by_name(args.project_name, args.version)

if (project_version is None):
    logging.error(f"Project: {args.project_name}, {args.version} does not exist. Create it using --create-project or login to Blackduck.")
    exit(1)

components_api_url = hub.get_link(project_version, "components")

for component in components:
    # Check if the version is known for this component and get the component/version or component URL
    if 'componentVersion' in component:
        component_url = component['componentVersion']
        versionName = component['componentVersionName']
    else:
        component_url = component['component']
        versionName= "?"

    post_data = {"component": component_url}

    response = hub.execute_post(components_api_url, data=post_data)

    if response.status_code == 200:
        logging.info(f"Successfully added {component['componentName']}, {versionName} to project {args.project_name}, {args.version}")
    else:
        logging.error(f"Failed to add {component['componentName']}, {versionName} to project {args.project_name}, {args.version}. Status code: {response.status_code}")
