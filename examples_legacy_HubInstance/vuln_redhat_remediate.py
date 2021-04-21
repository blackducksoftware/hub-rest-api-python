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
    #update to skip "released" status.

    if message[0] == 'Not affected':
        remediation_status = 'IGNORED'
    #elif message[0] == 'Released':
    #    remediation_status = 'PATCHED'
    else:
        remediation_status = 'NEW'

    comment = 'RedHat State: ' + message[0] + '\n' + 'RedHat link: ' + message[1]
    resp = hub.set_vulnerablity_remediation (vuln, remediation_status, comment)

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

    #Check if RedHat returned an entry for this CVE
    if 'message' not in redhat_resp.keys():
        el_version = get_el_version(componentVersionOriginId)
        
        # Removing this logic as the KB has data on patched components tied to originID.
        # If re-enabled, this needs to look at package version from the origin ID and compare it to the RedHat package version.
        # if "affected_release" in redhat_resp.keys():
        #     for item in redhat_resp['affected_release']:
        #         if item['product_name'] == el_version:
        #             if "package" in item.keys():  #Some RedHat data doesn’t have package field.  Not sure this is the best approach.
        #                 pkg_name = item['package'].split('-')[0]
        #                 if pkg_name in componentVersionOriginId:
        #                     fix_state = 'Released'
        #                     break
        
        # if fix_state != 'Released':
        
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
                    fix_state = 'Not Listed'
        #    else: 
        #        fix_state = 'Not Listed'
    else:
        fix_state = 'CVE Not Found'
        redhat_errata = 'N/A'  # No RedHat security entry for this CVE.

    return (fix_state, redhat_errata) 

def find_components(project_version, limit, all):
    count = 0

    items = hub.get_vulnerable_bom_components(project_version, limit)
    
    print ('"Component Name","Component Version","Component OriginID","CVE","RedHat State","Remediation Status","HTTP response code","update completed"')
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
                    print('"{}","{}","{}","{}","{}" "{}","{}","{}"'.
                        format(vuln['componentName'], vuln['componentVersionName'],
                        componentVersionOriginId, cve_id, message[0],
                        response[1], response[0], response_text))

        else:
            if (all):
                if 'componentVersionOriginId' in vuln.keys():
                    componentVersionOriginId=vuln['componentVersionOriginId']
                else:
                    componentVersionOriginId = 'unknown'
                print('"{}","{}","{}","{}","N/A","{}","N/A","N/A"'.
                    format (vuln['componentName'], vuln['componentVersionName'],
                    componentVersionOriginId, vuln['vulnerabilityWithRemediation']['vulnerabilityName'],
                    vuln['vulnerabilityWithRemediation']['remediationStatus']))

    return count

parser = argparse.ArgumentParser(description="Update status and comments for vunls from RedHat/CentOS")
parser.add_argument("-l", "--limit",
    default=9999,
    help="Set limit on number of vulnerabilitties to retrieve (default 9999)")
parser.add_argument("project_name", help="Black Duck project name")
parser.add_argument("version", help="Black Duck version")
parser.add_argument("--all", action='store_true', help="Print unprocessed vulns (default is processed vulns)")
  

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
    count = find_components(project_version, args.limit, args.all)
    print (f"Vulnerabilities Processed = {count}")
