#!/usr/bin/env python

import argparse
import json
import logging
import sys

from blackduck.HubRestApi import HubInstance, object_id

parser = argparse.ArgumentParser("Override (or undo) BOM component policy violations")
parser.add_argument("project")
parser.add_argument("-v", "--version", help="The version within the project to apply the override (or undo) to. If not supplied, the override (or undo) will be applied to all versions in the project")
parser.add_argument("component", help="The name of the BOM component")
parser.add_argument("component_version", help="The BOM component version")
parser.add_argument("comment")
parser.add_argument("-u", "--undo_override", action='store_true', help="Undo the override")
args = parser.parse_args()


logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stderr, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("blackduck").setLevel(logging.WARNING)

hub = HubInstance()

if args.version:
    project_versions = [hub.get_project_version_by_name(args.project, args.version)]
else:
    project = hub.get_project_by_name(args.project)
    project_versions = hub.get_project_versions(project).get('items')

for pv in project_versions:
    components_url = hub.get_link(pv, "components")
    components_url = f"{components_url}?q=componentOrVersionName:{args.component}"
    components = hub.execute_get(components_url).json().get('items', [])

    if components:
        # find the version we want (note: the query parm above will do an OR, not an AND)
        # if there is more than one term supplied so doing this in two steps to make sure 
        # we don't get a different, wrong component that shares the same version
        components = list(filter(lambda c: c['componentVersionName'] == args.component_version, components))

        assert len(components) in [0,1], f"Should find 0 or 1 BOM components but instead we found {len(components)}, hmmm, wasn't expecting that"

        component = components[0] if components else None
        if component:
            policy_status_url = hub.get_link(component, "policy-status")
            policy_status = hub.execute_get(policy_status_url).json()
            override = policy_status and policy_status['approvalStatus'] == 'IN_VIOLATION' and not args.undo_override
            undo = policy_status and policy_status['approvalStatus'] == 'IN_VIOLATION_OVERRIDDEN' and args.undo_override
            overridden = undone = False
            if override:
                #override
                data = {
                    'approvalStatus': 'IN_VIOLATION_OVERRIDDEN',
                    'comment': args.comment}
                response = hub.execute_put(policy_status_url, data=data)
                if response.status_code == 202:
                    logging.info(f"Policy violations for {args.component}:{args.component_version} have been overridden in project {args.project}, version {pv['versionName']}")
                    overridden = True
                else:
                    logging.error(f"Failed to override policy violations for {args.component}:{args.component_version}, status_code {response.status_code}")
            elif undo:
                #undo override
                data = {
                    'approvalStatus': 'IN_VIOLATION',
                    'comment': args.comment}
                response = hub.execute_put(policy_status_url, data=data)
                if response.status_code == 202:
                    logging.info(f"Undid override for {args.component}:{args.component_version} have been overridden")
                    undone = True
                else:
                    logging.error(f"Failed to override policy violations for {args.component}:{args.component_version}, status_code {response.status_code}")

            policy_status = hub.execute_get(policy_status_url).json()
            if overridden or undone:
                logging.debug(f"After updating policy status is {policy_status['approvalStatus']}")
            else:
                logging.debug(f"No update applied, policy status is {policy_status['approvalStatus']}")
        else:
            logging.info(f"Did not find BOM component {args.component}:{args.component_version} in project {args.project}, version {pv['versionName']}")
    else:
        logging.info(f"Did not find BOM component {args.component}:{args.component_version} in project {args.project}, version {pv['versionName']}")





