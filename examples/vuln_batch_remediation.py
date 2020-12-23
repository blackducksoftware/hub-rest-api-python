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
__updated__ = '2020-12-21'


def load_remediation_input(remediation_file):
    with open(remediation_file, mode='r') as infile:
        reader = csv.reader(infile)
        return {rows[0]:[rows[1],rows[2]] for rows in reader}

def remediation_is_valid(vuln, remediation_data):
    vulnerability_name = vuln['vulnerabilityWithRemediation']['vulnerabilityName']
    remediation_status = vuln['vulnerabilityWithRemediation']['remediationStatus']
    remediation_comment = vuln['vulnerabilityWithRemediation'].get('remediationComment','')
    if vulnerability_name in remediation_data.keys():
        return remediation_data[vulnerability_name]
    else:
        return None

def process_vulnerabilities(vulnerable_components, remediation_data=None, tags=None):
    for vuln in vulnerable_components['items']:
        remediation_action = remediation_is_valid(vuln, remediation_data)
        if remediation_action:
            print("located vulnerability {} with status {}".
                  format(vuln['vulnerabilityWithRemediation']['vulnerabilityName'],
                         vuln['vulnerabilityWithRemediation']['remediationStatus']))
            print("      executing hub.set_vulnerablity_remediation(vuln, '{}', '{}')"
                  .format(remediation_action[0],remediation_action[1]))
            # action is commented out intil remediation_is_valid is properly defined
            # hub.set_vulnerablity_remediation(vuln, remediation_action[0],remediation_action[1])

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
  Copyright 2020 organization_name. All rights reserved.

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
        parser.add_argument("--remediation-input-file", dest="remediation_file", help="CSV file Vulns fro autom,atic remediation")
        parser.add_argument("--process-tags", default=False, help="Process tags")
        parser.add_argument('-V', '--version', action='version', version=program_version_message)

        # Process arguments
        args = parser.parse_args()

        projectname = args.projectname
        projectversion = args.projectversion
        remediation_input = args.remediation_file
        process_tags = args.process_tags
        
        message = "{}\n\n Project:{}\nVersion: {}\n CSV: {}\n Process tags: {}\n".format(program_version_message,projectname, projectversion, remediation_input, process_tags)
        
        print (message)
        
        hub = HubInstance()

        project = hub.get_project_by_name(projectname)
        tags = hub.get_project_tags(project)
        if remediation_input:
            remediation_data = load_remediation_input(remediation_input)
        version = hub.get_project_version_by_name(projectname, projectversion)
        vulnerable_components = hub.get_vulnerable_bom_components(version)
        process_vulnerabilities(vulnerable_components, remediation_data)
        
        return 0
    except Exception:
        ### handle keyboard interrupt ###
        traceback.print_exc()
        return 0

if __name__ == "__main__":
    sys.exit(main())