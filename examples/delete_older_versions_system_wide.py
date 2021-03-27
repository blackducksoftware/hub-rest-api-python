'''
Created on Feb 2, 2021

@author: gsnyder

Find and delete older project-versions system-wide based on version age 
excluding versions whose phase is equal to RELEASED (or ARCHIVED)

Copyright (C) 2021 Synopsys, Inc.
http://www.synopsys.com/

Licensed to the Apache Software Foundation (ASF) under one
or more contributor license agreements. See the NOTICE file
distributed with this work for additional information
regarding copyright ownership. The ASF licenses this file
to you under the Apache License, Version 2.0 (the
"License"); you may not use this file except in compliance
with the License. You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
KIND, either express or implied. See the License for the
specific language governing permissions and limitations
under the License.
'''
import argparse
import logging
import sys

from blackduck.HubRestApi import HubInstance

import arrow

excluded_phases_defaults = ['RELEASED', 'ARCHIVED']

parser = argparse.ArgumentParser("Find and delete older project-versions system-wide based on age unless they are marked as RELEASED or ARCHIVED")
# parser.add_argument("project_name")
parser.add_argument("-e", "--excluded_phases", default=excluded_phases_defaults, help=f"Set the phases to exclude from deletion (defaults to {excluded_phases_defaults})")
parser.add_argument("-a", "--age", type=int, help=f"Project-versions older than this age (days) will be deleted unless their phase is in the list of excluded phases ({excluded_phases_defaults})")
parser.add_argument("-d", "--delete", action='store_true', help=f"Because this script can, and will, delete project-versions we require the caller to explicitly ask to delete things. Otherwise, the script runs in a 'test mode' and just says what it would do.")
parser.add_argument("-ncl", "--do_not_delete_code_locations", action='store_true', help=f"By default the script will delete code locations mapped to project versions being deleted.  Pass this flag if you do not want to delete code locations.")
args = parser.parse_args()

logging.basicConfig(format='%(asctime)s:%(levelname)s:%(module)s: %(message)s', stream=sys.stderr, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("blackduck.HubRestApi").setLevel(logging.WARNING)

hub = HubInstance()

projects = hub.get_projects(limit=9999).get('items', [])

logging.warning(f"The default behaviour of this script has changed.  Previously it would not delete mapped code locations while deleting a project version and would rely on these being cleaned up by the system at a later date.")
logging.info(f"If you wish to keep the previous behaviour please pass the -ncl or --do_not_delete_code_locations parameter.")

for project in projects:
	versions = hub.get_project_versions(project, limit=9999)
	sorted_versions = sorted(versions['items'], key = lambda i: i['createdAt'])

	un_released_versions = list(filter(lambda v: v['phase'] not in args.excluded_phases, sorted_versions))
	logging.debug(f"Found {len(un_released_versions)} versions in project {project['name']} which are not in phase RELEASED or ARCHIVED")

	for version in un_released_versions:
		version_age = (arrow.now() - arrow.get(version['createdAt'])).days
		if version_age > args.age:
			if args.delete:
				# TODO: What to do if/when this is the last version in a project to avoid having empty projects being left around
				logging.debug(f"Deleting version {version['versionName']} from project {project['name']} cause it is {version_age} days old which is greater than {args.age} days")
				url = version['_meta']['href']
				if not args.do_not_delete_code_locations:
					logging.debug(f"Deleting code locations for version {version['versionName']} from project {project['name']}")
					hub.delete_project_version_codelocations(version)

				response = hub.execute_delete(url)
				if response.status_code == 204:
					logging.info(f"Successfully deleted version {version['versionName']} from project {project['name']}")
				else:
					logging.error(f"Failed to delete version {version['versionName']} from project {project['name']}. status code {response.status_code}")
			else:
				logging.debug(f"In test-mode. Version {version['versionName']} from project {project['name']} would be deleted cause it is {version_age} days old which is greater than {args.age} days. Use '--delete' to actually delete it.")
		else:
			logging.debug(f"Version {version['versionName']} from project {project['name']} will be retained because it is {version_age} days old which is less or equal to the threshold of {args.age} days")


