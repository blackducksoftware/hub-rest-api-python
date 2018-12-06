'''
Created on Dec 5, 2018

@author: gsnyder

Upload policies from a file to a Black Duck server

'''
import argparse
import json
import logging
from pprint import pprint
import sys

from blackduck.HubRestApi import HubInstance, CreateFailedAlreadyExists


parser = argparse.ArgumentParser("Upload policies to a Hub instance from a file")
parser.add_argument("policies_file", help="A json-formatter file containing all the policies")
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

f =  open(args.policies_file, 'r')
policies_to_copy = json.load(f)

if not policies_to_copy:
	logging.debug("No policies to copy, sure you used the right file?")
	
for policy_info in policies_to_copy:
	new_policy_result = {}
	try:
		new_policy_result = dest_hub.create_policy(policy_info)
	except CreateFailedAlreadyExists:
		logging.warning("policy with name {} already exists".format(policy_info['name']))
	except:
		logging.error("Unknown error occurred while attempting to add policy {}".format(
			policy_info['name']), exc_info=True)
	else:
		logging.info("Created new policy, details {}".format(new_policy_result))






		