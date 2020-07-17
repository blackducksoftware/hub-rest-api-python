#!/usr/bin/env python

import argparse
import csv
import json
import logging
import sys
from pprint import pprint

from blackduck.HubRestApi import HubInstance, object_id

parser = argparse.ArgumentParser("Get a list of project-versions with un-confirmed snippet matches")
parser.add_argument("csv_file", help="Provide the name of the CSV file to dump the list of project-versions into")
parser.add_argument("-l", "--limit", type=int, default=100, help="Set the limit on the number of projects to retrieve at a time")
parser.add_argument("-a", "--all", action='store_true', help="Output all the project-versions regardless of whether they have snippet matches, or un-confirmed snippet matches")
args = parser.parse_args()

logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stderr, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

hub = HubInstance()

columns = [
    'Project Name', 
    'Version Name', 
    'Version URL', 
    'Has Snippets', 
    'Un-confirmed', 
    'Confirmed', 
    'Ignored',
    'Total'
]

with open(args.csv_file, 'w') as csv_file:
    writer = csv.DictWriter(csv_file, fieldnames=columns)
    writer.writeheader()

    for project in hub.get_projects(limit=args.limit).get('items', []):
        for version in hub.get_project_versions(project).get('items', []):
            snippet_counts_url = version['_meta']['href'] + "/snippet-counts"
            #
            # As of v2020.6.0 the Content-Type returned is application/vnd.blackducksoftware.internal-1+json;charset=UTF-8
            # so I'm accepting any content type to allow the GET to work flexibly
            #
            custom_headers = {'Accept': '*/*'}
            snippet_counts = hub.execute_get(snippet_counts_url, custom_headers=custom_headers).json()

            snippets_present = snippet_counts.get('snippetScanPresent', False)
            unconfirmed_snippets = snippets_present and snippet_counts.get('unreviewedCount', 0) > 0
            number_unconfirmed = snippet_counts.get('unreviewedCount', 0)
            number_confirmed = snippet_counts.get('reviewedCount', 0)
            number_ignored = snippet_counts.get('ignoredCount', 0)
            total = snippet_counts.get('totalCount', 0)
            assert (number_unconfirmed + number_confirmed + number_ignored) == total

            if snippets_present or args.all:
                # url_html = f"<a href={version['_meta']['href']}>{version['versionName']}</a>"
                url_html = f"=hyperlink(\"{version['_meta']['href']}/components\")"
                row = {
                    'Project Name': project['name'],
                    'Version Name': version['versionName'],
                    'Version URL': url_html,
                    'Has Snippets': snippets_present,
                    'Un-confirmed': number_unconfirmed,
                    'Confirmed': number_confirmed,
                    'Ignored': number_ignored,
                    'Total': total
                }
                writer.writerow(row)

