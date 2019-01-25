'''
Created on Dec 4, 2018

@author: gsnyder

Create a new user_group

'''
import argparse
import json
import logging
from pprint import pprint
import sys

from blackduck.HubRestApi import HubInstance


user_group_types = ['INTERNAL', 'EXTERNAL']

parser = argparse.ArgumentParser("Create a new user_group")
parser.add_argument("usergroupname")
parser.add_argument("--externalGroupName", default=None)
parser.add_argument("--type", choices=user_group_types, default="INTERNAL")
parser.add_argument("--active", default=True)

args = parser.parse_args()

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

hub = HubInstance()

if args.externalGroupName:
	external_group_name = args.externalGroupName
else:
	external_group_name = args.usergroupname

if args.type == 'INTERNAL':
	location = hub.create_user_group({
		'name': args.usergroupname,
		'createdFrom': args.type,
		'active': args.active,
		})
elif args.type == 'EXTERNAL':
	location = hub.create_user_group({
		'name': args.usergroupname,
		'externalName': external_group_name,
		'createdFrom': args.type,
		'active': args.active,
		})
else:
	print("You must choose a valid type {}".format(user_group_types))

logging.info("Created user_group {} at location {}".format(args.usergroupname, location))






