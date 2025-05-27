"""
Created on july 11, 2024
@author: Dinesh Ravi
Gather list of non matched components where blackduck could not able have match event with their kb for the bdio codelocation type
"""
from blackduck import Client

import argparse

import logging
import json
# py get_scan_missed_import_event.py --base-url=https://blackduck.company.com --token-file=.pt --project=ASTERIX2CLU3D_PR
# OGRAM --version=AED2_ANDROID_S_2_2024-09-21_00-32 --company=company --no-verify > missing.txt
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] {%(module)s:%(lineno)d} %(levelname)s - %(message)s"
)

parser = argparse.ArgumentParser("Get the BOM components for a given project-version and the license details for each BOM component")
parser.add_argument("--base-url", required=True, help="Hub server URL e.g. https://your.blackduck.url")
parser.add_argument("--token-file", dest='token_file', required=True, help="containing access token")
parser.add_argument("--project", dest='project_name', required=True, help="Project that contains the BOM components")
parser.add_argument("--version", dest='version_name', required=True, help="Version that contains the BOM components")
parser.add_argument("--company", dest='company_name', required=True, help="modules that contains the company name for separation")
parser.add_argument("--no-verify", dest='verify', action='store_false', help="disable TLS certificate verification")
args = parser.parse_args()

with open(args.token_file, 'r') as tf:
    access_token = tf.readline().strip()

bd = Client(base_url=args.base_url, token=access_token, verify=args.verify)

params = {
    'q': [f"name:{args.project_name}"]
}

projects = [p for p in bd.get_resource('projects', params=params) if p['name'] == args.project_name]
assert len(projects) == 1, f"There should be one, and only one project named {args.project_name}. We found {len(projects)}"
project = projects[0]

params = {
    'q': [f"versionName:{args.version_name}"]
}
versions = [v for v in bd.get_resource('versions', project, params=params) if v['versionName'] == args.version_name]
assert len(versions) == 1, f"There should be one, and only one version named {args.version_name}. We found {len(versions)}"
version = versions[0]

print(f"Found {project['name']}:{version['versionName']}")
hashset_company = set()
hashset_other = set()
# ===================
# print(version)
# params = {
#     'q': [f"name:*bdio*"]
# }
codelocations=[codelocation for codelocation in bd.get_resource('codelocations',version) if 'bdio' in codelocation['name']]
# print(codelocations[0])
# codelocation=codelocations[0]
for codelocation in codelocations:
    scans=bd.get_resource('scans',codelocation) 
    for scan in scans:
        events=[events for events in bd.get_resource('component-import-events',scan) if events['event']=="COMPONENT_MAPPING_FAILED"]
        if len(events)>0:
            print("============================")
            print(f"codelocation_name: {codelocation['name']}")
            print(f"matchCount: {scan['matchCount']}")
            print(f"missing: {len(events)}")
            
            for i,event in enumerate(events,start=1):
                print(f"--------------{i}")
                externalId=event['externalId']
                print(f"externalId: {externalId}")
                print(f"importComponentName: {event['importComponentName']}")
                print(f"importComponentVersionName: {event['importComponentVersionName']}")
                if args.company_name in externalId:
                    hashset_company.add(externalId)
                else:
                    hashset_other.add(externalId)

                # {'event': 'COMPONENT_MAPPING_FAILED', 
                #  'importComponentName': 'rsi-common-lib', 
                #  'importComponentVersionName': '0.2.14', 
                #  'externalId': 'com.company.aed2:rsi-common-lib:0.2.14', 
                #  'failureReason': 'Unable to map scanned component version to Black Duck project version because no mapping is present for the given external identifier'}
print("============================")
sorted_company=sorted(hashset_company)
sorted_other=sorted(hashset_other)

print(f"========total missing Other components to get foss report: {len(hashset_other)}========")
for i,missing in enumerate(sorted_other,start=1):
    print(f"{i} {missing}")
print(f"========total missing {args.company_name} components to manually add: {len(hashset_company)}========")
for i,missing in enumerate(sorted_company,start=1):
    print(f"{i} {missing}")
total_missing=len(sorted_company)+len(sorted_other)
print(f"========EB:{len(sorted_company)}+Other:{len(sorted_other)}={total_missing}========")
