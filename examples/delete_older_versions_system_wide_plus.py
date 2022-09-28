'''
Created on Sep 14, 2022

@author: mkoishi

Find and delete older versions and additionally delete unmapped codelocations, empty versions and empty projects.

Copyright (C) 2022 Synopsys, Inc.
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
import json
import traceback
from requests import HTTPError, RequestException

from blackduck import Client

import arrow

excluded_phases_defaults = ['RELEASED', 'ARCHIVED']
delete_longer_age = ['PRERELEASE']

program_description = \
'''Find and delete older versions and additionally delete unmapped codelocations, empty versions and empty projects.

Find and delete older project-versions system-wide based on version age excluding versions whose phase is equal to RELEASED or ARCHIVED.
Excluded phases can be overwritten by parameters.
Threshold version age is 30 days for PRE-RELEASE phase or 14 days for other phases. Threshold version ages can be overwritten by parameters.
Codelocations are deleted if mapped version is deleted by age unless 'do_not_delete_code_locations' parameter is given. 
Versions with no codelocations and components are deleted unless its phase is equal to RELEASED or ARCHIVED.
Projects which are destined to be empty because of deleting the last version of the project are also deleted.

USAGE:
API Toekn and hub URL need to be placed in the .restconfig.json file
    {
      "baseurl": "https://hub-hostname",
      "api_token": "<API token goes here>",
      "insecure": true,
      "debug": false
    }
