
import argparse
import json
import logging
import sys

from blackduck.HubRestApi import HubInstance

parser = argparse.ArgumentParser("Create a policy")
parser.add_argument("policy_file_name")

# Use something like,
#		python examples/get_policy.py "policy-name" -p > policy.json
# to create the json file needed to provide as input to this program
#
args = parser.parse_args()

logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stderr, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

hub = HubInstance()

policy_data = None
with open(args.policy_file_name) as f:
	policy_data = json.load(f)
result = hub.create_policy(policy_data)

print(result)