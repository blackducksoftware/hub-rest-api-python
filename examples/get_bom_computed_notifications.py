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

#
# Example usage:
#
#   To get all the vulnerability notices,
#       python examples/get_vulnerability_notifications.py > all_vuln_notifications.json
#
#   To get all the vulnerability notices and save the date/time of the last run,
#       python examples/get_vulnerability_notifications.py -s > all_vuln_notifications.json
#
#   To get all the vulnerability notices since the last run,
#       python examples/get_vulnerability_notifications.py -n `cat .last_run` > all_vuln_notifications.json
#
#   To get all the vulnerability notices since a date/time,
#       python examples/get_vulnerability_notifications.py -n "March 29, 2019 12:00" > since_mar_29_at_noon_vuln_notifications.json
#
#   To get all the vulnerability notices for a given project,
#       python examples/get_vulnerability_notifications.py -p my-project > all_vuln_notifications_for_my_project.json
#
#   To get all the vulnerability notices for a given project and version,
#       python examples/get_vulnerability_notifications.py -p my-project -v 1.0 > all_vuln_notifications_for_my_project_v1.0.json
#
#


parser = argparse.ArgumentParser("Retreive BOM computed notifications")
parser.add_argument("-p", "--project", help="If supplied, filter the notifications to this project")
parser.add_argument("-v", "--version", help="If supplied, filter the notifications to this version (requires a project)")
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

# Construct the URL to either pull from the system or user account scope,
# and then narrow the search to only include BOM computed
if args.system:
    notifications_url = "{}/api/notifications".format(hub.get_urlbase())
else:
    notifications_url = hub.get_link(current_user, "notifications")

notifications_url = "{}?limit={}&filter=notificationType:VERSION_BOM_CODE_LOCATION_BOM_COMPUTED".format(
    notifications_url, args.limit)

if newer_than:
    start_date = newer_than.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    notifications_url += "&startDate=" + start_date

bom_computed_notifications = hub.execute_get(notifications_url).json().get('items', [])

# if newer_than:
#     bom_computed_notifications = list(
#         filter(lambda n: timestring.Date(n['createdAt']) > newer_than, bom_computed_notifications))
if args.project:
    bom_computed_notifications = list(
        filter(lambda n: args.project in [apv['projectName'] for apv in n['content']['affectedProjectVersions']], 
            bom_computed_notifications))
    if args.version:
        bom_computed_notifications = list(
            filter(lambda n: args.version in [apv['projectVersionName'] for apv in n['content']['affectedProjectVersions']], 
                bom_computed_notifications))

print(json.dumps(bom_computed_notifications))
