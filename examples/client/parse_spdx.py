'''
Created on August 15, 2023
@author: swright

##################### DISCLAIMER ##########################
##  This script was created for a specific purpose and   ##
##   SHOULD NOT BE USED as a general purpose utility.    ##
##   For general purpose utility use                     ##
##      /examples/client/generate_sbom.py                ##
###########################################################

Copyright (C) 2023 Synopsys, Inc.
http://www.blackducksoftware.com/

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

This script will parse a provided SPDX file and import the SBOM to the
specified Project Name and Project Version. 

Then it will search each component specified in the SPDX file to determine
if the component was succesfully imported. Any missing components will be
added as a custom component and then added to the Project+Verion's BOM.

Requirements

- python3 version 3.8 or newer recommended
- the following packages are used by the script and should be installed 
  prior to use:	
    argparse
    blackduck
    sys
    logging
    time
    json
    pprint
    spdx_tools

- Blackduck instance
- API token with sufficient privileges to perform project version phase 
  change.

Install python packages with the following command:

 pip3 install argparse blackduck sys logging time json spdx_tools

usage: parse_spdx.py [-h] --base-url BASE_URL --token-file TOKEN_FILE --spdx-file SPDX_FILE --out-file OUT_FILE --project PROJECT_NAME --version VERSION_NAME [--no-verify]

Parse SPDX file and verify if component names are in current SBOM for given project-version

optional arguments:
  -h, --help            show this help message and exit
  --base-url BASE_URL   Hub server URL e.g. https://your.blackduck.url
  --token-file TOKEN_FILE
                        Access token file
  --spdx-file SPDX_FILE
                        SPDX input file
  --out-file OUT_FILE   Unmatched components file
  --project PROJECT_NAME
                        Project that contains the BOM components
  --version VERSION_NAME
                        Version that contains the BOM components
  --no-verify           Disable TLS certificate verification

'''

from blackduck import Client
import argparse
import sys
import logging
import time
import json
from pprint import pprint
from spdx_tools.spdx.model.document import Document
from spdx_tools.spdx.parser.error import SPDXParsingError
from spdx_tools.spdx.parser.parse_anything import parse_file

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] {%(module)s:%(lineno)d} %(levelname)s - %(message)s"
)

parser = argparse.ArgumentParser(description="Parse SPDX file and verify if component names are in current SBOM for given project-version")
parser.add_argument("--base-url", required=True, help="Hub server URL e.g. https://your.blackduck.url")
parser.add_argument("--token-file", dest='token_file', required=True,help="Access token file")
parser.add_argument("--spdx-file", dest='spdx_file', required=True, help="SPDX input file")
parser.add_argument("--out-file", dest='out_file', required=True, help="Unmatched components file")
parser.add_argument("--project", dest='project_name', required=True, help="Project that contains the BOM components")
parser.add_argument("--version", dest='version_name', required=True, help="Version that contains the BOM components")
parser.add_argument("--no-verify", dest='verify', action='store_false', help="Disable TLS certificate verification")
args = parser.parse_args()

# Parse SPDX file. This can take a very long time, so do this first.
# Returns a Document object on success, otherwise raises an SPDXParsingError
try:
    print("Reading SPDX file...")
    start = time.process_time()
    document: Document = parse_file(args.spdx_file)
    print(f"SPDX parsing took {time.process_time() - start} seconds")
except SPDXParsingError:
    logging.exception("Failed to parse spdx file")
    sys.exit(1)

with open(args.token_file, 'r') as tf:
    access_token = tf.readline().strip()

bd = Client(base_url=args.base_url, token=access_token, verify=args.verify)

# Open unmatched component file
# Will save name, spdxid, version, and origin/purl (if available) like so:
#    "name": "react-bootstrap",
#    "spdx_id": "SPDXRef-Pkg-react-bootstrap-2.1.2-30223",
#    "version": "2.1.2",
#    "origin": null
try: outfile = open(args.out_file, 'w')
except:
    logging.exception("Failed to open file for writing: " + args.out_file)
    sys.exit(1)

# Saved component data to write to file
comps_out = []

# Fetch Project (can only have 1)
params = {
    'q': [f"name:{args.project_name}"]
}
projects = [p for p in bd.get_resource('projects', params=params)
  if p['name'] == args.project_name]
assert len(projects) == 1, \
  f"There should one project named {args.project_name}. Found {len(projects)}"
project = projects[0]

# Fetch Version (can only have 1)
params = {
    'q': [f"versionName:{args.version_name}"]
}
versions = [v for v in bd.get_resource('versions', project, params=params)
  if v['versionName'] == args.version_name]
assert len(versions) == 1, \
  f"There should be 1 version named {args.version_name}. Found {len(versions)}"
version = versions[0]

logging.debug(f"Found {project['name']}:{version['versionName']}")

