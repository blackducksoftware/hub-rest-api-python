'''
Created on Nov 14, 2018

@author: gsnyder

Print a project given its name

'''

from blackduck.HubRestApi import HubInstance

import argparse
import json

parser = argparse.ArgumentParser()

parser.add_argument("--limit")
parser.add_argument("project_name")

args = parser.parse_args()

hub = HubInstance()

project = hub.get_project_by_name(args.project_name)

print(json.dumps(project))