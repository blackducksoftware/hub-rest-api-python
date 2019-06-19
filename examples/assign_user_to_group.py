'''
Created on April 23, 2019

@author: gsnyder

Assign a user to a user group

'''
import argparse
import json
import logging
from pprint import pprint
import sys

from blackduck.HubRestApi import HubInstance


parser = argparse.ArgumentParser("Create a new user")
parser.add_argument("user")
parser.add_argument("user_group")

args = parser.parse_args()

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

hub = HubInstance()

parameters={"q":"userName:{}".format(args.user)}

users = hub.get_users(parameters=parameters).get('items', [])

if users and len(users) == 1:
    user_obj = users[0]
    user_group_obj = hub.get_user_group_by_name(args.user_group)
    if user_group_obj:
        add_user_url = hub.get_link(user_group_obj, "users")
        post_data = [{"user": user_obj['_meta']['href']}]
        response = hub.execute_post(add_user_url, data=post_data)
        if response.status_code == 204:
            logging.info("Added user {} to user group {}".format(args.user, args.user_group))
        else:
            logging.error("Failed to add user {} to user group {}, status code was {}".format(
                args.user, args.user_group, response.status_code))
    else:
        logging.debug("did not find user group object for user group = {}".format(args.user_group))
else:
    logging.debug("Could not find user object with username = {}".format(args.user))






