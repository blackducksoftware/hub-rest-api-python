

import argparse
import json
import logging
import sys


from blackduck.HubRestApi import HubInstance


parser = argparse.ArgumentParser()
parser.add_argument("project_name")
parser.add_argument("application_id")
parser.add_argument("--overwrite", default = False, action='store_true', help="If overwrite is set will over write the current application id with the new one")

args = parser.parse_args()

hub = HubInstance()

# TODO: Debug overwrite, keep getting 412 response on PUT

response = hub.assign_project_application_id(args.project_name, args.application_id, overwrite=args.overwrite)

if response and response.status_code == 201:
	logging.info("successfully assigned application id {} to project {}".format(args.application_id, args.project_name))
else:
	logging.warning("Failed to assign application id {} to project {}".format(args.application_id, args.project_name))