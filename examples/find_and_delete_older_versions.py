'''
Created on January 30, 2019

@author: gsnyder

Find and delete older project-versions
'''
import argparse
import logging
import sys

from blackduck.HubRestApi import HubInstance

parser = argparse.ArgumentParser("Find and delete older project-versions")
parser.add_argument("project_name")
parser.add_argument("num_versions_to_keep", 
	type=int, 
	help="Give the number of (newest) versions to keep. Any versions above this number will be deleted.")
parser.add_argument("--preserve_scans", 
	action='store_true', 
	help='Set this option to preserve the scans associated with the versions being deleted. Default is False, so we will cleanup the scans as well')

args = parser.parse_args()

logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stdout, level=logging.DEBUG)

hub = HubInstance()

project = hub.get_project_by_name(args.project_name)

if project:
	versions = hub.get_project_versions(project, limit=9999)
	sorted_versions = sorted(versions['items'], key = lambda i: i['createdAt'])
	logging.debug("Found and sorted {} versions for project {}".format(
		len(sorted_versions), args.project_name))
	if len(sorted_versions) > args.num_versions_to_keep:
		versions_to_delete = sorted_versions[:-args.num_versions_to_keep]

		version_names_being_deleted = [v['versionName'] for v in versions_to_delete]
		logging.debug("Deleting versions {}".format(version_names_being_deleted))

		for version_to_delete in versions_to_delete:
			hub.delete_project_version_by_name(args.project_name, version_to_delete['versionName'])
			logging.info("Deleted version {}".format(version_to_delete['versionName']))
	else:
		logging.debug("Found {} versions which is not greater than the number to keep {}".format(
			len(sorted_versions), args.num_versions_to_keep))
else:
	logging.debug("No project found with the name {}".format(args.project_name))