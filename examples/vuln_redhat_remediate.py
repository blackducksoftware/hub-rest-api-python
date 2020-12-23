#!/usr/bin/env python3

"""
This script finds CVEs for RedHat and CentOS origins and looks them up in RedHat's security data.
If a match is found in RedHat's data, the Black Duck vulneralbity is updated with RedHat's stats
and a link to the RedHat advisory.

This  script is used to find vulnerabilities from RedHat/Centos origins an update their remediation
status on Black Duck with the status from RedHat.  Remdiation status will be NEW, IGNORED or PATCHED
based on the RedHat security errta.  A link to the RedHat errata is added as a comment.

"""

import argparse
import logging
import sys
import requests
import json
import re

from blackduck.HubRestApi import HubInstance, object_id

def update_hub_vuln(vuln, message):
    if message[0] == 'Not affected':
        remediation_status = 'IGNORED'
    elif message[0] == 'Released':
        remediation_status = 'PATCHED'
    else:
        remediation_status = 'NEW'

    comment = ' / '
    resp = hub.set_vulnerablity_remediation (vuln, remediation_status, comment.join(message))

    return (resp.status_code, remediation_status)

def get_el_version(componentVersionOriginId):

    #identify if component is from el7/ el8 release
    el_version = re.findall(r'el[0-9]',componentVersionOriginId)

    if 'el7' in el_version:
        return 'Red Hat Enterprise Linux 7'
    elif 'el8' in el_version:
        return 'Red Hat Enterprise Linux 8'
    elif 'el6' in el_version:
        return 'Red Hat Enterprise Linux 6'

def get_rhsa_opinion(cve_id, componentVersionOriginId):
    #return print_msg_box(cve_id + "  -->  " + componentVersionOriginId)
    
    redhat_errata = 'https://access.redhat.com/security/cve/'+ cve_id

    redhat_api = 'https://access.redhat.com/hydra/rest/securitydata/cve/' + cve_id + '.json'
    redhat_resp = requests.get(redhat_api, headers={}, verify=False).json()
    fix_state = ''

    el_version = get_el_version(componentVersionOriginId)
    
    if "affected_release" in redhat_resp.keys():
        for item in redhat_resp['affected_release']:
            if item['product_name'] == el_version:
                if "package" in item.keys():  #Some RedHat data doesn’t have package field.  Not sure this is the best approach.
                    pkg_name = item['package'].split('-')[0]
                    if pkg_name in componentVersionOriginId:
                        fix_state = 'Released'
                        break
    
    if fix_state != 'Released':
        if "package_state" in redhat_resp.keys():
            for item in redhat_resp['package_state']:
                if item['product_name'] == el_version:
                    pkg_name = re.split(r'(-|/)',componentVersionOriginId)[0]
                    if pkg_name in item['package_name'] or item['package_name'] in pkg_name:
                        fix_state = item['fix_state']
                        break
                    else:
                        fix_state = 'Uncertain'
                else:
                    fix_state = "Not Listed"
        else: 
            fix_state = "Not Listed"

    return (fix_state, redhat_errata) 

def find_components(project_version, limit):
    count = 0

    items = hub.get_vulnerable_bom_components(project_version, limit)
    
    print ('Component Name Version, Component OriginID, CVE, RedHat State, Remediation Status, HTTP response code, update status')
    for vuln in items['items']:
        if vuln['vulnerabilityWithRemediation']['source'] == "NVD" \
            and vuln['vulnerabilityWithRemediation']['remediationStatus'] == "NEW" \
            and vuln["componentVersionOriginName"] in ["centos","redhat"]:

            count +=1
            cve_id = vuln['vulnerabilityWithRemediation']['vulnerabilityName']
            componentVersionOriginId = vuln['componentVersionOriginId']
            for i in vuln['_meta']['links']:
                if i['rel'] == 'vulnerabilities':
                    message = get_rhsa_opinion(cve_id, componentVersionOriginId)
                    response = update_hub_vuln(vuln, message)
                    if response[0] == 202:
                        response_text = 'succeded'
                    else:
                        response_text = 'failed'    
                    print(f"{vuln['componentName']} {vuln['componentVersionName']}, {componentVersionOriginId}, {cve_id}, {message[0]}, {response[1]}, {response[0]}, {response_text}")
        else:
            print(f"{vuln['componentName']} {vuln['componentVersionName']}, {vuln['componentVersionOriginId']}, {vuln['vulnerabilityWithRemediation']['vulnerabilityName']}, N/A, {vuln['vulnerabilityWithRemediation']['remediationStatus']}, N/A, N/A")

    return count

parser = argparse.ArgumentParser("Lookup vulnerabilities from RedHat or CentOS origins, update comments with RHSA reference when available, mark as ignored if RedHat indicates 'not affected.'")
parser.add_argument("-l", "--limit",
    default=9999,
    help="Set limit on number of vulnerabilitties to retrieve (default 9999)")
parser.add_argument("project_name", help="Black Duck project name")
parser.add_argument("version", help="Black Duck version")

args = parser.parse_args()
 
logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stderr, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

#Create a connection to the Black Duck instance configured in .restconfig.json
hub = HubInstance()

#find project-version
project_version = hub.get_project_version_by_name(args.project_name, args.version)

if (project_version is None):
    print (f'Could not find {args.project_name} / {args.version}')
    exit (1)
else:
    print (f'Found {args.project_name} / {args.version}')
    print("Processing BOM Components...")
    count = find_components(project_version, args.limit)
    print (f"Vulnerabilities Processed = {count}")
