from blackduck import Client

import argparse
import logging
import requests

logging.basicConfig(
    level=logging.DEBUG,
    format="[%(asctime)s] {%(module)s:%(lineno)d} %(levelname)s - %(message)s"
)

parser = argparse.ArgumentParser("Recursively traverse resource endpoints")
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


def iterate_sub_resources(parent, breadcrumb=""):
    try:
        resources = bd.list_resources(parent)
    except TypeError:
        return

    for res in resources:
        print(f"{breadcrumb}->{res}", end='')
        if res in ['scan-data',  # 200; but .bdio output is not json
                   'apiDocumentation',  # 200; but output is just a huge amount of html
                   'detectUri',  # 204; no content
                   ]:
            print("...SKIPPING")
            continue
        print()

        try:
            obj = bd.get_resource(res, parent, items=False)
        except requests.HTTPError:
            continue
        if isinstance(obj, dict):
            print(f"dict with {len(obj.keys())} keys; keys:{obj.keys()}")
        else:
            raise RuntimeError("200 result should always return a dict: " + obj)
        if 'items' in obj:
            items = obj['items']
            if len(items) > 0:
                iterate_sub_resources(items[0], f"{breadcrumb}->{res}")


iterate_sub_resources(None)
