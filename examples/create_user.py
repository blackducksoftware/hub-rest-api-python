'''
Created on April 23, 2019

@author: gsnyder

Create a new user

'''
import argparse
import json
import logging
from pprint import pprint
import sys

from blackduck.HubRestApi import HubInstance


parser = argparse.ArgumentParser("Create a new user")
parser.add_argument("user_name")
parser.add_argument("first_name")
parser.add_argument("last_name")
parser.add_argument("email")
parser.add_argument("password")
parser.add_argument("-d", "--disable", action='store_true')


args = parser.parse_args()

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

hub = HubInstance()

data = {
  "userName" : args.user_name,
  "firstName" : args.first_name,
  "lastName" : args.last_name,
  "email" : args.email,
  "active" : not args.disable,
  "password" : args.password
}

hub.create_user(data)





