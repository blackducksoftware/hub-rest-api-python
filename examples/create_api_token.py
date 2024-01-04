'''
Created on January 1, 2024

@author: dnichol

Create a new user

To use this script. Firstly create a .restconfig.json file with either API token or basic auth (username/password) as per the examples :
https://github.com/blackducksoftware/hub-rest-api-python/blob/master/restconfig.json.example
https://github.com/blackducksoftware/hub-rest-api-python/blob/master/restconfig.json.api_token.example

Then to run:
python create_api_token.py MyToken "My Token Description"

It will output the token that is generated.  If you would like the token to be read only add the -r flag to the command line.

'''
import argparse
import json
import logging
from pprint import pprint
import sys

from blackduck.HubRestApi import HubInstance


parser = argparse.ArgumentParser("Create an API token")
parser.add_argument("name")
parser.add_argument("description")
parser.add_argument("-r", "--readonly", action='store_true')


args = parser.parse_args()

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

hub = HubInstance()

scope = ["read"]

if not args.readonly :
  scope = ["read", "write"]

post_data = {
  "name" : args.name,
  "description" : args.description,
  "scopes" : scope
}

current_user = hub.get_current_user()
add_token_url = hub.get_link(current_user, "api-tokens")

response = hub.execute_post(add_token_url, data=post_data)
if response.status_code == 201:
    token_obj = response.json()
    token=token_obj['token']
    logging.info("Added API token {} = {}".format(args.name, token))
else:
    logging.error("Failed to add API token {}, status code was {}".format(
        args.name, response.status_code))





