'''
Created on June 25, 2024

@author: dnichol and kumykov

Generate version detail reports (source and components) and consolidate information on source matches, with license 
and component matched.  Removes matches found underneith other matched components in the source tree (configurable).

Copyright (C) 2023 Synopsys, Inc.
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
import csv
import logging
import sys
import io
import time
import json
import traceback
from blackduck import Client
from zipfile import ZipFile
from pprint import pprint

program_description = \
'''Generate version detail reports (source and components) and consolidate information on source matches, with license 
and component matched.  Removes matches found underneath other matched components in the source tree (configurable).

This script assumes a project version exists and has scans associated with it (i.e. the project is not scanned as part of this process).

'''

# BD report general
BLACKDUCK_VERSION_MEDIATYPE = "application/vnd.blackducksoftware.status-4+json"
BLACKDUCK_VERSION_API = "/api/current-version"
# Retries to wait for BD report creation. RETRY_LIMIT can be overwritten by the script parameter. 
RETRY_LIMIT = 30
RETRY_TIMER = 30

def log_config(debug):
    if debug:
        logging.basicConfig(format='%(asctime)s:%(levelname)s:%(module)s: %(message)s', stream=sys.stderr, level=logging.DEBUG)
    else:
        logging.basicConfig(format='%(asctime)s:%(levelname)s:%(module)s: %(message)s', stream=sys.stderr, level=logging.INFO)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("blackduck").setLevel(logging.WARNING)

def find_project_by_name(bd, project_name):
    params = {
        'q': [f"name:{project_name}"]
    }
    projects = [p for p in bd.get_resource('projects', params=params) if p['name'] == project_name]
    assert len(projects) == 1, f"Project {project_name} not found."
    return projects[0]

def find_project_version_by_name(bd, project, version_name):
    params = {
        'q': [f"versionName:{version_name}"]
    }
    versions = [v for v in bd.get_resource('versions', project, params=params) if v['versionName'] == version_name]
    assert len(versions) == 1, f"Project version {version_name} for project {project['name']} not found"
    return versions[0]

def create_version_details_report(bd, version):
    version_reports_url = bd.list_resources(version).get('versionReport')
    post_data = {
        'reportFormat' : 'JSON',
        'locale' : 'en_US',
        'versionId': version['_meta']['href'].split("/")[-1],
        'categories' : [ 'COMPONENTS', 'FILES' ] # Generating "project version" report including components and files
    }

    bd.session.headers["Content-Type"] = "application/vnd.blackducksoftware.report-4+json"
    r = bd.session.post(version_reports_url, json=post_data)
    if (r.status_code == 403):
        logging.debug("Authorization Error - Please ensure the token you are using has write permissions!")
    r.raise_for_status()
    location = r.headers.get('Location')
    assert location, "Hmm, this does not make sense. If we successfully created a report then there needs to be a location where we can get it from"
    return location

def download_report(bd, location, retries, timeout):
    report_id = location.split("/")[-1]
    logging.debug(f"Report location {location}")
    url_data = location.split('/')
    url_data.pop(4)
    url_data.pop(4)
    download_link = '/'.join(url_data)
    logging.debug(f"Report Download link {download_link}")
    if retries:
        logging.debug(f"Retrieving generated report for {location}  via  {download_link}")
        response = bd.session.get(location)
        report_status = response.json().get('status', 'Not Ready')
        if response.status_code == 200 and report_status == 'COMPLETED':
            response = bd.session.get(download_link, headers={'Content-Type': 'application/zip', 'Accept':'application/zip'})
            if response.status_code == 200:
                return response.content
            else:
                logging.error("Ruh-roh, not sure what happened here")
                return None
        else:
            logging.debug(f"Report status request {response.status_code} {report_status} ,waiting {timeout} seconds then retrying...")
            time.sleep(timeout)
            retries -= 1
            return download_report(bd, location, retries, timeout)
    else:
        logging.debug(f"Failed to retrieve report {report_id} after multiple retries")
        return None

def get_blackduck_version(hub_client):
    url = hub_client.base_url + BLACKDUCK_VERSION_API
    res = hub_client.session.get(url)
    if res.status_code == 200 and res.content:
        return json.loads(res.content)['version']
    else:
        sys.exit(f"Get BlackDuck version failed with status {res.status_code}")

def reduce(path_set):
    path_set.sort()
    for path in path_set:
        if len(path) < 3:
            continue
        index = path_set.index(path)
        while index + 1 < len(path_set) and path in path_set[index+1]:
            logging.debug(f"{path} is in {path_set[index+1]} deleting the sub-path from the list")
            path_set.pop(index+1)
    return path_set

def trim_version_report(version_report, reduced_path_set):
    file_bom_entries = version_report['detailedFileBomViewEntries']
    aggregate_bom_view_entries = version_report['aggregateBomViewEntries']

    reduced_file_bom_entries = [e for e in file_bom_entries if f"{e.get('archiveContext', '')}!{e['path']}" in reduced_path_set]
    version_report['detailedFileBomViewEntries'] = reduced_file_bom_entries

    component_identifiers = [f"{e['projectId']}:{e['versionId']}" for e in reduced_file_bom_entries]
    deduplicated = list(dict.fromkeys(component_identifiers))

    reduced_aggregate_bom_view_entries = [e for e in aggregate_bom_view_entries if f"{e['producerProject']['id']}:{e['producerReleases'][0]['id']}" in deduplicated]
    version_report['aggregateBomViewEntries'] = reduced_aggregate_bom_view_entries

'''

