#!/usr/bin/env python

import argparse
import json
import logging
import sys

from blackduck.HubRestApi import HubInstance, object_id

journal_filters = [
    "journalObjectType", 
    "journalObjectNames", 
    "journalTriggerNames", 
    "journalDate", 
    "journalAction", 
    "journalTriggerType"
]

# A partial list of the journal actions (aka events) we can filter on
# To see a complete list go into the GUI, navigate to the activity page and
# select the Events filter
journal_actions = [
    'component_added',
    'component_deleted',
    'kb_component_deprecated',
    'kb_component_version_deprecated'
]

# Sample invocation
#
#   python examples/get_journal_events.py protex_tutorial -v 1.0 -f journalAction:component_added -f journalAction:component_deleted > journal_comp_adds_deletes.json
#

parser = argparse.ArgumentParser("Retreive journal events for projects or project-versions")
parser.add_argument("project")
parser.add_argument("-v", "--version")
parser.add_argument("-f", "--filter", nargs='+', action='append', help=f"Use the following filter keys to narrow the events returned ({journal_filters}). Specify the filter in the format filterKey:filterValue. ")

# TODO: Add a check on the journalFilterKey:journalFilterValue

args = parser.parse_args()

logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stderr, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

hub = HubInstance()

project_or_version = hub.get_project_by_name(args.project)
journal_url = hub.get_link(project_or_version, "project-journal")
if args.version:
    version = hub.get_project_version_by_name(args.project, args.version)
    version_id = object_id(version)
    journal_url = f"{journal_url}/versions/{version_id}"

if args.filter:
    filter_str = "&filter=".join([f[0] for f in args.filter])
    journal_url = f"{journal_url}?limit=9999&filter={filter_str}"

journal_events = hub.execute_get(journal_url).json()

print(json.dumps(journal_events))
