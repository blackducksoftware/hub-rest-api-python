'''
Created on Dec 4, 2018

@author: gsnyder

Upload users from a file to a Black Duck server

'''
import argparse
import json
import logging
from pprint import pprint
import sys

from blackduck.HubRestApi import HubInstance, CreateFailedAlreadyExists


parser = argparse.ArgumentParser("Upload users to a Hub instance from a file")
parser.add_argument("users_file", help="A json-formatter file containing all the user data, including their roles")
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

f =  open(args.users_file, 'r')
users_to_copy = json.load(f)

if not users_to_copy:
	logging.debug("No users to copy, sure you used the right file?")
	
def get_user(dest_hub, user_copy):
	parameters = {'q':'userName:{}'.format(user_copy['userName'])}
	users = dest_hub.get_users(parameters=parameters)
	if 'totalCount' in users and users['totalCount'] > 0:
		assert 'items' in users, "Should always be an items list when totalCount > 0"

		for user in users['items']:
			if user['userName'] == user_copy['userName']:
				return user
	return None

for user_info in users_to_copy:
	assert 'user' in user_info, "There must be a user object in each record"
	assert 'roles' in user_info, "There must be a list of role names in each record"

	user_copy = user_info['user']
	role_names = user_info['roles']

	new_user_url = None
	try:
		new_user_url = dest_hub.create_user(user_copy)
	except CreateFailedAlreadyExists:
		logging.warning("user with userName {} already exists".format(user_copy['userName']))
	except:
		logging.error("Unknown error occurred while attempting to add user {}".format(
			user_copy['userName']), exc_info=True)
	else:
		logging.info("Created new user at location {}".format(new_user_url))


	if new_user_url:
		new_user = dest_hub.get_user_by_url(new_user_url)
	else:
		new_user = get_user(dest_hub, user_copy)

	if not role_names:
		logging.debug("No roles to assign to user {}".format(user_copy['userName']))
	else:
		logging.debug('Assigning user roles {} to new user {} on hub at {}'.format(
			role_names, new_user['userName'], dest_hub.get_urlbase()))

	for role in role_names:
		try:
			dest_hub.assign_role_to_user_or_group(role, new_user)
		except:
			logging.error("Failed to assign role {} to user {}".format(
				role, new_user['userName']), exc_info=True)
		else:
			logging.info("Added role {} to user {}".format(role, new_user['userName']))
	# TODO: v3 returns different info than v4+ so need to work out what to do here
	# new_user_info = dest_hub.get_user_by_url(new_user_url)
	# logging.debug("New user data: {}".format(new_user_info))





		