# Can now access attributes from the parsed document
# Note: The SPDX module renames tags slightly from the original json format.
#print(f"Parsed document name: {document.creation_info.name}")
#creators_as_str = ", ".join([creator.to_serialized_string() for creator in document.creation_info.creators])
#print(f"Created on {document.creation_info.created} by {creators_as_str}")

# A test of multiple search params....
# this works, but it's an OR, not AND
#  - we'll find everything with name OR version match
#name = "micromatch"
#ver = "4.0.2"
#params = {
#    'q': [f"componentOrVersionName:{name}"],
#    'q': [f"componentOrVersionName:{ver}"],
#}
#comps = bd.get_resource('components', version, params=params)
#for comp in comps:
#    print(comp['componentName'])

# A test of custom comp search params....
#name = "swrightcomp"
#params = {
#    'q': [f"componentOrVersionName:{name}"],
#}
#comps = bd.get_resource('components', version, params=params)
#for comp in comps:
#    print(comp['componentName'])
#quit()
# Some fun stats to track as we go
matches = 0
nopurl = 0
nomatch = 0

# Walk through each component in the SPDX file
for package in document.packages:
    # spdx-tools module says only name, spdx_id, download_location are required
    # We hope we'll have an external reference (pURL), but we might not.
    extref = None

    # NOTE: BD can mangle the original component name
    # EX: "React" -> "React from Facebook"
    if package.external_references:
        print(" Found external reference: " + package.external_references[0].locator)
        extref = package.external_references[0].locator

        # TODO lookup KB api here
        #/api/search/kb-components?filter=pURL:<name>

        # TODO: if lookup successful, next in loop
        # if <lookup KB API true>:
        #   continue
    else:
        nopurl += 1
        print(" No pURL found for component: ")
        print("  " + package.name)
        print("  " + package.spdx_id)
        print("  " + package.version)

    # Lookup existing SBOM for a match (just on name to start)
    # This is a fuzzy match (see "react" for an example)
    params = {
        'q': [f"componentOrVersionName:{package.name}"]
    }
    
    # Search BOM for specific component name
    comps = bd.get_resource('components', version, params=params)
    # TODO investigate searching tag here
    have_match = False
    num_match = 0
    for comp in comps:
        #pprint(bd.list_resources(comp))
        #pprint(comp)
        # Check component name + version name
        if comp['componentVersionName'] == package.version:
            have_match = True
            num_match += 1
            # TODO need to worry about multiple matches?
            break

    if have_match:
        matches += 1
        print("Found comp match in BOM: " + package.name)
    else:
        # TODO:
        # 1) check if in custom component list (system-wide)
        # 2) add if not there
        # 3) add to project BOM
        nomatch += 1
        print("May need to add this custom comp: " + package.name)
        comp_data = {
            "name": package.name,
            "spdx_id": package.spdx_id,
            "version": package.version,
            "origin": extref
        }
        comps_out.append(comp_data)

# Save unmatched components
json.dump(comps_out, outfile)
outfile.close()

print("Stats: ")
print(f" Non matches: {nomatch}")
print(f" Matches: {matches}")
print(f" Packages missing purl: {nopurl}")

# Parsed SPDX package data looks like
# Package(spdx_id='SPDXRef-Pkg-micromatch-4.0.2-30343', 
#	name='micromatch', 
#	download_location=NOASSERTION, 
#	version='4.0.2', 
#	file_name=None, 
#	supplier=None, 
#	originator=None, 
#	files_analyzed=True, 
#	verification_code=PackageVerificationCode(value='600ce1a1b891b48a20a3d395e4714f854dc6ced4', 
#	  excluded_files=[]), 
#	checksums=[], 
#	homepage='https://www.npmjs.com/package/micromatch', 
#	source_info=None, 
#	license_concluded=LicenseSymbol('MIT', 
#	is_exception=False), 
#	license_info_from_files=[LicenseSymbol('Apache-2.0', 
#  	  is_exception=False), 
#	  LicenseSymbol('BSD-2-Clause', 
#	  is_exception=False), 
#	  LicenseSymbol('ISC', 
#	  is_exception=False), 
#	  LicenseSymbol('JSON', 
#	  is_exception=False), 
#	  LicenseSymbol('LicenseRef-Historical-Permission-Notice-and-Disclaimer---sell-variant', 
#	  is_exception=False), 
#	  LicenseSymbol('LicenseRef-MIT-Open-Group-variant', 
#	  is_exception=False)], 
#	license_declared=LicenseSymbol('MIT', 
#	  is_exception=False), 
#	license_comment=None, 
#	copyright_text=NOASSERTION, 
#	summary=None, 
#	description=None, 
#	comment=None, 
#	external_references=[ExternalPackageRef(category=<ExternalPackageRefCategory.PACKAGE_MANAGER: 2>, 
#	  reference_type='purl', 
#	  locator='pkg:npm/micromatch@4.0.2', 
#	  comment=None)], 
#	attribution_texts=[], 
#	primary_package_purpose=None, 
#	release_date=None, 
#	built_date=None, 
#	valid_until_date=None)
