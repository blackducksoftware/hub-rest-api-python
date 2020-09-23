'''
Created on Nov 8, 2019

@author: ylei

Delete multiple projects and their scans. The project names to be deleted are kept in clean_project.json
'''

import argparse
import csv
import logging
import sys
import json
import arrow

from blackduck.HubRestApi import HubInstance

parser = argparse.ArgumentParser("A program that will delete projects along with their scans")
#parser.add_argument("project", help="Project name")
parser.add_argument("-f", "--filename", default="clean_project.json", help="File to keep Project names")
parser.add_argument("-k", "--keep_scans", action = 'store_true', default=False, help="Use this option if you want to keep scans associated with the project-versions. Default is False, scans will be deleted.")
parser.add_argument("-b", "--backup_scans", action = 'store_true', default=False, help="Use this option if you want to backup scans associated with the project-versions. Default is False, scans will not be backuped.")
parser.add_argument("-a", "--age", default=3, help="The age, in days. If a project is older than this age it will be deleted.")
args = parser.parse_args()

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

hub = HubInstance()

filename = args.filename
with open(filename, 'r+') as f:
    d = json.load(f)
print("Projects in maintain json file: ", d['clean_project'])
for proj in d['clean_project']:
    now = arrow.now()
    clean_time = now.to('local').shift(days=-int(args.age))
    project = hub.get_project_by_name(proj)
    if not project:
        print("Project", proj, "doesn't exist in server. Skip.")
        continue

    if clean_time > arrow.get(project['createdAt']).to('local'):
        print("Project ", project['name'], ' last for more than 3 days. Will be backup abd deleted.')
        hub.delete_project_by_name(proj, save_scans=args.keep_scans, backup_scans=args.backup_scans)
