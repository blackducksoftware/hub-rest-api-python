'''
Created on Dec 4, 2018

@author: gsnyder

Upload user groups from a file to a Black Duck server

'''
import argparse
import json
import logging
from pprint import pprint
import sys

from blackduck.HubRestApi import HubInstance, CreateFailedAlreadyExists


parser = argparse.ArgumentParser("Upload user_groups to a Hub instance from a file")
parser.add_argument("user_groups_file", help="A json-formatter file containing all the user_group data, including their roles")
parser.add_argument("dest_url", help="The URL for the destination Hub instance")
parser.add_argument("dest_username", default="sysadmin", help="The destination user account - default: sysadmin")
parser.add_argument("dest_password", default="blackduck")

args = parser.parse_args()

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

dest_hub = HubInstance(
	args.dest_url, 
	args.dest_username,
	args.dest_password,
	write_config_flag=False,
	insecure=True)

f =  open(args.user_groups_file, 'r')
user_groups_to_copy = json.load(f)

if not user_groups_to_copy:
	logging.debug("No user_groups to copy, sure you used the right file?")
	
def get_user_group(dest_hub, user_group_copy):
	# filtering did not appear to work so doing it on the app side
	user_groups = dest_hub.get_user_groups()
	if 'totalCount' in user_groups and user_groups['totalCount'] > 0:
		assert 'items' in user_groups, "Should always be an items list when totalCount > 0"

		for user_group in user_groups['items']:
			if user_group['name'] == user_group_copy['name']:
				return user_group
	return None

for user_group_info in user_groups_to_copy:
	assert 'user_group' in user_group_info, "There must be a user_group object in each record"
	assert 'roles' in user_group_info, "There must be a list of role names in each record"

	user_group_copy = user_group_info['user_group']
	role_names = user_group_info['roles']

	new_user_group_result = {}
	try:
		new_user_group_result = dest_hub.create_user_group(user_group_copy)
	except CreateFailedAlreadyExists:
		logging.warning("user_group with name {} already exists".format(user_group_copy['name']))
	except:
		logging.error("Unknown error occurred while attempting to add user_group {}".format(
			user_group_copy['name']), exc_info=True)
	else:
		logging.info("Created new user_group, details {}".format(new_user_group_result))

	# We need a copy of the newly (or recently) created user group
	new_user_group = get_user_group(dest_hub, user_group_copy)

	if not role_names:
		logging.debug("No roles to assign to user_group {}".format(user_group_copy['name']))
	else:
		logging.debug('Assigning user_group roles {} to new user_group {} on hub at {}'.format(
			role_names, user_group_copy['name'], dest_hub.get_urlbase()))

	for role in role_names:
		try:
			add_role_response = dest_hub.assign_role_to_user_or_group(role, new_user_group)
		except:
			logging.error("Failed to assign role {} to user_group {}".format(
				role, user_group_copy['name']), exc_info=True)
		else:
			if add_role_response.status_code == 201:
				logging.info("Added role {} to user_group {}".format(role, user_group_copy['name']))
			else:
				logging.error("Failed to add role {} to user_group {}, details {}".format(
					role, user_group_copy['name'], add_role_response.json()))
	# TODO: v3 returns different info than v4+ so need to work out what to do here
	# new_user_info = dest_hub.get_user_by_url(new_user_url)
	# logging.debug("New user data: {}".format(new_user_info))





		