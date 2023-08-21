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
    re
    pathlib

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
import re
from pprint import pprint
from pathlib import Path
from spdx_tools.spdx.model.document import Document
from spdx_tools.spdx.validation.document_validator import validate_full_spdx_document
from spdx_tools.spdx.parser.error import SPDXParsingError
from spdx_tools.spdx.parser.parse_anything import parse_file

# TODO what happens if file doesn't exist?
# Returns SPDX Document object on success, otherwise exits on parse failure
# Input: file = Filename to process
# Returns: SPDX document object
def spdx_parse(file):
    print("Parsing SPDX file...")
    start = time.process_time()
    try:
        document: Document = parse_file(file)
        print(f"SPDX parsing took {time.process_time() - start} seconds")
        return(document)
    except SPDXParsingError:
        logging.exception("Failed to parse spdx file")
        sys.exit(1)

# Validates the SPDX file. Logs all validation messages as warnings.
def spdx_validate(document):
    print("Validating SPDX file...")
    start = time.process_time()
    validation_messages = validate_full_spdx_document(document)
    print(f"SPDX validation took {time.process_time() - start} seconds")

    # TODO is there a way to distinguish between something fatal and something
    # BD can deal with?
    # TODO - this can take forever, so add an optional --skip-validation flag
    for validation_message in validation_messages:
        # Just printing these messages intead of exiting. Later when we try to import
        # the file to BD, let's plan to exit if it fails. Seeing lots of errors in the
        # sample data.
        logging.warning(validation_message.validation_message)

# TODO is it possible to make this a case-insensitive match?
# Lookup the given matchname in the KB
# Logs a successful match
# Return the boolean purlmatch and matchname, which we might change from
#  its original value -- we will force it to be the same as the name in the KB
#  That way we can more accurately search the BOM later.
def find_comp_in_kb(matchname, extref):
    # KB lookup to check for pURL match
    purlmatch = False
    params = {
            'packageUrl': extref
    }
    # TODO any other action to take here?
    # We should probably track KB matches?
    for result in bd.get_items("/api/search/purl-components", params=params):
        # TODO do we need to worry about more than 1 match?
        purlmatch = True
        # in this event, override the spdx name and use the known KB name
        # TODO: is version mangling possible?
        if matchname != result['componentName']:
            print(f"Renaming {matchname} -> {result['componentName']}")
            return(purlmatch, result['componentName'])
    return(purlmatch, matchname)

# TODO is it possible to make this a case-insensitive match?
# Locate component name + version in BOM
# Returns True on success, False on failure
def find_comp_in_bom(bd, compname, compver, projver):
    have_match = False
    num_match = 0

    # Lookup existing SBOM for a match
    # This is a fuzzy match (see "react" for an example)
    params = {
        'q': [f"componentOrVersionName:{compname}"]
    }

    # Search BOM for specific component name
    comps = bd.get_resource('components', projver, params=params)
    for comp in comps:
        if comp['componentName'] != compname:
            # The BD API search is inexact. Force our match to be precise.
            continue
        # Check component name + version name
        try:
            if comp['componentVersionName'] == compver:
                return True
        except:
            # Handle situation where it's missing the version name for some reason
            print(f"comp {compname} in BOM has no version!")
            return False
    return False


# TODO is it possible to make this a case-insensitive match?
# Returns:
#  CompMatch - Contains matched component url, None for no match
#  VerMatch  - Contains matched component verison url, None for no match
def find_cust_comp(cust_comp_name, cust_comp_version):
    params = {
        'q': [f"name:{cust_comp_name}"]
    }

    matched_comp = None
    matched_ver = None
    # Relies on internal header
    headers = {'Accept': 'application/vnd.blackducksoftware.internal-1+json'}
    for comp in bd.get_resource('components', params=params, headers=headers):
        if cust_comp_name != comp['name']:
            # Skip it. We want to be precise in our matching, despite the API.
            continue
        matched_comp = comp['_meta']['href']
        # Check version
        for version in bd.get_resource('versions', comp):
            if cust_comp_version == version['versionName']:
                # Successfully matched both name and version
                matched_ver = version['_meta']['href']
                return(matched_comp, matched_ver)

    return(matched_comp, matched_ver)


