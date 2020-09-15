#!/usr/bin/env python

'''
Created on Feb 21, 2020

@author: gsnyder

Retrieve BOM computed notifications

Note: The user account you run this under will determine the scope (i.e. projects, versions) of 
the notifications that can be received.

'''

# TODO: Use startDate filter on /api/notifications to limit the notifications retrieved when using -n

import argparse
from datetime import datetime
import json
import logging
import pytz
import sys
import timestring

from terminaltables import AsciiTable

from blackduck.HubRestApi import HubInstance, object_id


parser = argparse.ArgumentParser("Retreive BOM computed notifications")
parser.add_argument("project", help="The name of the project")
parser.add_argument("version", help="The name of the version")
parser.add_argument("-n", "--newer_than", 
    default=None, 
    type=str,
    help="Set this option to see all vulnerability notifications published since the given date/time.")
parser.add_argument("-d", "--save_dt", 
    action='store_true', 
    help="If set, the date/time will be saved to a file named '.last_run' in the current directory which can be used later with the -n option to see vulnerabilities published since the last run.")
parser.add_argument("-l", "--limit", default=100000, help="To change the limit on the number of notifications to retrieve")
parser.add_argument("-s", "--system", action='store_true', help="Pull notifications from the system as opposed to the user's account")
args = parser.parse_args()

if args.newer_than:
    newer_than = timestring.Date(args.newer_than).date
    # adjust to UTC so the comparison is normalized
    newer_than = newer_than.astimezone(pytz.utc)
else:
    newer_than = None

if args.save_dt:
    with open(".last_run", "w") as f:
        f.write(datetime.now().isoformat())

logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stderr, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

hub = HubInstance()
current_user = hub.get_current_user()
version = hub.get_project_version_by_name(args.project, args.version)
version_url = version['_meta']['href']

# Construct the URL to either pull from the system or user account scope,
# and then narrow the search to only include BOM computed notifications
if args.system:
    notifications_url = "{}/api/notifications".format(hub.get_urlbase())
else:
    notifications_url = hub.get_link(current_user, "notifications")

notifications_url = "{}?limit={}&filter=notificationType:VERSION_BOM_CODE_LOCATION_BOM_COMPUTED".format(
    notifications_url, args.limit)

if newer_than:
    # add to the URL to include startDate
    start_date = newer_than.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    notifications_url += "&startDate=" + start_date

logging.debug(f"Retrieving BOM computed notifications using {notifications_url}")
bom_computed_notifications = hub.execute_get(notifications_url).json().get('items', [])

# filter to include only those notification pertaining to the specified project, version
bom_computed_notifications = list(
    filter(lambda n: version_url == n['content']['projectVersion'], bom_computed_notifications))

print(json.dumps(bom_computed_notifications))
