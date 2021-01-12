#!/usr/bin/python3
# encoding: utf-8
'''
examples.vulnerability_remediation -- shortdesc
examples.vulnerability_remediation is a description
It defines classes_and_methods
@author:     user_name
@copyright:  2020 organization_name. All rights reserved.
@license:    license
@contact:    user_email
@deffield    updated: Updated
'''

'''
This script updates vulnerablity remedation status for specific CVEs
or specific origins in a Black Duck projec/version.  The intent is to reduce the number of
new vulnearblitites that need to be manually reviewed.  The script only process 
vulnerablities that are currently have NEW remediation stautus.  The script looks for two
types of matches for vulnerablitites.
They are:

o) Specific CVE - intended to apply remedation status for specific CVE
o) Origin subtring - intended to apply remediation status for specific origins
                     For example, origns for a particular processor architecture (PPC)

Each processing step can be turned on or off.  At least one step must be run.  Default
is to run both.

The script get's it CVE and orign lists from CSV files.  The CSV filenames are loaded
from Custom Fields in the Black Duck project.  This allows different groups of projects to
use different remeidation settings.  If a CVE remediation status should apply globally
to all projects, Black Duck's global remediation feature should be used.

Here is an example of the CSV data for the CVE list:

"CVE-2016-1840","IGNORED","Applies only to Apple OS"
"CVE-2019-15847","IGNORED","Applies to Power9 architecture"
"CVE-2016-4606","IGNORED","Applies only to Apple OS" 

The 1st column is used for exact matches to CVE ids on vulnerablitites.
The 2nd column is the new remediation status.  Thus must be a valid Black duck status.
The 3rd column is a comment that will be added to the vulnerablity without change.

Here is an example of the CSV data for the origin exclusion list:

"ppc","IGNORED","Ignore PPC origins"
"armv7hl","NEEDS_REVIEW","Review ARMV7HL origins"

The 1st column is used for substring match to OriginID
The 2nd column is the new remediation status.  Thus must be a valid Black duck status.
The 3rd column is a comment that will be added to the vulnerablity without change.

If a vulnerablity matches both CVE and origin exclusion, the CVE remeditation is applied.
The comment will be updated the value from both files.

Black Duck custom fields are used to hold the file names.  The files are opened
relative to the directory where the script is run.  The default Custom Field labels
the script looks for are:
    CVE Remediation List
    Origin Exclusion List
The lables can be changed from the command line, if needed.

'''

import sys
import os
import json
import csv
import traceback

from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter

from blackduck.HubRestApi import HubInstance


__all__ = []
__version__ = 0.1
__date__ = '2020-12-21'
__updated__ = '2021-12-26'


def load_remediation_input(remediation_file):
    with open(remediation_file, mode='r') as infile:
        reader = csv.reader(infile)
        return {rows[0]:[rows[1],rows[2]] for rows in reader}

def remediation_is_valid(vuln, remediation_data):
    vulnerability_name = vuln['vulnerabilityWithRemediation']['vulnerabilityName']
    # remediation_status = vuln['vulnerabilityWithRemediation']['remediationStatus']
    # remediation_comment = vuln['vulnerabilityWithRemediation'].get('remediationComment','')
    if vulnerability_name in remediation_data.keys():
        return remediation_data[vulnerability_name]
    else:
        return None

def origin_is_excluded (vuln, exclusion_data):
    if 'componentVersionOriginId' in vuln.keys():
        originId = vuln['componentVersionOriginId']
        for excludedOrigin in exclusion_data:
            if excludedOrigin in originId:
               return exclusion_data[excludedOrigin]
        return None
    else:
        return None

def find_custom_field_value (custom_fields, custom_field_label):
    for field in custom_fields['items']:
        if field['label'] == custom_field_label:
            if len(field['values']) > 0:
                return field['values'][0]
            else:
                print (f'Error: Custom Field \"{custom_field_label}\" is empty on Black Duck instance.')
                return None
    return None

