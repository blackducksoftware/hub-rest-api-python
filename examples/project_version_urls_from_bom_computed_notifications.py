#!/usr/bin/env python

import argparse
import logging
import json
import sys

parser = argparse.ArgumentParser("Process the JSON output from get_bom_component_policy_violations.py to create a FIX IT message that guides the project team how to resolve the issues identified through policy rule violations")
parser.add_argument("-f", "--policy_violations_file", help="By default, program reads JSON doc from stdin, but you can alternatively give a file name")
parser.add_argument("-o", "--output_file", help="By default, the fix it message is written to stdout. Use this option to instead write to a file")

args = parser.parse_args()

logging.basicConfig(format='%(asctime)s%(levelname)s:%(message)s', stream=sys.stderr, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

bom_computed_notifications = json.load(sys.stdin)
bom_computed_notifications = sorted(bom_computed_notifications, key=lambda n: n['createdAt'])

for bom_computed_notification in bom_computed_notifications:
    project_version_url = bom_computed_notification['content']['projectVersion']
    # created_at = bom_computed_notification['createdAt']
    print(project_version_url)