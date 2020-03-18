#!/usr/bin/env python

import argparse
import json
import logging
import sys


from blackduck.HubRestApi import HubInstance


def check_minimum(value):
    minimum = 1800
    ivalue = int(value)
    if ivalue < minimum:
        raise argparse.ArgumentTypeError("Timeout value must be greater than or equal to {} (seconds). You gave {}".format(
            minimum, ivalue))
    return ivalue

parser = argparse.ArgumentParser("Set the user session timeout - applies to both local and SSO authenticated sessions")
parser.add_argument("timeout", type=check_minimum, help="The (integer) timeout value in seconds")
args = parser.parse_args()

logging.basicConfig(format='%(asctime)s%(levelname)s:%(message)s', stream=sys.stderr, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

hub = HubInstance()

url = hub.get_apibase() + "/system-oauth-client"

new_timeout = {
    "accessTokenValiditySeconds": args.timeout
}

response = hub.execute_put(url, data=new_timeout)
print("Result code for attempting to set session timeout to {} seconds was: {}".format(
    args.timeout, response.status_code))