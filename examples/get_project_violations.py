'''
Created on Nov 14, 2018

@author: gsnyder

Print a project given its name

'''

from blackduck.HubRestApi import HubInstance

import argparse
import json

parser = argparse.ArgumentParser(description='Use this to check the status of a given version for a given project.  If no version is given then it will return the status of the highest version.')

parser.add_argument("--limit")
parser.add_argument("project_name")
parser.add_argument("--version", default="empty", help="If provided, will result in if that version passed policy check")

args = parser.parse_args()

hub = HubInstance()

status=hub.get_project_violation_status(args.project_name, args.version)
print(status)
if(status == "IN_VIOLATION"):
    exit(0)
elif(status == "NOT_IN_VIOLATION"):
    exit(0)
else:
    exit(0)
