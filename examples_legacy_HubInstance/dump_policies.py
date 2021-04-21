'''
Created on Dec 5, 2018

@author: gsnyder

Dump policies to a file

'''
import argparse
import copy
import json
import logging
from pprint import pprint
import sys

from blackduck.HubRestApi import HubInstance, CreateFailedAlreadyExists


def serialize_to_file(file, data):
	with open(file, "w") as f:
		json.dump(data, f, indent=3)

parser = argparse.ArgumentParser("Dump policies from a Hub instance")
parser.add_argument("base_filename", help="There will be two files dumped - one raw and one prepped to copy policies to another Hub instance")
args = parser.parse_args()

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

source_hub = HubInstance()

policy_keys_to_delete = [
	'_meta', 
	'href', 
	'links', 
	'createdAt', 
	'createdBy',
	'createdByUser',
	'updatedAt', 
	'updatedBy',
	'updatedByUser']

policies_to_copy = source_hub.get_policies()

def fix_policy_expression(policy):
	'''a GET on /api/policy-rules (or /api/policy-rules/{id}) returns a policy object that is valid for use in the GUI app,
	but is not valid to use for creating a new policy directly on another server. We need to adjust the schema, content
	to make it suitable for use in creating new policies (on another server).
	'''
	new_policy = copy.deepcopy(policy)

	for expression in new_policy['expression']['expressions']:
		values = [d["value"] for d in expression['values']]
		parameters = {"values": values}
		expression['parameters'] = parameters
		del expression['values']
	return new_policy

if 'totalCount' in policies_to_copy and policies_to_copy['totalCount'] > 0:
	logging.debug("Dumping {} policies from {}".format(policies_to_copy['totalCount'], source_hub.config['baseurl']))
	assert 'items' in policies_to_copy, "Should always be a list of items in a non-zero list of policies"

	policy_data_raw = []
	policy_data_prepped_to_copy = []

	for policy in policies_to_copy['items']:
		policy = source_hub.get_policy_by_url(policy['_meta']['href'])
		policy_data_raw.append(policy)

		policy_copy_prepped_to_create = policy.copy()

		for k in policy_keys_to_delete:
			if k in policy_copy_prepped_to_create:
				del policy_copy_prepped_to_create[k]

		new_policy = fix_policy_expression(policy_copy_prepped_to_create)

		policy_data_prepped_to_copy.append(new_policy)

	raw_file = args.base_filename + ".raw"
	prepped_file = args.base_filename + ".prepped"

	serialize_to_file(raw_file, policy_data_raw)
	serialize_to_file(prepped_file, policy_data_prepped_to_copy)
else:
	logging.info("No policies to dump")



		