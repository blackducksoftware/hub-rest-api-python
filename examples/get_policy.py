#!/usr/bin/env python

import argparse
from datetime import datetime
import json
import logging
import sys

from blackduck.HubRestApi import HubInstance


parser = argparse.ArgumentParser("Get a policy")
parser.add_argument("name")
parser.add_argument("-p", "--prep", action='store_true', help="Prep the output to be used to (re-)create the policy later, i.e. strip stuff out that is not needed for creation")

args = parser.parse_args()

logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stderr, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

hub = HubInstance()
policies_url = hub.get_apibase() + "/policy-rules"
# policies = hub.get_policies()
policies = hub.execute_get(policies_url).json().get('items', [])

for policy in policies:
    if policy['name'] == args.name:
        if args.prep:
            for attribute in ['createdAt', 'createdBy', 'createdByUser', 'updatedAt', 'updatedBy', 'updatedByUser', '_meta']:
                if attribute in policy:
                    del policy[attribute]
        print(json.dumps(policy))
