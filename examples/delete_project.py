'''
Created on March 4, 2019

@author: gsnyder

Delete a project and its scans
'''

import argparse
import csv
import logging
import sys

from blackduck.HubRestApi import HubInstance

parser = argparse.ArgumentParser("A program that will delete a project along with its scans")
parser.add_argument("project", help="Project name")
parser.add_argument("-k", "--keep_scans", action = 'store_true', default=False, help="Use this option if you want to keep scans associated with the project-versions. Default is False, scans will be deleted.")
args = parser.parse_args()

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

hub = HubInstance()

hub.delete_project_by_name(args.project, save_scans=args.keep_scans)