def process_vulnerabilities(hub, vulnerable_components, remediation_data=None, exclusion_data=None):
    count = 0
    print('"Component Name","Component Version","Component OriginID","CVE","Reason","Remeidation Status","HTTP response code"')

    for vuln in vulnerable_components['items']:
        if vuln['vulnerabilityWithRemediation']['remediationStatus'] == "NEW":
            if (remediation_data):
                remediation_action = remediation_is_valid(vuln, remediation_data)

            if (exclusion_data):
                exclusion_action = origin_is_excluded(vuln, exclusion_data)

            # If vuln has both a remdiation action and an origin exclusion action, set remdiation status
            # to the remdiation action.  Append the exclusion action's comment to the overall comment.
            reason = 'CVE-list'
            if (remediation_action and exclusion_action):
                remediation_action[1] =  exclusion_action[1] + '\n' + remediation_action[1]
                reason = 'CVE-list and origin-exclusion'
            elif (exclusion_action): # If only exclusion action found, use it to set remediation status
                remediation_action = exclusion_action
                reason = 'origin-exclusion'

            if (remediation_action):
                resp = hub.set_vulnerablity_remediation(vuln, remediation_action[0],remediation_action[1])
                count += 1
                print ('\"{}\",\"{}\",\"{}\",\"{}\",\"{}\",\"{}\",\"{}\"'.
                    format(vuln['componentName'], vuln['componentVersionName'],
                    vuln['componentVersionOriginId'], 
                    vuln['vulnerabilityWithRemediation']['vulnerabilityName'],
                    reason, remediation_action[0], resp.status_code))
    print (f'Remediated {count} vulnerabilities.')

def main(argv=None): # IGNORE:C0111
    '''Command line options.'''

    if argv is None:
        argv = sys.argv
    else:
        sys.argv.extend(argv)

    program_name = os.path.basename(sys.argv[0])
    program_version = "v%s" % __version__
    program_build_date = str(__updated__)
    program_version_message = '%%(prog)s %s (%s)' % (program_version, program_build_date)
    program_shortdesc = __import__('__main__').__doc__.split("\n")[1]
    program_license = '''%s

  Created by user_name on %s.
  Copyright 2020 Synopsys. All rights reserved.

  Licensed under the Apache License 2.0
  http://www.apache.org/licenses/LICENSE-2.0

  Distributed on an "AS IS" basis without warranties
  or conditions of any kind, either express or implied.

USAGE
''' % (program_shortdesc, str(__date__))

    try:
        # Setup argument parser
        parser = ArgumentParser(description=program_license, formatter_class=RawDescriptionHelpFormatter)
        parser.add_argument("projectname", help="Project nname")
        parser.add_argument("projectversion", help="Project vesrsion")
        parser.add_argument("--no-process-cve-remediation-list", dest='process_cve_remediation_list', action='store_false', help="Disbable processing CVE-Remediation-list")
        parser.add_argument("--no-process-origin-exclusion-list", dest='process_origin_exclusion_list', action='store_false', help="Disable processing Origin-Exclusion-List")
        parser.add_argument("--cve-remediation-list-custom-field-label", default='CVE Remediation List', help='Label of Custom Field on Black Duck that contains remeidation list file name')
        parser.add_argument("--origin-exclusion-list-custom-field-label", default='Origin Exclusion List', help='Label of Custom Field on Black Duck that containts origin exclusion list file name')
        parser.add_argument('-V', '--version', action='version', version=program_version_message)

        # Process arguments
        args = parser.parse_args()

        projectname = args.projectname
        projectversion = args.projectversion
        process_cve_remediation = args.process_cve_remediation_list
        process_origin_exclulsion = args.process_origin_exclusion_list
       
        message = f"{program_version_message}\n\n Project: {projectname}\n Version: {projectversion}\n Process origin exclusion list: {process_origin_exclulsion}\n Process CVE remediation list: {process_cve_remediation}"
        print (message)
        
        if (process_cve_remediation == False) and (process_origin_exclulsion == False):
            print ('Error: Nothing to do, both --no-process-cve-remediation-list and --no-process-origin-exclusion-list set.')
            exit (1)

        # Connect to Black Duck instance, retrive project, project version, and the project's custom fields.        
        hub = HubInstance()
        project = hub.get_project_by_name(projectname)
        version = hub.get_project_version_by_name(projectname, projectversion)
        custom_fields = hub.get_project_custom_fields (project)

        if (process_cve_remediation):
            cve_remediation_file = find_custom_field_value (custom_fields, args.cve_remediation_list_custom_field_label)
            print (f' Opening: {args.cve_remediation_list_custom_field_label}:{cve_remediation_file}')
            remediation_data = load_remediation_input(cve_remediation_file)
        else:
            remediation_data = None

        if (process_origin_exclulsion):
            exclusion_list_file = find_custom_field_value (custom_fields, args.origin_exclusion_list_custom_field_label)
            print (f' Opening: {args.origin_exclusion_list_custom_field_label}:{exclusion_list_file}')
            exclusion_data = load_remediation_input(exclusion_list_file)
        else:
            exclusion_data = None

        # Retrieve the vulnerabiltites for the project version
        vulnerable_components = hub.get_vulnerable_bom_components(version)

        process_vulnerabilities(hub, vulnerable_components, remediation_data, exclusion_data)
        
        return 0
    except Exception:
        ### handle keyboard interrupt ###
        traceback.print_exc()
        return 0

if __name__ == "__main__":
    sys.exit(main())