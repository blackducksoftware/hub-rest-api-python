'''
Created on Nov 13, 2018

@author: gsnyder

Given a project name, a version name, delete the project-version and any scans associated with it

'''
from blackduck.HubRestApi import HubInstance
import logging
import sys

import argparse

parser = argparse.ArgumentParser()
parser.add_argument("project_name")
parser.add_argument("version_name")
parser.add_argument("-s", "--save_scans", action='store_true', help="Set this option to preserve the scans mapped to this project version")

args = parser.parse_args()

logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stderr, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

hub = HubInstance()

hub.delete_project_version_by_name(args.project_name, args.version_name, save_scans=args.save_scans)