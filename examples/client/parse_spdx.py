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
- The following packages are used by the script and should be installed 
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

usage: parse_spdx.py [-h] --base-url BASE_URL --token-file TOKEN_FILE
                     --spdx-file SPDX_FILE --out-file OUT_FILE --project
                     PROJECT_NAME --version VERSION_NAME
                     [--license LICENSE_NAME] [--no-verify]
                     [--no-spdx-validate]

Parse SPDX file and verify if component names are in current SBOM for given
project-version

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
  --license LICENSE_NAME
                        License name to use for custom components (default:
                        NOASSERTION)
  --no-verify           Disable TLS certificate verification
  --no-spdx-validate    Disable SPDX validation

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
# Input: SPDX document object
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

# Returns MIME type to provide to scan API
# Input: filename to check
def get_sbom_mime_type(filename):
    with open(filename, 'r') as f:
        data = f.readlines()
        content = " ".join(data)
    if 'CycloneDX' in content:
        return 'application/vnd.cyclonedx'
    if 'SPDX' in content:
        return 'application/spdx'
    return None

# Poll for successful scan of SBOM.
# Input: Name of SBOM document (not the filename, the name defined inside the json body)
# Returns on success. Errors will result in fatal exit.
def poll_for_upload(sbom_name):
    max_retries = 30
    sleep_time = 10
    matched_scan = False

    # TODO also check for api/projects/<ver>/versions/<ver>/codelocations
    # -- status - operationNameCode = ServerScanning, operationName=Scanning, status
    #    -- should be COMPLETED, not IN_PROGRESS
    #    -- operatinName: Scanning
    # Search for the latest scan matching our SBOM
    # This might be a risk for a race condition
    params = {
        'q': [f"name:{sbom_name}"],
        'sort': ["updatedAt: ASC"]
    }

    cls = bd.get_resource('codeLocations', params=params)
    for cl in cls:
        # Force exact match of: spdx_doc_name + " spdx/sbom"
        # BD appends the "spdx/sbom" string to the name.
        if cl['name'] != sbom_name + " spdx/sbom":
            continue

        matched_scan = True
        for link in (cl['_meta']['links']):
            # Locate the scans URL to check for status
            if link['rel'] == "scans":
                summaries_url = link['href']
                break

        assert(summaries_url)
        params = {
            'sort': ["updatedAt: ASC"]
        }

        while (max_retries):
            max_retries -= 1
            for item in bd.get_items(summaries_url, params=params):
                # Only checking the first item as it's the most recent
                if item['scanState'] == "SUCCESS":
                    print("Scan complete")
                    return
                elif item['scanState'] == "FAILURE":
                    logging.error(f"SPDX Scan Failure: {item['statusMessage']}")
                    sys.exit(1)
                else:
                    # Only other state should be "STARTED" -- keep polling
                    print(f"Waiting for status success, currently: {item['scanState']}")
                    time.sleep(sleep_time)
                    # Break out of for loop so we always check the most recent
                    break

    # Handle various errors that might happen
    if max_retries == 0:
        logging.error("Failed to verify successful SPDX Scan in {max_retries * sleep_time} seconds")
    elif not matched_scan:
        logging.error(f"No scan found for SBOM: {sbom_name}")
    else:
        logging.error(f"Unable to verify successful scan of SBOM: {sbom_name}")

    sys.exit(1)

# TODO do we care about project_groups?
# Upload provided SBOM file to Black Duck
# Inputs:
#   filename - Name of file to upload
#   project - Project name to map to
#   version - Version name to map to
def upload_sbom_file(filename, project, version):
    mime_type = get_sbom_mime_type(filename)
    if not mime_type:
        logging.error(f"Could not identify file content for {filename}")
        sys.exit(1)
    files = {"file": (filename, open(filename,"rb"), mime_type)}
    fields = {"projectName": project, "versionName": version}
    response = bd.session.post("/api/scan/data", files = files, data=fields)
    logging.debug(response)

    if response.status_code == 409:
        logging.error(f"File {filename} is already mapped to a different project version")

    if response.status_code != 201:
        logging.error(f"Failed to upload SPDX file:")
        try:
            pprint(response.json()['errorMessage'])
        except:
            logging.error(f"Status code {response.status_code}")
        sys.exit(1)


