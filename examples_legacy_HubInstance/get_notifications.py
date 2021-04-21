#!/usr/bin/env python

'''
Created on May 19, 2020

@author: gsnyder

Retrieve notifications (a variant/derivative of get_vulnerability_notifications.py)

Note: The user account you run this under will determine the scope (i.e. projects, versions) of 
the notifications that can be received.

'''

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
#   To get help,
#       python3 examples/get_notifications.py -h
#
#   To get policy rule violation notifications system-wide, since the beginning of "time"
#       python3 examples/get_notifications.py > notifications.json
#
#   To get policy rule notifications system-wide, since a given date/time,
#       python3 examples/get_notifications.py -n "May 17, 2020" > notifications.json
#
#   To get policy rule violations and policy override notifications, since a given date/time,
#       python3 examples/get_notifications.py -n "May 17, 2020" -t RULE_VIOLATION POLICY_OVERRIDE > notifications.json

ALL_NOTIFICATION_TYPES = [
    'RULE_VIOLATION', 
    'RULE_VIOLATION_CLEARED', 
    'POLICY_OVERRIDE', 
    'VULNERABILITY', 
    'PROJECT_VERSION', 
    'PROJECT'
]

parser = argparse.ArgumentParser("Retreive vulnerability notifications")
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
parser.add_argument("-t", "--types", nargs='+', default=['RULE_VIOLATION'], help="A list of notification types you want to retrieve")
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

if args.system:
    notifications_url = "{}/api/notifications".format(hub.get_urlbase())
else:
    notifications_url = hub.get_link(current_user, "notifications")

notifications_url = "{}?limit={}".format(notifications_url, args.limit)

filtered_notifications = []

notifications = hub.execute_get(notifications_url).json().get('items', [])

logging.debug("Total of {} notifications retrieved".format(len(notifications)))
filtered_notifications = list(filter(lambda n: n['type'] in args.types, notifications))
logging.debug("After filtering for notification types ({}) we are left with {} notifications".format(
    args.types, len(filtered_notifications)))

if newer_than:
    logging.debug("Filtering {} notifications to only include those after {}".format(
        len(filtered_notifications), newer_than))
    filtered_notifications = list(
        filter(lambda n: timestring.Date(n['createdAt']) > newer_than, filtered_notifications))
    logging.debug("{} notifications after filtering for those after {}".format(
        len(filtered_notifications), newer_than))

if args.project:
    filtered_notifications = list(
        filter(lambda n: args.project in [apv['projectName'] for apv in n['content']['affectedProjectVersions']], 
            filtered_notifications))
    if args.version:
        filtered_notifications = list(
            filter(lambda n: args.version in [apv['projectVersionName'] for apv in n['content']['affectedProjectVersions']], 
                filtered_notifications))

print(json.dumps(filtered_notifications))

