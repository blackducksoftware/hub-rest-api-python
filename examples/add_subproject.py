#!/usr/bin/env python

import http.client
http.client._MAXHEADERS = 1000

import argparse
import copy
from datetime import datetime
import json
import logging
import sys
import timestring

from blackduck.HubRestApi import HubInstance, object_id

parser = argparse.ArgumentParser("Add a sub-project to a project")
parser.add_argument("parent_project")
parser.add_argument("parent_version")
parser.add_argument("sub_project")
parser.add_argument("sub_version")
args = parser.parse_args()

logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stderr, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

hub = HubInstance()

parent_project = hub.get_project_version_by_name(args.parent_project, args.parent_version)
sub_project = hub.get_project_version_by_name(args.sub_project, args.sub_version)

hub.add_version_as_component(parent_project, sub_project)