# Returns URL of matching license
# Exits on failure, we assume it must pre-exist - TODO could probably just create this?
# Note: License name search is case-sensitive
def get_license_url(license_name):
    params = {
        'q': [f"name:{license_name}"]
    }
    for result in bd.get_items("/api/licenses", params=params):
        # Added precise matching in case of a situation like "NOASSERTION" & "NOASSERTION2"
        if (result['name'] == license_name):
            return(result['_meta']['href'])

    logging.error(f"Failed to find license {license_name}")
    sys.exit(1)

# Create a custom component
# Inputs:
#   name - Name of component to add
#   version - Version of component to add
#   license - License name
# Returns the URL for the newly created component version URL if successful
def create_cust_comp(name, version, license):
    print(f"Adding custom component: {name} {version}")
    license_url = get_license_url(license)
    data = {
        'name': name,
        'version' : {
          'versionName' : version,
          'license' : {
            'license' : license_url
          },
        }
    }
    response = bd.session.post("api/components", json=data)
    logging.debug(response)
    if response.status_code == 412:
        # Shouldn't be possible. We checked for existence earlier.
        logging.error(f"Component {name} already exists")
        sys.exit(1)

    if response.status_code != 201:
        # Shouldn't be possible. We checked for existence earlier.
        logging.error(response.json()['errors'][0]['errorMessage'])
        logging.error(f"Status code {response.status_code}")
        sys.exit(1)

    # Should be guaranteed 1 version because we just created it!
    for version in bd.get_items(response.links['versions']['url']):
        return(version['_meta']['href'])


# Create a version for a custom component that already exists
#
# Inputs:
#   comp_url - API URL of the component to update
#   version  - Version to add to existing component
#   license  - License to use for version
#
# Returns: component version url just created
def create_cust_comp_ver(comp_url, version, license):
    license_url = get_license_url(license)
    data = {
      'versionName' : version,
      'license' : {
          'license' : license_url
      },
    }
    response = bd.session.post(comp_url + "/versions", json=data)
    logging.debug(response)
    if response.status_code == 412:
        # Shouldn't be possible. We checked for existence earlier.
        logging.error(f"Version {version} already exists for component")
        sys.exit(1)

    # necessary?
    if response.status_code != 201:
        logging.error(f"Failed to add Version {version} to component")
        sys.exit(1)

    return(response.links['self']['url'])

# Add specified component version url to our project+version SBOM
# Inputs: 
#   proj_version_url: API URL for a project+version to update
#   comp_ver_url: API URL of a component+version to add
def add_to_sbom(proj_version_url, comp_ver_url):
    data = {
        'component': comp_ver_url
    }
    response = bd.session.post(proj_version_url + "/components", json=data)
    if (response.status_code != 200):
        logging.error(response.json()['errors'][0]['errorMessage'])
        logging.error(f"Status code {response.status_code}")
        sys.exit(1)

parser = argparse.ArgumentParser(description="Parse SPDX file and verify if component names are in current SBOM for given project-version")
parser.add_argument("--base-url", required=True, help="Hub server URL e.g. https://your.blackduck.url")
parser.add_argument("--token-file", dest='token_file', required=True,help="Access token file")
parser.add_argument("--spdx-file", dest='spdx_file', required=True, help="SPDX input file")
parser.add_argument("--out-file", dest='out_file', required=True, help="Unmatched components file")
parser.add_argument("--project", dest='project_name', required=True, help="Project that contains the BOM components")
parser.add_argument("--version", dest='version_name', required=True, help="Version that contains the BOM components")
parser.add_argument("--license", dest='license_name', required=False, default="NOASSERTION", help="License name to use for custom components")
parser.add_argument("--no-verify", dest='verify', action='store_false', help="Disable TLS certificate verification")
parser.add_argument("--no-spdx-validate", dest='spdx_validate', action='store_false', help="Disable SPDX validation")
args = parser.parse_args()

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] {%(module)s:%(lineno)d} %(levelname)s - %(message)s"
)

if (Path(args.spdx_file).is_file()):
    document = spdx_parse(args.spdx_file)
    if (args.spdx_validate):
        spdx_validate(document)
else:
    logging.error(f"Invalid SPDX file: {args.spdx_file}")
    sys.exit(1)

with open(args.token_file, 'r') as tf:
    access_token = tf.readline().strip()

bd = Client(base_url=args.base_url, token=access_token, verify=args.verify)