# Lookup the given pURL in the BD KB.
#
# Inputs:
#   extref - pURL to look up
#
# Returns:
#  If match: API matching data (the "result" object)
#  No match: None
def find_comp_in_kb(extref):
    params = {
            'packageUrl': extref
    }
    for result in bd.get_items("/api/search/purl-components", params=params):
        # Should be exactly 1 match when successful
        return(result)

    # Fall through -- lookup failed
    return(None)


# Locate component name + version in BOM
# Inputs:
#   compname - Component name to locate
#   compver  - Component version to locate
#   projver  - Project version to locate component in BOM
#
# Returns: True on success, False on failure
def find_comp_in_bom(compname, compver, projver):
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


# Verifies if a custom component and version already exist in the system
#
# Inputs:
#   compname - Component name to locate
#   compver  - Component version to locate
# Returns:
#  CompMatch - Contains matched component url, None for no match
#  VerMatch  - Contains matched component verison url, None for no match
def find_cust_comp(compname, compver):
    params = {
        'q': [f"name:{compname}"]
    }

    matched_comp = None
    matched_ver = None
    # Warning: Relies on internal header
    headers = {'Accept': 'application/vnd.blackducksoftware.internal-1+json'}
    for comp in bd.get_resource('components', params=params, headers=headers):
        if compname == comp['name']:
            # Force exact match
            matched_comp = comp['_meta']['href']
        else:
            # Keep checking search results
            continue

        # Check version
        for version in bd.get_resource('versions', comp):
            if compver == version['versionName']:
                # Successfully matched both name and version
                matched_ver = version['_meta']['href']
                return(matched_comp, matched_ver)

        # If we got this far, break out of the loop
        # We matched the component, but not the version
        break

    return(matched_comp, matched_ver)

# Find URL of license to use for custom compnent creation
# Inputs:
#   license_name - Name of license to locate (case-sensitive)
#
# Returns: URL of license successfully matched. Failures are fatal.
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
# Prints out any errors encountered. Errors are fatal.
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
parser.add_argument("--license", dest='license_name', required=False, default="NOASSERTION", help="License name to use for custom components (default: NOASSERTION)")
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
    logging.error(f"Could not open SPDX file: {args.spdx_file}")
    sys.exit(1)

with open(args.token_file, 'r') as tf:
    access_token = tf.readline().strip()

global bd
bd = Client(base_url=args.base_url, token=access_token, verify=args.verify)

#pprint(bd.list_resources())

upload_sbom_file(args.spdx_file, args.project_name, args.version_name)
# This will exit if it fails
poll_for_upload(document.creation_info.name)

# some debug/test stubs
# TODO: delete these
#ver="https://purl-validation.saas-staging.blackduck.com/api/projects/c2b4463f-7996-4c45-8443-b69b4f82ef1d/versions/67e4f6f5-2f42-42c4-9b69-e39bad55f907"
#comp = "https://purl-validation.saas-staging.blackduck.com/api/components/fc0a76fe-70a4-4afa-9a94-c3c22d63454f/versions/fabaabb9-3b9a-4b5f-850a-39fe84c4cfc4"
#add_to_sbom(ver, comp)
#quit()

#matchcomp, matchver = find_cust_comp("ipaddress", "1.0.23")
#if matchcomp:
#    print("matched comp")
#else:
#    print("no comp match")
#if matchver:
#    print("matched ver")
#else:
#    print("no ver match")
#comp_ver_url = create_cust_comp("MY COMPONENT z", "1", args.license_name)
#
#comp_url = "https://purl-validation.saas-staging.blackduck.com/api/components/886c04d4-28ce-4a27-be4c-f083e73a9f69"
#comp_ver_url = create_cust_comp_ver(comp_url, "701", "NOASSERTION")
#
#pv = "https://purl-validation.saas-staging.blackduck.com/api/projects/14b714d0-fa37-4684-86cc-ed4e7cc64b89/versions/b8426ca3-1e27-4045-843b-003eca72f98e"
#cv = "https://purl-validation.saas-staging.blackduck.com/api/components/886c04d4-28ce-4a27-be4c-f083e73a9f69/versions/56f64b7f-c284-457d-b593-0cf19a272a19"
#add_to_sbom(pv, cv)
#quit()

