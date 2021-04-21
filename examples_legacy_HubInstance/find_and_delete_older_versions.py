'''
Created on January 30, 2019

@author: gsnyder

Find and delete older project-versions, unless their phase is equal to RELEASED or ARCHIVED
'''
import argparse
import logging
import sys

from blackduck.HubRestApi import HubInstance

parser = argparse.ArgumentParser("Find and delete older project-versions unless they are marked as RELEASED or ARCHIVED")
parser.add_argument("project_name")
parser.add_argument("num_versions_to_keep", 
	type=int, 
	help="Give the number of (newest, Non-RELEASED) versions to keep.")

args = parser.parse_args()

logging.basicConfig(format='%(asctime)s:%(levelname)s:%(module)s: %(message)s', stream=sys.stderr, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("blackduck.HubRestApi").setLevel(logging.WARNING)

hub = HubInstance()

project = hub.get_project_by_name(args.project_name)

if project:
	versions = hub.get_project_versions(project, limit=9999)
	sorted_versions = sorted(versions['items'], key = lambda i: i['createdAt'])

	# un_released_versions = list(filter(lambda v: v['phase'] not in  ['RELEASED'], sorted_versions))
	# logging.debug(f"Found {len(un_released_versions)} versions which are not in phase RELEASED of which we will keep only {args.num_versions_to_keep}")

	un_released_versions = list(filter(lambda v: v['phase'] not in  ['RELEASED', 'ARCHIVED'], sorted_versions))
	logging.debug(f"Found {len(un_released_versions)} versions which are not in phase RELEASED or ARCHIVED of which we will keep only {args.num_versions_to_keep}")

	if len(un_released_versions) > args.num_versions_to_keep:
		versions_to_delete = un_released_versions[:-args.num_versions_to_keep]

		version_names_being_deleted = [v['versionName'] for v in versions_to_delete]
		logging.info("Deleting (the oldest) non-RELEASED versions: {}".format(version_names_being_deleted))

		for version_to_delete in versions_to_delete:
			hub.delete_project_version_by_name(args.project_name, version_to_delete['versionName'])
			logging.info("Deleted version {}".format(version_to_delete['versionName']))
	else:
		logging.info("Found {} (non-RELEASED) versions which is not greater than the number to keep {}".format(
			len(un_released_versions), args.num_versions_to_keep))
else:
	logging.debug("No project found with the name {}".format(args.project_name))