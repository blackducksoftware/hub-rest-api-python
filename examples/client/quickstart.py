from blackduck import Client

import argparse
import logging
from pprint import pprint

logging.basicConfig(
    level=logging.DEBUG,
    format="[%(asctime)s] {%(module)s:%(lineno)d} %(levelname)s - %(message)s"
)

parser = argparse.ArgumentParser("Quickstart demonstration with Client")
parser.add_argument("--base-url", required=True, help="Hub server URL e.g. https://your.blackduck.url")
parser.add_argument("--token-file", dest='token_file', required=True, help="containing access token")
parser.add_argument("--no-verify", dest='verify', action='store_false', help="disable TLS certificate verification")
args = parser.parse_args()

with open(args.token_file, 'r') as tf:
    access_token = tf.readline().strip()

bd = Client(
    base_url=args.base_url,
    token=access_token,
    verify=args.verify
)

for project in bd.get_resource('projects'):
    print(f"Project: {project['name']}")
    print("Project list_resources():")
    pprint(bd.list_resources(project))
    for version in bd.get_resource('versions', project):
        print(f"Version: {version['versionName']}")
        for bom_component in bd.get_resource('components', version):
            print(f"BOM component: {bom_component['componentName']}:{bom_component['componentVersionName']}")
        # print(f"Version list_resources():")
        # pprint(bd.list_resources(version))
        # print("Exiting after printing first project and version")
        # quit(0)
