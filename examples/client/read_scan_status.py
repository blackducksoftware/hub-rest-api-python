'''
Created on Mar 7, 2023

@author: kumykov
'''
import argparse
import json
import logging
import sys

from blackduck import Client

parser = argparse.ArgumentParser("Get all the users")
parser.add_argument("--base-url", required=True, help="Hub server URL e.g. https://your.blackduck.url")
parser.add_argument("--token-file", dest='token_file', required=True, help="containing access token")
parser.add_argument("--no-verify", dest='verify', action='store_false', help="disable TLS certificate verification")
args = parser.parse_args()


logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stderr, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("blackduck").setLevel(logging.WARNING)

with open(args.token_file, 'r') as tf:
    access_token = tf.readline().strip()

bd = Client(
    base_url=args.base_url,
    token=access_token,
    verify=args.verify
)

headers = {'Accept': 'application/vnd.blackducksoftware.internal-1+json'}
status = {"in_progress": 0, "completed": 0, "error": 0, "skipped": 0}

for i in status.keys():
    params = {"filter": ["codeLocationStatus:{}".format(i)]}
    codelocations = bd.get_resource('codeLocations', params=params, headers=headers)
    status[i] = sum(1 for _ in codelocations)
    
print (status)

