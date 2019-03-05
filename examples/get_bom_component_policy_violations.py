#!/usr/bin/env python

import argparse
import json
import logging
import sys


from blackduck.HubRestApi import HubInstance


parser = argparse.ArgumentParser("Retreive BOM components for the given project and version")
parser.add_argument("project_name")
parser.add_argument("version")

args = parser.parse_args()

logging.basicConfig(format='%(asctime)s%(levelname)s:%(message)s', stream=sys.stderr, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

hub = HubInstance()

project = hub.get_project_by_name(args.project_name)
version = hub.get_version_by_name(project, args.version)

bom_components = hub.get_version_components(version)

all_policy_violations = dict()

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