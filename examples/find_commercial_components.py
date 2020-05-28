#!/usr/bin/env python

'''
Created on Mar 29, 2019

@author: gsnyder

Retrieve components marked as commercial and having CVE's

Warning: This program is single-threaded to minimize the load on the system so it can take
a very long time to run.

'''

import argparse
import csv
from datetime import datetime
import json
import logging
import sys

from blackduck.HubRestApi import HubInstance

parser = argparse.ArgumentParser("Find components marked as commercial, and with vulnerabilities, in the Black Duck KB and write them to an Excel file, one row per vulnerability")
parser.add_argument("-f", "--file", default="has_commercial_components.csv", help="The output file name (default: has_commercial_components.csv) to use when capturing all the components marked commercial from the Black Duck KB that have vulnerabilities")
parser.add_argument("-l", "--limit", type=int, default=100, help="The number of components to return with each call to the REST API (default: 100)")
parser.add_argument("-t", "--total", type=int, default=99999, help="The total number of components to retrieve")
args = parser.parse_args()

logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stderr, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

hub = HubInstance()

components_url = hub.get_apibase() + "/search/components"

offset = 0
total_hits = 0

# loop to page through the results from the KB until there are none left
while total_hits < args.total:
    logging.debug("Retrieving components with has_commercial=true AND has_cves=true from offset {}, limit {}".format(
        offset, args.limit))
    find_commercial_url = components_url + "?q=has_commercial:true&filter=has_cves:true&limit={}&offset={}".format(
        args.limit, offset)

    logging.debug("Executing GET on {}".format(find_commercial_url))
    results = hub.execute_get(find_commercial_url).json().get('items', [])

    if results:
        offset += args.limit
        hits = results[0]['hits']
        total_hits += len(hits)
        logging.debug("Found {} hits, total hits now {}".format(len(hits), total_hits))

        rows = []
        for hit in hits:
            number_versions = int(hit['fields']['release_count'][0])
            component_name = hit['fields']['name'][0]
            component_url = hit['component']
            component_description = hit['fields']['description'][0]
            if number_versions < 1000:
                component = hub.execute_get(hit['component']).json()
                versions_url = hub.get_link(component, "versions")
                versions = hub.execute_get(versions_url).json().get('items', [])
                logging.debug("Found {} versions for component {}".format(len(versions), component['name']))
                for version in versions:
                    version_name = version['versionName']
                    version_url =version['_meta']['href']
                    vuln_url = hub.get_link(version, "vulnerabilities")
                    vulns = hub.execute_get(vuln_url).json().get('items', [])
                    logging.debug("Found {} vulnerabilities for version {}".format(
                        len(vulns), version_name))
                    for vuln in vulns:      
                        logging.debug("Adding {}".format(vuln['name']))
                        row_data = {
                                "Component Name": component_name,
                                "Component URL": component_url,
                                "Description": component_description,
                                "Version": version_name,
                                "Version URL": version_url,
                                "Vuln": vuln['name'],
                                "Vulnerability URL": vuln['_meta']['href'],
                                "Vuln Description": vuln['description'],
                                "Vuln Severity": vuln['severity'],
                                "Vuln CWE URL": hub.get_link(vuln, "cwes"),
                                "Vuln Published Date": vuln['publishedDate'],
                                "Vuln Updated Date": vuln['updatedDate'],
                            }

                        #
                        # Expand CVSS2 and CVSS3 data into separate columns so they can be used (in Excel)
                        # to filter, sort, etc
                        #
                        cvss2 = {}
                        if 'temporalMetrics' in vuln['cvss2']:
                            # expand temporal metrics
                            cvss2_temporal_metrics = {"cvss2_temporal_"+k:v for (k,v) in vuln['cvss2']['temporalMetrics'].items()}
                            cvss2.update(cvss2_temporal_metrics)
                            # remove the redundant info
                            del vuln['cvss2']['temporalMetrics']
                        cvss2.update({"cvss2_"+k:str(v) for (k,v) in vuln['cvss2'].items()})
                        row_data.update(cvss2)

                        cvss3 = {}
                        if 'cvss3' in vuln:
                            if 'temporalMetrics' in vuln['cvss3']:
                                # expand temporal metrics
                                cvss3_temporal_metrics = {"cvss3_temporal_"+k:v for (k,v) in vuln['cvss3']['temporalMetrics'].items()}
                                cvss3.update(cvss3_temporal_metrics)
                                # remove the redundant info
                                del vuln['cvss3']['temporalMetrics']
                            cvss3 = {"cvss3_"+k:str(v) for (k,v) in vuln['cvss3'].items()}
                            row_data.update(cvss3)
                        rows.append(row_data)

        if len(hits) < args.limit:
            # at the end?
            logging.debug("Looks like we are at the end, breaking loop")
            break
    else:
        logging.debug("No results, exiting loop")
        break

logging.debug("Saving {} hits to has_commercial_components.csv".format(total_hits))
all_columns = set()
for row in rows:
    all_columns = all_columns.union(row.keys())

# Relying on spelling of keys/column names to put them into a 'nice' order
# when they are written out to CSV using DictWriter
all_columns = sorted(all_columns)

with open(args.file, "w", newline="") as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=all_columns)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)

