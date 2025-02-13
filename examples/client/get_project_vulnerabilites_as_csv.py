'''
Export the vulnerabilites from a project as CSV. Can be used to apply batch vulnerability
remediation with vuln_batch_remediation.py

Output is in format:
identifier, status, comment, componentName, componentVersion, description 

The API token should be specified in a .env file or as environment variable.
'''
import re
import os
import sys
import csv
import logging
import argparse
from pprint import pprint
from blackduck import Client
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = os.getenv('API_TOKEN')

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] {%(module)s:%(lineno)d} %(levelname)s - %(message)s"
)

def strip_newline(str):
    return str.replace('\r', '').replace('\n', '\\n')

def match_component(selected_components, component):
    if (len(selected_components) == 0):
        return True

    for selected in selected_components:
        if (re.search(selected, component, re.IGNORECASE)):
            return True

    return False

def main():
    program_name = os.path.basename(sys.argv[0])
    parser = argparse.ArgumentParser(prog=program_name, usage="%(prog)s [options]", description="Automated Assessment")
    parser.add_argument("project", help="project name")
    parser.add_argument("version",  help="project version, e.g. latest")
    parser.add_argument("--output", required=False,help="csv output path" )
    parser.add_argument("--base-url", required=False, help="base url", default="https://blackduck.omicron.at")
    parser.add_argument("--components", required=False, help="component names, comma seperated without space")
    args = parser.parse_args()

    components = args.components.split(',') if args.components != None else []
    projectname = args.project
    projectversion = args.version
    output = args.output  if  args.output != None else "output.csv"

    csv_file = open(output, mode='w', newline='', encoding='utf-8')
    csv_writer = csv.writer(csv_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)

    bd = Client(
        token=API_TOKEN,
        base_url=args.base_url,
        verify=False  # TLS certificate verification
    )

    for project in bd.get_resource('projects'):
        if (project['name'] == projectname):
            for version in bd.get_resource('versions', project):
                if (projectversion == None):
                    pprint(version['versionName'])

                else:
                    if (version['versionName'] == projectversion):
                        for vulnverable_component in bd.get_resource('vulnerable-components', version):
                            componentName = vulnverable_component["componentName"]

                            if (match_component(components, componentName)):
                                componentVersion = vulnverable_component["componentVersionName"]
                                remediation = vulnverable_component['vulnerabilityWithRemediation']

                                status = remediation['remediationStatus']
                                identifier = remediation['vulnerabilityName']
                                description = strip_newline(remediation['description'])
                                comment = strip_newline(remediation.get('remediationComment', ""))
                                
                                row =  [identifier, status, comment, componentName, componentVersion, description]
                                csv_writer.writerow(row)
                        break
            break

if __name__ == "__main__":
    main()