CSV output details

component name  = aggregateBomViewEntries[].producerProject.name
version name  = aggregateBomViewEntries[].producerReleases[0].version
license  = licenses[].licenseDisplay
file path = extract from detailedFileBomViewEntries
match type = aggregateBomViewEntries[].matchTypes
review status = aggregateBomViewEntries[].reviewSummary.reviewStatus

'''
def get_csv_fieldnames():
    return ['component name', 'version name', 'license', 'match type', 'review status']

def get_csv_data(version_report, keep_dupes):
    csv_data = list()
    components = list()
    for bom_view_entry in version_report['aggregateBomViewEntries']:
        entry = dict()   
        entry['component name'] = bom_view_entry['producerProject']['name']
        entry['version name'] = bom_view_entry['producerReleases'][0]['version']
        entry['license'] = bom_view_entry['licenses'][0]['licenseDisplay'].replace(' AND ',';').replace('(','').replace(')','')
        pid = bom_view_entry['producerProject']['id']
        vid = bom_view_entry['producerReleases'][0]['id']
        #path_list = [p['path'] for p in version_report['detailedFileBomViewEntries'] if p['projectId'] == pid and p['versionId'] == vid]
        #entry['file path'] = ';'.join(path_list)
        entry['match type'] = ';'.join(bom_view_entry['matchTypes'])
        entry['review status'] = bom_view_entry['reviewSummary']['reviewStatus']
        
        # Only add if this component was not previously added.
        composite_key = pid + vid
        if composite_key not in components:
            csv_data.append(entry)
            components.append(composite_key)
    if keep_dupes:
        return csv_data
    else:
        return remove_duplicates(csv_data)
    
def remove_duplicates(data):
    # Put data into buckets by version
    buckets = dict()
    for row in data:
        name = row['component name'].lower()
        version = row['version name']
        if not version in buckets:
            buckets[version] = [row]
        else:
            buckets[version].append(row)
    # Run reduction process for component names that start with existing component name
    # This process will ignore case in component names
    for set in buckets.values():
        set.sort(key = lambda d: d['component name'].lower())
        for row in set:
            index = set.index(row)
            name  = row['component name'].lower()
            while index + 1 < len(set) and set[index+1]['component name'].lower().startswith(name):
                set.pop(index+1)
    reduced_data = list()
    for b in buckets.values():
        reduced_data.extend(b)
    return reduced_data

def write_output_file(version_report, output_file, keep_dupes):
    if output_file.lower().endswith(".csv"):
        logging.info(f"Writing CSV output into {output_file}")
        field_names = get_csv_fieldnames()
        with open(output_file, "w") as f:
            writer = csv.DictWriter(f, fieldnames = field_names, extrasaction = 'ignore',quoting=csv.QUOTE_ALL) # TODO
            writer.writeheader()
            writer.writerows(get_csv_data(version_report, keep_dupes))
        return
    # If it's neither, then .json
    if not output_file.lower().endswith(".json"):
        output_file += ".json"
    logging.info(f"Writing JSON output into {output_file}")
    with open(output_file,"w") as f:
        json.dump(version_report, f)

def parse_command_args():
    parser = argparse.ArgumentParser(description=program_description, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("-u", "--base-url",     required=True, help="Hub server URL e.g. https://your.blackduck.url")
    parser.add_argument("-t", "--token-file",   required=True, help="File containing access token")
    parser.add_argument("-nv", "--no-verify",   action='store_false', help="Disable TLS certificate verification")
    parser.add_argument("-d", "--debug", action='store_true', help="Set debug output on")
    parser.add_argument("-pn", "--project-name", required=True, help="Project Name")
    parser.add_argument("-pv", "--project-version-name", required=True, help="Project Version Name")
    parser.add_argument("-o", "--output-file", required=False, help="File name to write output. File extension determines format .json and .csv, json is the default.")
    parser.add_argument("-kd", "--keep-dupes", action='store_true', help="Do not reduce CVS data by fuzzy matching component names")
    parser.add_argument("-kh", "--keep_hierarchy", action='store_true', help="Set to keep all entries in the sources report. Will not remove components found under others.")
    parser.add_argument("--report-retries", metavar="", type=int, default=RETRY_LIMIT, help="Retries for receiving the generated BlackDuck report. Generating copyright report tends to take longer minutes.")
    parser.add_argument("--report-timeout", metavar="", type=int, default=RETRY_TIMER, help="Wait time between subsequent download attempts.")
    parser.add_argument("--timeout", metavar="", type=int, default=60, help="Timeout for REST-API. Some API may take longer than the default 60 seconds")
    parser.add_argument("--retries", metavar="", type=int, default=4, help="Retries for REST-API. Some API may need more retries than the default 4 times")
    return parser.parse_args()

def main():
    args = parse_command_args()
    with open(args.token_file, 'r') as tf:
        token = tf.readline().strip()
    output_file = args.output_file
    if not args.output_file:
        output_file = f"{args.project_name}-{args.project_version_name}.json".replace(" ","_")
    try:
        log_config(args.debug)    
        hub_client = Client(token=token,
                            base_url=args.base_url,
                            verify=args.no_verify,
                            timeout=args.timeout,
                            retries=args.retries)
        
        project = find_project_by_name(hub_client, args.project_name)
        version = find_project_version_by_name(hub_client, project, args.project_version_name)
        location = create_version_details_report(hub_client, version)
        report_zip = download_report(hub_client, location, args.report_retries, args.report_timeout)
        logging.debug(f"Deleting report from Black Duck {hub_client.session.delete(location)}")
        zip=ZipFile(io.BytesIO(report_zip), "r")
        pprint(zip.namelist())
        report_data = {name: zip.read(name) for name in zip.namelist()}
        filename = [i for i in report_data.keys() if i.endswith(".json")][0]
        version_report = json.loads(report_data[filename])
        with open("out.json", "w") as f:
            json.dump(version_report, f)
        # TODO items
        # Process file section of report data to identify primary paths
        path_set = [f"{entry.get('archiveContext', '')}!{entry['path']}" for entry in version_report['detailedFileBomViewEntries']]
        reduced_path_set = reduce(path_set.copy())
        logging.info(f"{len(path_set)-len(reduced_path_set)} path entries were scrubbed from the dataset.")

        # Remove component entries that correspond to removed path entries.

        logging.info(f"Original dataset contains {len(version_report['aggregateBomViewEntries'])} bom entries and {len(version_report['detailedFileBomViewEntries'])} file view entries")
        if not args.keep_hierarchy:
            trim_version_report(version_report, reduced_path_set)
            logging.info(f"Truncated dataset contains {len(version_report['aggregateBomViewEntries'])} bom entries and {len(version_report['detailedFileBomViewEntries'])} file view entries")

        write_output_file(version_report, output_file, args.keep_dupes)

        # Combine component data with selected file data
        # Output result with CSV anf JSON as options.



    except (Exception, BaseException) as err:
        logging.error(f"Exception by {str(err)}. See the stack trace")
        traceback.print_exc()

if __name__ == '__main__':
    sys.exit(main())
