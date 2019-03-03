'''
Created on Dec 5, 2018

@author: gsnyder

Dump user groups to a file

'''
import argparse
import json
import logging
from pprint import pprint
import sys

from blackduck.HubRestApi import HubInstance, CreateFailedAlreadyExists


def serialize_to_file(file, data):
	with open(file, "w") as f:
		json.dump(data, f, indent=3)

parser = argparse.ArgumentParser("Dump user_groups from a Hub instance")
parser.add_argument("base_filename", help="There will be two files dumped - one raw and one prepped to copy user_groups to another Hub instance")
args = parser.parse_args()

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

source_hub = HubInstance()

user_group_keys_to_delete = ['_meta', 'href', 'links']

user_groups_to_copy = source_hub.get_user_groups()

if 'totalCount' in user_groups_to_copy and user_groups_to_copy['totalCount'] > 0:
	logging.debug("Dumping {} user_groups from {}".format(user_groups_to_copy['totalCount'], source_hub.config['baseurl']))
	assert 'items' in user_groups_to_copy, "Should always be a list of items in a non-zero list of user_groups"

	user_group_data_raw = []
	user_group_data_prepped_to_copy = []

	for user_group in user_groups_to_copy['items']:
		user_group_roles = source_hub.get_roles_for_user_or_group(user_group)

		user_group_data_raw.append({
			'user_group': user_group, 'roles': user_group_roles
			})

		user_group_copy_prepped_to_create = user_group.copy()
		for k in user_group_keys_to_delete:
			if k in user_group_copy_prepped_to_create:
				del user_group_copy_prepped_to_create[k]

		user_group_roles_to_create = [role['name'] for role in user_group_roles['items']]

		user_group_data_prepped_to_copy.append({
			'user_group': user_group_copy_prepped_to_create, 'roles': user_group_roles_to_create
			})

	raw_file = args.base_filename + ".raw"
	prepped_file = args.base_filename + ".prepped"

	serialize_to_file(raw_file, user_group_data_raw)
	serialize_to_file(prepped_file, user_group_data_prepped_to_copy)
else:
	logging.info("No user groups to dump")



		