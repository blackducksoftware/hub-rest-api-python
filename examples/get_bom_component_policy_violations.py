#!/usr/bin/env python

import argparse
import json
import logging
import sys


from blackduck.HubRestApi import HubInstance


parser = argparse.ArgumentParser("Retreive BOM components for the given project and version by giving project/version names OR using a version URL")
mutually_xgroup = parser.add_mutually_exclusive_group()
mutually_xgroup.add_argument("-p", "--project_name")
mutually_xgroup.add_argument("-u", "--url")
parser.add_argument("-v", "--version", required="-p" in sys.argv or "--project_name" in sys.argv)

args = parser.parse_args()

logging.basicConfig(format='%(asctime)s%(levelname)s:%(message)s', stream=sys.stderr, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

hub = HubInstance()

if args.url:
    project_url = "/".join(args.url.split("/")[:-2])
    project = hub.execute_get(project_url).json()
    version = hub.execute_get(args.url).json()
else:
    project = hub.get_project_by_name(args.project_name)
    version = hub.get_version_by_name(project, args.version)

if project and version:
    bom_components = hub.get_version_components(version)
else:
    sys.exit()

all_policy_violations = dict()

all_policy_violations.update({'project': project, 'version': version})

for bom_component in bom_components.get('items'):
    if bom_component.get('policyStatus') == "IN_VIOLATION":
        policy_rules_url = hub.get_link(bom_component, "policy-rules")
        try:
            response = hub.execute_get(policy_rules_url)
            policies = response.json()
        except:
            logging.error("Unable to retrieve policies for BOM component {}".format(
                bom_component), exc_info=True)
        else:
            component_name = bom_component['componentName']
            component_version_name = bom_component['componentVersionName']
            all_policy_violations.update({
                    "{}:{}".format(component_name, component_version_name): {
                        "bom_component": bom_component,
                        "policies_in_violation": policies
                    }
                })


print(json.dumps(all_policy_violations))