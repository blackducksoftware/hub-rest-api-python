#!/usr/bin/env python

import argparse
from datetime import datetime
import logging
import json
import sys

parser = argparse.ArgumentParser("Process the JSON output from get_bom_component_policy_violations.py to create a FIX IT message that guides the project team how to resolve the issues identified through policy rule violations")
parser.add_argument("-f", "--policy_violations_file", help="By default, program reads JSON doc from stdin, but you can alternatively give a file name")
parser.add_argument("-o", "--output_file", help="By default, the fix it message is written to stdout. Use this option to instead write to a file")

args = parser.parse_args()

logging.basicConfig(format='%(asctime)s%(levelname)s:%(message)s', stream=sys.stderr, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

if args.policy_violations_file:
    with open(args.policy_violations_file, 'r') as pvf:
        policy_violations = json.load(pvf)
else:
    policy_violations = json.load(sys.stdin)

project_name = policy_violations['project']['name']
version_label = policy_violations['version']['versionName']
version_url = policy_violations['version']['_meta']['href']
version_license = policy_violations['version']['license']['licenseDisplay']
if version_license.lower() == "unknown license":
    license_statement = """This project version does not appear to have a declared license. 
        You should probably declare one.. You can find more info on how to choose the appropriate license
        for your project <a href=https://our-company/choosing-license>here</a>"""
else:
    license_statement = "This project version is governed by the {} license.".format(version_license)

html = """
<html>
    <body>
        <p>This is a summary of the policy violations found in project {}, version {}. It was created {}. 
        This summary provides guidance on what to do to resolve these violations. </p>
        <p>{}</p> 
        <p>You can view the project version and more details regarding it
        on Black Duck <a href={}>here</a></p>
        <p>For more information on SCA (Software Composition Analysis) and 
        how it fits into our SDLC go to <a href=https://our-company/sca-info>https://our-company/sca-info</a></p>

        <table border=1>
            <tr>
                <th>Component</th>
                <th>Version</th>
                <th>Component License</th>
                <th>URL</th>
                <th>Violation</th>
                <th>Guidance to Fix</th>
                <th>Overrideable</th>
                <th>Severity</th>
            </tr>
""".format(project_name, version_label, datetime.now(), license_statement, version_url)

del policy_violations['project']
del policy_violations['version']

for violation_info in policy_violations.values():
    component_name = violation_info['bom_component']['componentName']
    component_version = violation_info['bom_component'].get('componentVersionName')
    component_url = violation_info['bom_component']['component']
    # if component-version URL is available use it, but if not revert to the component URL
    component_version_url = violation_info['bom_component'].get('componentVersion', component_url)
    component_license = ",".join([l['licenseDisplay'] for l in violation_info['bom_component']['licenses']])
    policies_in_violation = violation_info['policies_in_violation']['totalCount']
    for policy_violation in violation_info['policies_in_violation']['items']:
        pv_name = policy_violation['name']
        pv_description = policy_violation['description']
        overridable = policy_violation['overridable']
        severity = policy_violation['severity']
        html += """
            <tr>
                <td>{}</td>
                <td>{}</td>
                <td>{}</td>
                <td><a href={}>click here to view more info on this component from Black Duck</a></td>
                <td>{}</td>
                <td>{}</td>
                <td>{}</td>
                <td>{}</td>
            </tr>
        """.format(component_name, component_version, component_license, component_version_url, pv_name, pv_description, overridable, severity)

html += """
        </table>
    </body>
</html>
"""

if args.output_file:
    output_file = open(args.output_file, 'w')
else:
    output_file = sys.stdout

output_file.write(html)



