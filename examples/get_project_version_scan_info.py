#!/usr/bin/env python

from blackduck.HubRestApi import HubInstance

import argparse
import json

parser = argparse.ArgumentParser()
parser.add_argument("project_name")
parser.add_argument("version_name")
args = parser.parse_args()

hub = HubInstance()

project = hub.get_project_by_name(args.project_name)
if project:
    version = hub.get_version_by_name(project, args.version_name)

    if version:
        codelocation_url = hub.get_link(version, "codelocations")
        response = hub.execute_get(codelocation_url)
        if response.status_code == 200:
            # codelocation and scan are synonymous
            codelocation_info = response.json().get('items', [])
            if codelocation_info:
                most_recent_scan = max([cl['updatedAt'] for cl in codelocation_info])
                oldest_scan = min([cl['updatedAt'] for cl in codelocation_info])
                number_scans = len(codelocation_info)
            else:
                number_scans = 0
                oldest_scan = most_recent_scan = "Not applicable"

            print(json.dumps(
                {
                    'scans': codelocation_info,
                    'number_scans': number_scans,
                    'most_recent_scan': most_recent_scan,
                    'oldest_scan': oldest_scan
                }))
        else:
            print("Failed to retrieve the codelocation (aka scan) info, response code was {}".format(response.status_code))
    else:
        print("Could not find the version {} in project {}".format(args.version_name, args.project_name))
else:
    print("Could not find the project {}".format(args.project_name))