# some little debug/test stubs
# TODO: delete these
#comp_ver_url = create_cust_comp("MY COMPONENT z", "1", args.license_name)
#
#comp_url = "https://purl-validation.saas-staging.blackduck.com/api/components/886c04d4-28ce-4a27-be4c-f083e73a9f69"
#comp_ver_url = create_cust_comp_ver(comp_url, "701", "NOASSERTION")
#
#pv = "https://purl-validation.saas-staging.blackduck.com/api/projects/14b714d0-fa37-4684-86cc-ed4e7cc64b89/versions/b8426ca3-1e27-4045-843b-003eca72f98e"
#cv = "https://purl-validation.saas-staging.blackduck.com/api/components/886c04d4-28ce-4a27-be4c-f083e73a9f69/versions/56f64b7f-c284-457d-b593-0cf19a272a19"
#add_to_sbom(pv, cv)
#quit()

# Open unmatched component file
# Will save name, spdxid, version, and origin/purl for later in json format:
#    "name": "react-bootstrap",
#    "spdx_id": "SPDXRef-Pkg-react-bootstrap-2.1.2-30223",
#    "version": "2.1.2",
#    "origin": null
# TODO this try/except actually isn't right
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
proj_version_url = version['_meta']['href']

logging.debug(f"Found {project['name']}:{version['versionName']}")


# situations to consider + actions
# 1) No purl available : check SBOM for comp+ver, then add cust comp + add to SBOM
# 2) Have purl + found in KB 
#    - In SBOM? -> done
#    - Else -> add known KB comp to SBOM
#       *** this shouldn't happen in theory
# 3) Have purl + not in KB (main case we are concerned with)
#     - In SBOM? (maybe already added or whatever?) -> done
#     - Else -> add cust comp + add to SBOM (same as 1)

# Stats to track
bom_matches = 0
kb_matches = 0
nopurl = 0
nomatch = 0
package_count = 0
cust_comp_count = 0
cust_ver_count = 0
# Saving all encountered components by their name+version (watching for repeats)
packages = {}

# Walk through each component in the SPDX file
for package in document.packages:
    package_count += 1
    # We hope we'll have an external reference (pURL), but we might not.
    extref = None
    purlmatch = False
    matchname = package.name
    matchver = package.version
    # Tracking unique package name + version from spdx file 
    packages[matchname+matchver] = packages.get(matchname+matchver, 0) + 1

    # NOTE: BD can change the original component name
    # EX: "React" -> "React from Facebook"
    if package.external_references:
        inkb, matchname = find_comp_in_kb(matchname, package.external_references[0].locator)
        if inkb: kb_matches += 1
    else:
        nopurl += 1
        print("No pURL found for component: ")
        print("  " + package.name)
        print("  " + package.spdx_id)
        print("  " + package.version)

    if find_comp_in_bom(bd, matchname, matchver, version):
        bom_matches += 1
        #print(" Found comp match in BOM: " + matchname + matchver)
    else:
        nomatch += 1
        comp_data = {
            "name": package.name,
            "spdx_id": package.spdx_id,
            "version": package.version,
            "origin": extref
        }
        comps_out.append(comp_data)
        
        # Check if custom component already exists
        comp_url, comp_ver_url = find_cust_comp(package.name, package.version)
        
        if not comp_url:
            # Custom component did not exist, so create it
            cust_comp_count += 1
            comp_ver_url = create_cust_comp(package.name, package.version,
              args.license_name, approval)
        elif comp_url and not comp_ver_url:
            # Custom component existed, but not the version we care about
            cust_ver_count += 1
            print(f"Adding version {package.version} to custom component {package.name}")
            comp_ver_url = create_cust_comp_ver(comp_url, package.version, args.license_name)
            # DEBUG
            quit()
        else:
            print("Custom component already exists, not in SBOM")

        # is this possible? i don't think so
        assert(comp_ver_url), f"No comp_ver URL found for {package.name} {package.version}"
        print(f"Adding component to SBOM: {package.name} {package.version}")
        add_to_sbom(proj_version_url, comp_ver_url)
        
# Save unmatched components
json.dump(comps_out, outfile)
outfile.close()

print("\nStats: ")
print("------")
print(f" SPDX packages processed: {package_count}")
print(f" Non matches: {nomatch}")
print(f" KB matches: {kb_matches}")
print(f" BOM matches: {bom_matches}")
print(f" Packages missing purl: {nopurl}")
print(f" Custom components created: {cust_comp_count}")
print(f" Custom component versions created: {cust_ver_count}")
#pprint(packages)
print(f" {len(packages)} unique packages processed")
