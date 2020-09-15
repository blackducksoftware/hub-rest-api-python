#!/usr/bin/env python

import argparse
import json

from blackduck.HubRestApi import HubInstance


parser = argparse.ArgumentParser("Get Remediation Info of vulnerable BOM component for the given project and version")
parser.add_argument("project_name")
parser.add_argument("version")

args = parser.parse_args()


hub = HubInstance()

project = hub.get_project_by_name(args.project_name)
version = hub.get_version_by_name(project, args.version)

bom_components = hub.get_vulnerable_bom_components(version)


project_id = project['_meta']['href'].split("/")[-1]
version_id = version['_meta']['href'].split("/")[-1]

all_info = dict()

for bom_component in bom_components['items']:
    component_remediation = get_component_remediation(bom_component)
    component_version_with_no_vulnerability = component_remediation['noVulnerabilities']['name'] \
        if 'noVulnerabilities' in component_remediation else "No Solution Found"
    latest_component_version = component_remediation['latestAfterCurrent']['name'] \
        if 'latestAfterCurrent' in component_remediation else "No Latest version Found"
    all_info.update({"{}, {}".format((bom_component['componentName'], bom_component['componentVersionName'])): {
        "component_version_no_vulnerability": component_version_with_no_vulnerability,
        "latest_component_version": latest_component_version
    }
    })

print(json.dumps(all_info))
