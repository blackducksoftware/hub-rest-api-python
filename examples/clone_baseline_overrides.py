#!/usr/bin/env python

import argparse
import arrow
import json
import logging
import sys

from blackduck.HubRestApi import HubInstance, object_id

def get_policy_status_comment(policy_status):
    '''Return the most recent policy status comment
    '''
    comments = list()
    for view in policy_status.get('policyRuleViolationViews', []):
        for record in view.get('updatedBy', []):
            comments.append((record['comment'], arrow.get(record['updatedAt'])))
    comments = sorted(comments, key=lambda c: c[1])
    return comments[-1]

def components_with_overrides(hub_instance, version):
    # components_url = hub_instance.get_link(version, "components") + "?limit=999"
    # components = hub_instance.execute_get(components_url).json().get('items', [])
    components = hub_instance.get_version_components(version, limit=999).get('items', [])
    have_overrides = [c for c in components if c['policyStatus'] == 'IN_VIOLATION_OVERRIDDEN']
    # need to retrieve override comments
    for component in have_overrides:
        policy_status_url = hub_instance.get_link(component, "policy-status")
        # Note: The public endpoint/media type does NOT return the override comment 
        #   shown in the GUI. So, using a private internal media type, below, which allows retrieval 
        #   of the comment info. 
        #   Ref: <blackduck_url>/api-doc/public.html#policy-status-representation
        #
        # Warning: Use of an internal media type is not supported. What does this mean?
        #   It can break on a future release of Black Duck so this script will
        #   need to be re-tested for each future version of Black Duck. And, if it fails,
        #   it will need to be reworked accordingly
        custom_headers = {'Accept':'application/vnd.blackducksoftware.internal-1+json'}
        policy_status = hub_instance.execute_get(policy_status_url, custom_headers=custom_headers).json()
        comment, comment_dt = get_policy_status_comment(policy_status)
        component['comment'] = comment
        component['comment_dt'] = comment_dt
    return have_overrides

def clone_policy_status(hub_instance, version, component_overrides):
    overrides_by_name = {f"{c['componentName']}:{c['componentVersionName']}":c for c in component_overrides}
    components = hub_instance.get_version_components(version, limit = 999).get('items', [])
    for component in components:
        cn = f"{component['componentName']}:{component['componentVersionName']}"
        override = overrides_by_name.get(cn)
        if override:
            policy_status_url = hub_instance.get_link(component, "policy-status")
            # TODO: use comment_dt from override or accept the dt for when we cloned?
            data = {
                'approvalStatus': override['policyStatus'],
                'comment': override['comment'],
            }
            response = hub_instance.execute_put(policy_status_url, data=data)
            if response.status_code == 202:
                logging.info(f"Cloned override to {cn} in version {version['versionName']}")
            else:
                logging.error(f"Failed to clone overide to {cn} in version {version['versionName']}")
        else:
            logging.debug(f"{cn} not in overrides to clone")


def clone_overrides(hub_instance, project, baseline_version_name):
    versions = hub_instance.get_project_versions(project).get('items', [])
    version_names = ",".join([v['versionName'] for v in versions])
    assert baseline_version_name in version_names, "The baseline version must exist in the project"

    logging.debug(f"Cloning overrides from version '{baseline_version_name}' to the other versions ({version_names}) in project {project['name']}")
    baseline_version = next(v for v in versions if v['versionName'] == baseline_version_name)
    overrides_to_clone = components_with_overrides(hub_instance, baseline_version)
    versions_to_clone_to = [v for v in versions if v['versionName'] != baseline_version_name]
    for version in versions_to_clone_to:
        clone_policy_status(hub_instance, version, overrides_to_clone)

parser = argparse.ArgumentParser("Clone component everrides from a baseline version to all other versions in the project")
parser.add_argument("-p", "--project", help="Specify a project to do the override cloning on (default is to clone overrides in all projects)")
parser.add_argument("-b", "--baseline_version", default="baseline", help="The name of the baseline version from which to clone overrides")
args = parser.parse_args()


logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stderr, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("blackduck").setLevel(logging.WARNING)

hub = HubInstance()

if args.project:
    projects = [hub.get_project_by_name(args.project)]
else:
    projects = hub.get_projects(limit=999).get('items', [])

for project in projects:
    clone_overrides(hub, project, args.baseline_version)

