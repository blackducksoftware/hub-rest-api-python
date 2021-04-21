'''
Created on Dec 4, 2018

@author: gsnyder

Copy users and their roles from one Hub instance to another

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

parser = argparse.ArgumentParser("Dump users from a Hub instance")
parser.add_argument("base_filename", help="There will be two files dumped - one raw and one prepped to copy users to another Hub instance")
args = parser.parse_args()

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

source_hub = HubInstance()

user_keys_to_delete = ['_meta', 'href', 'links']

users_to_copy = source_hub.get_users()

if 'totalCount' in users_to_copy and users_to_copy['totalCount'] > 0:
	logging.info("Dumping {} users from {}".format(users_to_copy['totalCount'], source_hub.config['baseurl']))
	assert 'items' in users_to_copy, "Should always be a list of items in a non-zero list of users"

	user_data_raw = []
	user_data_prepped_to_copy = []

	for user in users_to_copy['items']:
		if user['userName'] == 'sysadmin':
			continue
		# pprint(user)
		user_roles = source_hub.get_roles_for_user_or_group(user)

		user_data_raw.append({
			'user': user, 'roles': user_roles
			})

		user_copy_prepped_to_create = user.copy()
		for k in user_keys_to_delete:
			if k in user_copy_prepped_to_create:
				del user_copy_prepped_to_create[k]

		# Need to add a password value to get Hub to create the user even
		# for EXTERNAL users
		if 'password' not in user_copy_prepped_to_create:
			user_copy_prepped_to_create['password'] = 'blackduck'

		user_roles_to_create = [role['name'] for role in user_roles['items']]

		user_data_prepped_to_copy.append({
			'user': user_copy_prepped_to_create, 'roles': user_roles_to_create
			})

	raw_file = args.base_filename + ".raw"
	prepped_file = args.base_filename + ".prepped"

	serialize_to_file(raw_file, user_data_raw)
	serialize_to_file(prepped_file, user_data_prepped_to_copy)
else:
	logging.info("No users to dump")


		