'''

class VersionCounter:
    '''Manage version counter for project. This is used for Test Mode and simulates totalCount of version in project.
       Since actual version deletions never occur in Test Mode, we are unable to rely on the totalCount.
    '''
    def __init__(self):
        self.version_counter = 0

    def decrese_version_counter(self):
        self.version_counter -= 1

    def read_version_counter(self):
        return self.version_counter

    def reset_version_counter(self, version_number):
        self.version_counter = version_number

number_of_projects = 0
number_of_deleted_projects = 0
number_of_failed_to_delete_projects = 0
number_of_versions = 0
number_of_deleted_versions = 0
number_of_failed_to_delete_versions = 0
number_of_deleted_codelocations = 0
number_of_failed_to_delete_codelocations = 0
version_counter = VersionCounter()

def log_config():
    # TODO: debug option in .restconfig file to be reflected
    logging.basicConfig(format='%(asctime)s:%(levelname)s:%(module)s: %(message)s', stream=sys.stderr, level=logging.DEBUG)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("blackduck").setLevel(logging.WARNING)

def parse_parameter():
    parser = argparse.ArgumentParser(description=program_description, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("-e", 
                        "--excluded_phases",
                        nargs='+',
                        default=excluded_phases_defaults, 
                        help=f"Set the phases to exclude from deletion (defaults to {excluded_phases_defaults})")
    parser.add_argument("-al",
                        "--age_longer",
                        type=int,
                        default=30,
                        help=f"Project-versions older than this age (days) with {delete_longer_age} phase will be deleted unless their phase is in the list of excluded phases {excluded_phases_defaults}. Default is 30 days")
    parser.add_argument("-as",
                        "--age_shorter",
                        type=int,
                        default=14,
                        help=f"Project-versions older than this age (days) with other than {delete_longer_age} phase will be deleted unless their phase is in the list of excluded phases {excluded_phases_defaults}. Default is 14 days")
    parser.add_argument("-d",
                        "--delete",
                        action='store_true',
                        help=f"Because this script can, and will, delete project-versions we require the caller to explicitly "
                              "ask to delete things. Otherwise, the script runs in a 'test mode' and just says what it would do.")
    parser.add_argument("-ncl",
                        "--do_not_delete_code_locations",
                        action='store_true',
                        help=f"By default the script will delete code locations mapped to project versions being deleted. "
                              "Pass this flag if you do not want to delete code locations.")
    parser.add_argument("-t",
                        "--timeout",
                        type=int,
                        default=15,
                        help=f"Timeout for REST-API. Some API may take longer than the default 15 seconds")
    parser.add_argument("-r",
                        "--retries",
                        type=int,
                        default=3,
                        help=f"Retries for REST-API. Some API may need more retries than the default 3 times")
    return parser.parse_args()

def traverse_projects_versions(hub_client, args):
    global number_of_projects
    global number_of_versions

    # TODO: Wish to have get_resource('projects') and get_resource('versions') retry for HTTP failure
    for project in hub_client.get_resource('projects'):
        versions = []
        # It must receive and collect all versions from the returned generator to next coming sort and filtering
        for ver in hub_client.get_resource('versions', project):
            number_of_versions += 1
            versions.append(ver)

        sorted_versions = sorted(versions, key = lambda i: i['createdAt'])
        un_released_versions = list(filter(lambda v: v['phase'] not in args.excluded_phases, sorted_versions))
        excluded = ' or '.join(args.excluded_phases)
        logging.debug(f"Found {len(un_released_versions)} versions in project {project['name']} which are not in phase {excluded}")

        if not args.delete:
            version_number = hub_client.get_metadata('versions', project)['totalCount']
            version_counter.reset_version_counter(version_number)

        for version in un_released_versions:
            delete_aged_version(hub_client, args, project, version)

        number_of_projects += 1

    print_report(args)

def delete_aged_version(hub_client, args, project, version):
    global number_of_deleted_projects
    global number_of_deleted_versions
    global number_of_failed_to_delete_versions
    global number_of_deleted_codelocations

    version_age = (arrow.now() - arrow.get(version['createdAt'])).days
    age = args.age_longer if version['phase'] in delete_longer_age else args.age_shorter

    if version_age > age:
        if args.delete:
            logging.debug(f"Deleting version {version['versionName']} with phase {version['phase']} from project {project['name']} because it is {version_age} days old which is greater than {age} days")
        else:
            logging.info(f"In test-mode. Version {version['versionName']} with phase {version['phase']} from project {project['name']} would be deleted because it is {version_age} days old which is greater than {age} days. Use '--delete' to actually delete it.")
        if not args.do_not_delete_code_locations:
            if args.delete:
                logging.debug(f"Deleting code locations for version {version['versionName']} from project {project['name']}")
            else:
                logging.info(f"In test-mode. Codelocations for version {version['versionName']} from project {project['name']} would be deleted.")
            delete_version_codelocations(hub_client, args, version)
        delete_version(hub_client, args, project, version)
    elif is_version_empty(hub_client, version):
        if args.delete:
            logging.debug(f"Deleting version {version['versionName']} with phase {version['phase']} from project {project['name']} because it is empty version")
        else:
            logging.info(f"In test-mode. Version {version['versionName']} with phase {version['phase']} from project {project['name']} would be deleted because it is empty. Use '--delete' to actually delete it.")
        delete_version(hub_client, args, project, version)

def delete_version(hub_client, args, project, version):
    global number_of_deleted_versions
    global number_of_failed_to_delete_versions

    try:
        if is_last_version_of_project(hub_client, args, project):
            delete_empty_project(hub_client, args, project)
            return
        if args.delete:
            url = version['_meta']['href']
            response = hub_client.session.delete(url)
            if response.status_code == 204:
                logging.info(f"Successfully deleted version {version['versionName']} with phase {version['phase']} from project {project['name']}")
                number_of_deleted_versions += 1
            else:
                logging.error(f"Failed to delete version {version['versionName']} from project {project['name']}. status code {response.status_code}")
                number_of_failed_to_delete_versions += 1
        else:
            version_counter.decrese_version_counter()
            number_of_deleted_versions += 1
    # We continue if the raised exception is about REST request
    except RequestException as err:
        logging.error(f"Failed to delete version {version['versionName']}. Reason is " + str(err))
        number_of_failed_to_delete_versions += 1
    except Exception as err:
        raise err

def is_last_version_of_project(hub_client, args, project):
    try:
        if args.delete:
            versions = hub_client.get_metadata('versions', project)
            if versions['totalCount'] == 1:
                return True
        else:
            if version_counter.read_version_counter() == 1:
                return True
    except RequestException as err:
        logging.error(f"Failed to get versions data from project {project['name']}. Reason is " + str(err))
    except Exception as err:
        raise err

    return False

def is_version_empty(hub_client, version):
    try:
        components = hub_client.get_metadata('components', version)
        codelocations = hub_client.get_metadata('codelocations', version)
        if components['totalCount'] == 0 and codelocations['totalCount'] == 0:
            return True
    except RequestException as err:
        logging.error(f"Failed to get components and codelocations data from {version['versionName']}. Reason is " + str(err))
    except Exception as err:
        raise err

    return False

def delete_empty_project(hub_client, args, project):
    global number_of_deleted_projects
    global number_of_failed_to_delete_projects
    global number_of_deleted_versions
    global number_of_failed_to_delete_versions

    try:
        if args.delete:
            url = project['_meta']['href']
            response = hub_client.session.delete(url)
            if response.status_code == 204:
                number_of_deleted_projects += 1
                number_of_deleted_versions += 1
                logging.info(f"Successfully deleted empty project {project['name']}")
            else:
                logging.error(f"Failed to delete empty project {project['name']}. status code {response.status_code}")
                number_of_failed_to_delete_projects += 1
                number_of_failed_to_delete_versions += 1
        else:
            logging.info(f"In test-mode. project {project['name']} would be deleted because it is empty project")
            number_of_deleted_projects += 1
            number_of_deleted_versions += 1
    # We continue if the raised exception is about REST request
    except RequestException as err:
        logging.error(f"Failed to delete project {project['name']}. Reason is " + str(err))
        number_of_failed_to_delete_projects += 1
        number_of_failed_to_delete_versions += 1
    except Exception as err:
        raise err

def delete_version_codelocations(hub_client, args, version):
    global number_of_deleted_codelocations
    global number_of_failed_to_delete_codelocations
    
    try:
        codelocations = hub_client.get_resource('codelocations', version)
        for codelocation in codelocations:
            if args.delete:
                response = hub_client.session.delete(codelocation['_meta']['href'])
                if response.status_code == 204:
                    logging.info(f"Successfully deleted codelocation {codelocation['name']} from version {version['versionName']}")
                    number_of_deleted_codelocations += 1
                else:
                    logging.error(f"Failed to delete codelocation {codelocation['name']} from version {version['versionName']}. status code {response.status_code}")
                    number_of_failed_to_delete_codelocations += 1
            else:
                number_of_deleted_codelocations += 1
    # We continue if the raised exception is about REST request
    except (RequestException) as err:
        logging.error(f"Failed to delete codelocation from version {version['versionName']}. Reason is " + str(err))
        number_of_failed_to_delete_codelocations += 1
    except Exception as err:
        raise err

def print_report(args):
    logging.info(f"General Statistics Report")
    if not args.delete:
        logging.info(f"This is the test mode")
    logging.info(f"Total number of projects: {number_of_projects}")
    logging.info(f"Total number of deleted projects: {number_of_deleted_projects}")
    logging.info(f"Total number of failed to delete projects: {number_of_failed_to_delete_projects}")
    logging.info(f"Total number of versions: {number_of_versions}")
    logging.info(f"Total number of deleted_versions: {number_of_deleted_versions}")
    logging.info(f"Total number of failed to delete versions: {number_of_failed_to_delete_versions}")
    logging.info(f"Total number of deleted_codelocations: {number_of_deleted_codelocations}")
    logging.info(f"Total number of failed to delete codelocations: {number_of_failed_to_delete_codelocations}")

def main():
    log_config()
    args = parse_parameter()
    try:
        with open('.restconfig.json','r') as f:
            config = json.load(f)
        hub_client = Client(token=config['api_token'],
                            base_url=config['baseurl'],
                            verify=not config['insecure'],
                            timeout=args.timeout,
                            retries=args.retries)
        
        traverse_projects_versions(hub_client, args)
    except HTTPError as err:
        hub_client.http_error_handler(err)
    except Exception as err:
        logging.error(f"Failed to perform the task. See the stack trace")
        traceback.print_exc()

if __name__ == '__main__':
    sys.exit(main())