# Open unmatched component file to save name, spdxid, version, and
# origin/purl for later in json format
# TODO this try/except isn't quite right
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
    print(f"Processing SPDX package: {matchname} {matchver}....")
    # Tracking unique package name + version from spdx file 
    packages[matchname+matchver] = packages.get(matchname+matchver, 0) + 1

    if package.external_references:
        # TODO need to handle the possiblity of:
        # A) multiple extrefs
        # B) an extref that is not a purl
        #    --  referenceType should be "purl" - ignore others?
        kb_match = find_comp_in_kb(package.external_references[0].locator)
        if (kb_match):
            # Update package name and version to reflect the KB name/ver
            print(f" KB match for {package.name} {package.version}")
            kb_matches+=1
            matchname = kb_match['componentName']
            matchver = kb_match['versionName']
        else:
            print(f" No KB match for {package.name} {package.version}")
    else:
        nopurl += 1
        kb_match = None
        print(f"No pURL provided for {package.name} {package.version}")

    if find_comp_in_bom(matchname, matchver, version):
        bom_matches += 1
        print(f" Found component in BOM: {matchname} {matchver}")
        # It's in the BOM so we are happy
        # Everything else below is related to adding to the BOM
        continue

    # If we've gotten this far, the package is not in the BOM.
    # Now we need to figure out:
    #  - Is it already in the KB and we need to add it? (should be rare)
    #  - Do we need to add a custom component?
    #  - Do we need to add a version to an existing custom component?
    nomatch += 1
    print(f" Not present in BOM: {matchname} {matchver}")
    comp_data = {
        "name": package.name,
        "spdx_id": package.spdx_id,
        "version": package.version,
        "origin": extref
    }
    comps_out.append(comp_data)

    # KB match was successful, but it wasn't in the BOM for some reason
    if kb_match:
        print(f" WARNING: {matchname} {matchver} in KB but not in SBOM")
        add_to_sbom(proj_version_url, kb_match['version'])
        # temp debug to find this case
        quit()
        # short-circuit the rest
        continue

    # Check if custom component already exists
    comp_url, comp_ver_url = find_cust_comp(package.name, package.version)

    if not comp_url:
        # Custom component did not exist, so create it
        cust_comp_count += 1
        comp_ver_url = create_cust_comp(package.name, package.version,
          args.license_name)
    elif comp_url and not comp_ver_url:
        # Custom component existed, but not the version we care about
        cust_ver_count += 1
        print(f" Adding version {package.version} to custom component {package.name}")
        comp_ver_url = create_cust_comp_ver(comp_url, package.version, args.license_name)
    else:
        print(" Custom component already exists, not in SBOM")

    # Shouldn't be possible
    assert(comp_ver_url), f"No component URL found for {package.name} {package.version}"

    print(f" Adding component to SBOM: {package.name} aka {matchname} {package.version}")
    add_to_sbom(proj_version_url, comp_ver_url)
        
# Save unmatched components
json.dump(comps_out, outfile)
outfile.close()

print("\nStats: ")
print("------")
print(f" SPDX packages processed: {package_count}")
print(f" Packages missing from BOM: {nomatch}")
print(f" BOM matches: {bom_matches}")
print(f" KB matches: {kb_matches}")
print(f" Packages missing purl: {nopurl}")
print(f" Custom components created: {cust_comp_count}")
print(f" Custom component versions created: {cust_ver_count}")
#pprint(packages)
print(f" {len(packages)} unique packages processed")
