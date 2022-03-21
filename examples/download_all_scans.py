import argparse
import json
import logging
import sys
from datetime import timedelta
from pprint import pprint

import arrow
from blackduck import Client
from blackduck.Utils import get_resource_name

logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stderr, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("blackduck").setLevel(logging.DEBUG)

def main():
    upstream_copyright_data_file='copyright_data.txt'

    parser = argparse.ArgumentParser("Enumerate BOM componets without copyrigth statements. retrieve copyright statements form upstream channel and/or version")
    parser.add_argument("-u", "--base-url", required=True, help="Hub server URL e.g. https://your.blackduck.url")
    parser.add_argument("-t", "--token-file", dest='token_file', required=True, help="containing access token")
    parser.add_argument("-nv", "--no-verify", dest='verify', action='store_false', help="disable TLS certificate verification")
    parser.add_argument("-o", "--outputdir", dest='outputdir', default='outdir', help="disable TLS certificate verification")
    args = parser.parse_args()

    with open(args.token_file, 'r') as tf:
        access_token = tf.readline().strip()

    global bd
    bd = Client(base_url=args.base_url, token=access_token, verify=args.verify, timeout = 60.0)
    outdir=None
    if args.outputdir:
        outdir = args.outputdir
    import os
    if not os.path.exists(outdir):
        os.mkdir(outdir)
    projects = bd.get_resource('projects')
    for project in projects:
        versions = bd.get_resource('versions',project)
        for version in versions:
            codelocations = bd.get_resource('codelocations', version)
            for codelocation in codelocations:
                resources = bd.list_resources(codelocation)
                url = resources['scan-data']
                filename = url.split('/')[6]
                response = bd.session.get(url, stream=True, verify=False)
                print (response.status_code)
                print (response.ok)
                print (url)
                if response.ok:
                    pathname = os.path.join(outdir, filename)
                    with open(pathname, "wb") as f:
                        for data in response.iter_content():
                            f.write(data)
                    print(f"{filename}, {pathname}")

if __name__ == "__main__":
    sys.exit(main())

