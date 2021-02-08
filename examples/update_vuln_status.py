#!/usr/bin/env python

import http.client
# http.client._MAXHEADERS = 1000

import argparse
import copy
from datetime import datetime
import json
import logging
import sys
import timestring

from blackduck.HubRestApi import HubInstance, object_id

parser = argparse.ArgumentParser("Update vulnerability remediation status for a given vulnerability either using the default status or a user-supplied status")
parser.add_argument("vulnerability", help="e.g. CVE-2020-8488")
parser.add_argument("project", help="The project to apply the updates to")
parser.add_argument("version", help="The version within the project to apply the updates to")

sub_parsers = parser.add_subparsers(help="Update modes")

use_default_parser = sub_parsers.add_parser("use_default")
user_supplied_parser = sub_parsers.add_parser("user_supplied")

user_supplied_parser.add_argument(
    "status", 
    choices=['new', 'review', 'required', 'complete', 'mitigated', 'patched', 'ignored', 'duplicate'])
user_supplied_parser.add_argument("comment")

args = parser.parse_args()

if args.version and not args.project:
    raise RuntimeError("You must specify a project with (-p, --project) with the version option")

logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stderr, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

hub = HubInstance()

project = hub.get_project_by_name(args.project)

version = hub.get_version_by_name(project, args.version)

vulnerable_components_url = hub.get_link(version, "vulnerable-components") + "?limit=9999"
custom_headers = {'Accept':'application/vnd.blackducksoftware.bill-of-materials-6+json'}
response = hub.execute_get(vulnerable_components_url, custom_headers=custom_headers)
vulnerable_bom_components = response.json().get('items', [])

status_keyword_lookup = {
    "review": "NEEDS_REVIEW",
    "required": "REMEDIATION_REQUIRED",
    "complete": "REMEDIATION_COMPLETE",
    "mitigated": "MITIGATED",
    "patched": "PATCHED",
    "ignored": "IGNORED",
    "duplicate": "DUPLICATE",
}

if hasattr(args, "status"):
    # user supplied status
    status = status_keyword_lookup[args.status]
    comment = args.comment
else:
    default_remediation_status_url = hub.get_apibase() + f"/vulnerabilities/{args.vulnerability}/default-remediation-status"
    default_remediation_status = hub.execute_get(default_remediation_status_url).json()
    status = default_remediation_status['remediationStatus']
    comment = default_remediation_status['comment']

for i, vuln in enumerate(vulnerable_bom_components):
    vuln_name = vuln['vulnerabilityWithRemediation']['vulnerabilityName']

    if vuln_name == args.vulnerability:
        vuln['remediationStatus'] = status
        vuln['comment'] = comment
        logging.debug(f"Updating vuln {args.vulnerability} in project {project['name']}, version {version['versionName']} using URL {vuln['_meta']['href']} with status {status} and comment {comment}")
        result = hub.execute_put(vuln['_meta']['href'], data=vuln)
        
        if result.status_code == 202:
            logging.info(f"Successfully updated vuln {args.vulnerability} in project {project['name']}, version {version['versionName']} with status {status} and comment {comment}")
        else:
            logging.error(f"Failed to update vuln {args.vulnerability} in project {project['name']}, version {version['versionName']}; http status code: {result.status_code}")

