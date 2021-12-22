'''
Created on Nov 18, 2019

@author: gsnyder

Get all in-use licenses, their components, and the project-versions using those components

Note: This program uses an internal API endpoint which can, and probably will, break at some future date
'''

'''
Copyright (C) 2021 Synopsys, Inc.
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
import logging
import sys

# pip install xlwt
import xlwt
from xlwt import Workbook

from blackduck.HubRestApi import HubInstance
from pprint import pprint


parser = argparse.ArgumentParser("Retrieve all in-use licenses and write out which components and project-versions use them in an Excel (xls) worksheet")
parser.add_argument('-f', '--file', default="licenses_inuse.xls", help="Specificy what file to write the results into")
args = parser.parse_args()

logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stdout, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

def write_to_sheet(sheet, data):
    for d in data:
        sheet.write(d[0], d[1], d[2])

hub = HubInstance()

# WARNING:
#   This uses an internal, un-supported API endpoint (see below) 
#   and therefore could break in future versions of Black Duck. 
#   This script was tested with BD v2021.8.2. 
#
# An ER has been filed in Synopsys Jira ticket HUB-26144 to make a 
# in-use filter part of a public endpoint for retrieving licenses

inuse_licenses_url = hub.get_apibase() + "/internal/composite/licenses?filter=inUse:true"
logging.debug("Retrieving in-use licenses using url {}".format(inuse_licenses_url))
custom_headers={'Accept': 'application/vnd.blackducksoftware.internal-1+json'}
logging.debug(f"custom_headers: {custom_headers}")
response = hub.execute_get(inuse_licenses_url, custom_headers=custom_headers)
inuse_licenses = response.json().get('items', [])
logging.debug("Found {} licenses in use".format(len(inuse_licenses)))

wb = Workbook()
inuse_licenses_sheet = wb.add_sheet('In-use licenses')
data_to_write = [
    (0,0,"license"),
    (0,1,"component name"),
    (0,2,"component version"),
    (0,3,"project name"),
    (0,4,"project version"),
    (0,5,"project URL"),
    (0,6,"project-version URL"),
    (0,7,"project-version distribution type"),
    (0,8,"project-version phase")
]
write_to_sheet(inuse_licenses_sheet, data_to_write)

# Add component, project references to the in-use licenses
offset = 0
for license in inuse_licenses:
    usages_url = hub.get_link(license, "usages")
    usages_url = usages_url + "?limit=1000"
    logging.debug("Retrieving usages for license {}".format(license['name']))
    response = hub.execute_get(usages_url)
    usages = response.json().get('items', [])
    logging.debug("Found {} usages for license {}".format(len(usages), license['name']))
    for usage in usages:
        component_version = usage.get('componentVersionName', 'Unknown')
        component_name_str = f"{usage['componentName']}:{component_version}"
        # usage === component that referenced the license
        logging.debug("Retrieving project-versions that use component {}:{} (license={}".format(
            usage['componentName'], component_version, license['name']))
        component_url = hub.get_link(usage, "componentVersion") or hub.get_link(usage, 'component')
        #TODO Figure out how to handle the case where the component version is not known
        logging.debug(f"component_url: {component_url}")
        if not component_url:
            logging.warning(f"Component {component_name_str} had no URL, skipping...")
            continue
        else:
            logging.debug(f"Retrieving component info for {component_name_str}")
        response = hub.execute_get(component_url)
        component = response.json()
        usage['component_details'] = component
        project_version_references_url = hub.get_link(component, "references")
        if not project_version_references_url:
            logging.warning(f"Component {component_name_str} has no 'references' link, skipping...")
            continue
        else:
            logging.debug(f"Retrieving project references for {component_name_str}")
        project_version_references_url = project_version_references_url + "?limit=1000"
        response = hub.execute_get(project_version_references_url)
        project_references = response.json().get('items', [])
        logging.debug("found {} project references".format(len(project_references)))
        usage['component_details']['project_references'] = project_references
        data_to_write = []
        if project_references:
            for i, project_ref in enumerate(project_references):
                row = offset + i + 1
                logging.debug("Adding license {}, used in component {}:{}, and project-version {}:{} to row {}".format(
                    license['name'], usage['componentName'], component_version, project_ref['projectName'], project_ref['versionName'], row))
                data_to_write.extend([
                    (row, 0, license['name']),
                    (row, 1, usage['componentName']),
                    (row, 2, component_version),
                    (row, 3, project_ref['projectName']),
                    (row, 4, project_ref['versionName']),
                    (row, 5, project_ref['projectUrl']),
                    (row, 6, project_ref['projectVersionUrl']),
                    (row, 7, project_ref['distribution']),
                    (row, 8, project_ref['phase'])
                ])
        else:
            row = offset + 1
            data_to_write.extend([
                (row, 0, license['name']),
                (row, 1, usage['componentName']),
                (row, 2, component_version),
                (row, 3, "None"),
                (row, 4, "None"),
                (row, 5, "NA"),
                (row, 6, "NA"),
                (row, 7, "NA"),
                (row, 8, "NA")
            ])

        logging.debug("writing data to excel sheet".format(len(data_to_write)))
        write_to_sheet(inuse_licenses_sheet, data_to_write)
        offset += max(len(project_references), 1)
        logging.debug("Wrote {} rows of data, offset is now {}".format(max(len(project_references), 1), offset))
wb.save(args.file)
