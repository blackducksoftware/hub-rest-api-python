#!/usr/bin/env python

import argparse
import json
import logging
import sys
from pprint import pprint

from blackduck.HubRestApi import HubInstance, object_id

parser = argparse.ArgumentParser("Retrieve snippet match counts for a given project-version")
parser.add_argument("project_name")
parser.add_argument("version")

args = parser.parse_args()

logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stderr, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

hub = HubInstance()

version = hub.get_project_version_by_name(args.project_name, args.version)

snippet_counts_url = version['_meta']['href'] + "/snippet-counts"

snippet_counts = hub.execute_get(snippet_counts_url).json()

del snippet_counts['_meta']

print("Snippet count info for project {}, version {}:".format(args.project_name, args.version))
pprint(snippet_counts)