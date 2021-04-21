from blackduck import Client

import argparse
import logging
from pprint import pprint

logging.basicConfig(
    level=logging.DEBUG,
    format="[%(asctime)s] {%(module)s:%(lineno)d} %(levelname)s - %(message)s"
)

parser = argparse.ArgumentParser("Get a specific component and list its vulnerabilities")
parser.add_argument("--base-url", required=True, help="Hub server URL e.g. https://your.blackduck.url")
parser.add_argument("--token-file", dest='token_file', required=True, help="containing access token")
parser.add_argument("--no-verify", dest='verify', action='store_false', help="disable TLS certificate verification")
args = parser.parse_args()

with open(args.token_file, 'r') as tf:
    access_token = tf.readline().strip()

bd = Client(base_url=args.base_url, token=access_token, verify=args.verify)

params = {
    'q': ["maven:commons-beanutils:commons-beanutils:1.9.3"]
}
search_results = bd.get_items("/api/components", params=params)
for result in search_results:
    pprint(result)
    print(f"{result['componentName']} {result['versionName']}")
    url = result['version']
    component_version = bd.get_json(url)

    for vulnerability in bd.get_resource('vulnerabilities', component_version):
        print(vulnerability['name'])
