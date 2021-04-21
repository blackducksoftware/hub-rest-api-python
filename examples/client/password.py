from blackduck import Client
from blackduck.Client import HubSession
from blackduck.Authentication import CookieAuth

import argparse
import logging
from pprint import pprint

logging.basicConfig(
    level=logging.DEBUG,
    format="[%(asctime)s] {%(module)s:%(lineno)d} %(levelname)s - %(message)s"
)

parser = argparse.ArgumentParser("Authenticate using username/password credentials")
parser.add_argument("--base-url", required=True, help="Hub server URL e.g. https://your.blackduck.url")
parser.add_argument("--username", required=True, help="Hub user")
parser.add_argument("--password", required=True, help="Hub user")
parser.add_argument("--no-verify", dest='verify', action='store_false', help="disable TLS certificate verification")
args = parser.parse_args()

base_url = args.base_url
session = HubSession(base_url, timeout=15.0, retries=3, verify=args.verify)
auth = CookieAuth(session, args.username, args.password)

bd = Client(base_url=base_url, session=session, auth=auth)

pprint(bd.list_resources())
