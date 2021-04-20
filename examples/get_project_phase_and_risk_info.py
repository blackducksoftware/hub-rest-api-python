import argparse
import csv
import glob
import json
import logging
import os
import shutil
import requests
import sys
import time
import timeit

import pandas
from pandas.errors import EmptyDataError

from blackduck.HubRestApi import HubInstance

parser = argparse.ArgumentParser(
    "Get last scan date, project phase, license risk, operational risk and vulnerability counts for a given project version ")
parser.add_argument("project")
parser.add_argument("version")
parser.add_argument('-v', '--verbose', action='store_true', default=False, help='turn on DEBUG logging')

args = parser.parse_args()


def set_logging_level(log_level):
    logging.basicConfig(stream=sys.stderr, level=log_level)


if args.verbose:
    set_logging_level(logging.DEBUG)
else:
    set_logging_level(logging.INFO)

projname = args.project
hub = HubInstance()
rootDir = os.getcwd()

def get_info():
    project = hub.get_project_by_name(args.project)
    version = hub.get_version_by_name(project, args.version)
    phase_and_risk_info = {}

    # get last scan date for project version
    code_location_url = hub.get_link(version, "codelocations")
    response = hub.execute_get(code_location_url)
    if response.status_code in [200, 201]:
        code_location_info = response.json().get('items', [])
        if code_location_info:
            updated_at = max([cl['updatedAt'] for cl in code_location_info])
            updated_at = updated_at.split(".")[0].split("T")
            most_recent_scan = " ".join(updated_at)
        phase_and_risk_info.update({'most_recent_scan_date': most_recent_scan})

    # get project version phase
    project_version_phase = "No phase has been set" if not version['phase'] else version['phase']
    phase_and_risk_info.update({'project_version_phase': project_version_phase})
    response = hub.execute_get(version['_meta']['links'][2]['href'])
    if response.status_code in [200, 201]:
        phase_and_risk_info.update(response.json().get('categories'))
    else:
        phase_and_risk_info.update({"risk_info": "No Info Available"})
    print(json.dumps(phase_and_risk_info))

def main():
    start = timeit.default_timer()
    get_info()
    print("Time spent getting info: {} seconds".format(int(timeit.default_timer() - start)))

main()
