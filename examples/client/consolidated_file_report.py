'''
Created on August 30, 2023

@author: mkoishi

Generate reports which consolidates information on BOM components, versions with license information, BOM files with
license and copyright information from KB and license search (discoveries - file licenses or file copyrights), 
and BlackDuck unmatched files in the target source code.

Copyright (C) 2023 Synopsys, Inc.
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
import os
import re
import time
import subprocess
import json
import traceback
import copy
import ijson
from json2html import *
from blackduck import Client
from zipfile import ZipFile

program_description = \
'''This script collects BlackDuck reports for version details and discoveries and generates new reports.
The newly generated reports are a report of BOM component-versions with license information, a report of BOM files that consolidates licenses and copyright texts information from KB and discoveries (e.g., file licenses, file copyrights), and a report of BlackDuck unmatched files.
The generated reports are found in a folder named "blackduck_consolidated_file_report"
Synopsys-Detect is executed from the script unless skip-detect option is chosen. Synopsys-Detect runs in synchronous mode and please consider adjusting the "detect.timeout" detect parameter if completion of Synopsys-Detect is estimated to take longer.

Config file:
API Token, hub URL and two more options need to be placed in the .restconfig.json file that must be placed in the same folder where this script resides.
For more information, please find the instructions in the linked contents at https://community.synopsys.com/s/article/How-to-use-the-hub-rest-api-python-for-Black-Duck

Pre-requisites:
1) python (>=3.5) and pip are installed.
2) Install PyPI modules "blackduck", "ijson" and "json2html.

Examples:
1) If Synopsys-Detect is wanted to execute prior to the HTML report generation and the report should include file-copyright texts, then
python3 ./consolidated_file_report.py <YOUR_BD_PROJECT_NAME> <YOUR_BD_PROJECT_VERSION_NAME> \
-f html -cl 2 -rr 100 \
-dp detect.blackduck.signature.scanner.snippet.matching=SNIPPET_MATCHING \
detect.blackduck.signature.scanner.license.search=true \
detect.blackduck.signature.scanner.copyright.search=true \
detect.source.path=<YOUR_TARGET_SOURCE_PATH> \
detect.timeout=1800 \
blackduck.trust.cert=true

Note: blackduck.trust.cert=true is not recommended in the production environment.

2) If execution of Synopsys-Detect is wanted to bypass and no copyright texts are needed in the file report, then
python3 ./consolidated_file_report.py <YOUR_BD_PROJECT_NAME> <YOUR_BD_PROJECT_VERSION_NAME> \
-f html -sd -rr 100 -dp detect.source.path=<YOUR_TARGET_SOURCE_PATH>

Note: Please provide -dp detect.source.path parameter. If otherwise, the script has no clue for the target source folder.
'''

# Synopsys Detect parameters
DOWNLOAD_DETECT = ["curl", "-s", "-L", "https://detect.synopsys.com/detect8.sh"]
BLACKDUCK_URL = "--blackduck.url="
BLACKDUCK_TOKEN = "--blackduck.api.token="
BLACKDUCK_PROJECT = "--detect.project.name="
BLACKDUCK_VERSION = "--detect.project.version.name="
BLACKDUCK_WAIT = "--detect.wait.for.results=true"
ENV_DETECT_VERSION = "DETECT_LATEST_RELEASE_VERSION"
# BD report general
BLACKDUCK_REPORT_MEDIATYPE = "application/vnd.blackducksoftware.report-4+json"
blackduck_report_download_api = "/api/projects/{projectId}/versions/{projectVersionId}/reports/{reportId}/download"
blackduck_link_component_ui_api = "/api/projects/{projectId}/versions/{projectVersionId}/components"
blackduck_link_snippet_ui_api = "/api/projects/{projectId}/versions/{projectVersionId}/source-trees"
# BD version details report
blackduck_create_version_report_api = "/api/versions/{projectVersionId}/reports"
blackduck_version_report_filename = "./blackduck_version_report_for_{projectVersionId}.zip"
# BD discoveries report
blackduck_create_discoveries_report_api = "/api/versions/{projectVersionId}/license-reports"
blackduck_discoveries_report_filename = "./blackduck_discoveries_report_for_{projectVersionId}.zip"
# Consolidated report
BLACKDUCK_VERSION_MEDIATYPE = "application/vnd.blackducksoftware.status-4+json"
BLACKDUCK_VERSION_API = "/api/current-version"
BLACKDUCK_SOURCE_PATH = "detect.source.path"
REPORT_DIR = "./blackduck_consolidated_file_report"
REPORT_HEADER = "/header_report"
REPORT_OS_FILE = "/os_file_report"
REPORT_COMPONENT_BOM = "/component_bom_report"
REPORT_FILE_BOM = "/file_bom_report"
REPORT_DISCOVERY = "/discovery"
BLACKDUCK_SNIPPET_FILTER = "?filter=bomMatchType%3Asnippet&offset=0&limit=100"
# Retries to wait for BD report creation. RETRY_LIMIT can be overwritten by the script parameter. 
RETRY_LIMIT = 30
RETRY_TIMER = 30
# Reports
report_content = {
    'title' : 'Black Duck Consolidated File Report',
    'configurationSettings':{
        'detectParameters': [],
        'scanDateTime': '',
        'blackDuckVersion': '',
        'linkToBlackDuckProjectVersionInUI': '',
        'linkToBlackDuckSnippetMatchInUI': ''
    },
    'fileInventory': {
        'linkToUnmatchedOsFileData': "",
        'linkToBomComponentEntries': "",
        'linkToBomFileEntries': "",
    }
}
report_os_file = {
    'unmatchedOsFileEntries': {
        'description': 'This list includes folders and files which belong to the target source directory and are not matched by BlackDuck',
        'unmatched': []
    }
}
report_component_bom = {
    'bomComponentEntries': {
        'description': 'This list includes BOM component information which is extracted from BlackDuck project version report.',
        'bomComponents': []
    } 
}
report_file_bom = {
    'bomFileEntries': {
        'description': 'This list includes BOM file information which is extracted from BlackDuck project version report and Discovery report.',
        'bomFiles': [],
        'unmatchedFileDiscoveries': [] 
    }
}

def log_config(debug):
    if debug:
        logging.basicConfig(format='%(asctime)s:%(levelname)s:%(module)s: %(message)s', stream=sys.stderr, level=logging.DEBUG)
    else:
        logging.basicConfig(format='%(asctime)s:%(levelname)s:%(module)s: %(message)s', stream=sys.stderr, level=logging.INFO)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("blackduck").setLevel(logging.WARNING)

def parse_parameter():
    parser = argparse.ArgumentParser(description=program_description, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("project",
                        metavar="project",
                        type=str,
                        help="Provide the BlackDuck project name.")
    parser.add_argument("version",
                        metavar="version",
                        type=str,
                        help="Provide the BlackDuck project version name.")
    parser.add_argument("-f", 
                        "--report_format",
                        metavar="",
                        type=str,
                        default="json",
                        help="Specify the report format. Currently either JSON or HTML is supported. Default is JSON.")
    parser.add_argument("-cl", 
                        "--copyright_level",
                        metavar="",
                        type=int,
                        default=0,
                        help="Specify the included copyright text level. Level 0 (default value) is no copyright texts included, 1 is only copyright texts from KB included, 2 is copyright texts from KB and discoveries included.")
    parser.add_argument("-sd",
                        "--skip_detect",
                        action='store_true',
                        help="Set if execution of Synopsys-Detect is wanted to bypass.")
    parser.add_argument("-dv",
                        "--detect_version",
                        metavar="",
                        type=str,
                        default="latest",
                        help="Specify the Synopsys Detect version to download and run. If not set, the latest version will run.")
    parser.add_argument("-rr",
                        "--report_retries",
                        metavar="",
                        type=int,
                        default=RETRY_LIMIT,
                        help="Retries for receiving the generated BlackDuck report. Timeout timer is hard-coded 30 sec. Generating a copyright report tends to take longer.")
    parser.add_argument("-t",
                        "--timeout",
                        metavar="",
                        type=int,
                        default=15,
                        help="Timeout for REST-API. Some API may take longer than the default 15 seconds")
    parser.add_argument("-r",
                        "--retries",
                        metavar="",
                        type=int,
                        default=3,
                        help="Retries for REST-API. Some API may need more retries than the default 3 times")
    parser.add_argument("-dp",
                        "--detect_parameters",
                        metavar="",
                        type=str,
                        nargs="*",
                        default="",
                        help="List Synopsys Detect parameters with whitespace separators and without '--'. Example: -dp detect.blackduck.signature.scanner.snippet.matching=SNIPPET_MATCHING detect.blackduck.signature.scanner.license.search=true ")
    return parser.parse_args()

def run_detect(project, version, bd_url, bd_token, detect_version, bd_params=None):
    """ Download and run Synopsys Detect. """
    # TODO: Consider to change to async and pall completion of the scan because that maybe more robust against network errors. 
    detect_params = [
        BLACKDUCK_URL + bd_url,
        BLACKDUCK_TOKEN + bd_token,
        BLACKDUCK_PROJECT + project,
        BLACKDUCK_VERSION + version,
        BLACKDUCK_WAIT]
    if bd_params is not None:
        for param in bd_params:
            detect_params.append(f"--{param}")

    # Download the designated detect version of synopsys-detect 
    if detect_version != "latest":
        major_version = detect_version.split(".", 1)[0]
        for i, element in enumerate(DOWNLOAD_DETECT):
            if element == "https://detect.synopsys.com/detect8.sh":
                DOWNLOAD_DETECT[i] = element.replace("detect8", f"detect{major_version}")
                break            
        my_env = os.environ.copy()
        my_env[ENV_DETECT_VERSION] = detect_version
    with open("synopsys-detect.sh", "w") as detect:
        logging.info(f"Synopsys Detect version {detect_version} is being downloaded now!")
        subprocess.run(DOWNLOAD_DETECT, stdout=detect)
    
    detect_command = ["bash", f"{detect.name}"] + detect_params
    logging.info(f"synopsys-detect synchronous scan is in execution now!")
    if detect_version != "latest":
        results = subprocess.run(detect_command, capture_output=True, text=True, env=my_env)
    else:
        results = subprocess.run(detect_command, capture_output=True, text=True)

    print(results.stdout)
    print(results.stderr)
    results.check_returncode()
    return

def get_bd_project_data(hub_client, project_name, version_name):
    """ Get and return project ID, version ID and codelocations. """
    project_id = ""
    for project in hub_client.get_resource("projects"):
        if project['name'] == project_name:
            project_id = (project['_meta']['href']).split("projects/", 1)[1]
            break
    if project_id == "":
        sys.exit(f"No project for {project_name} was found!")
    version_id = codelocations = ""
    for version in hub_client.get_resource("versions", project):
        if version['versionName'] == version_name:
            version_id = (version['_meta']['href']).split("versions/", 1)[1]
            for link in version['_meta']['links']:
                if link['rel'] == "codelocations":
                    codelocations = link['href']
                    break
            break
    if version_id == "":
        sys.exit(f"No project version for {version_name} was found!")
    if codelocations == "":
        sys.exit(f"No codelocations for {project_name} {version_name} found ")

    return project_id, version_id, codelocations

def report_create(hub_client, url, body):
    """ 
    Request BlackDuck to create report. Requested report is included in the request payload.
    """
    res = hub_client.session.post(url, headers={'Content-Type': BLACKDUCK_REPORT_MEDIATYPE}, json=body)
    if res.status_code != 201:
        sys.exit(f"BlackDuck report creation failed with status {res.status_code}!") 
    # return report_url
    return res.headers['Location']

def report_download(hub_client, report_url, project_id, version_id, retry_count):
    """
    Download the generated report after the report completion. We will retry until reaching the retry-limit.
    """
    retries = retry_count
    while retries:
        res = hub_client.session.get(report_url, headers={'Accept': BLACKDUCK_REPORT_MEDIATYPE})
        if res.status_code == 200 and (json.loads(res.content))['status'] == "COMPLETED":
            report_id = report_url.split("reports/", 1)[1]
            download_url = (((blackduck_report_download_api.replace("{projectId}", project_id))
                     .replace("{projectVersionId}", version_id))
                     .replace("{reportId}", report_id))  
            res = hub_client.session.get(download_url, 
                                         headers={'Content-Type': 'application/zip', 'Accept':'application/zip'})
            if res.status_code != 200:
                sys.exit(f"BlackDuck report download failed with status {res.status_code} for {download_url}!")
            return res.content
        elif res.status_code != 200:
            sys.exit(f"BlackDuck report creation not completed successfully with status {res.status_code}")
        else:
            logging.info(f"Waiting for the report generation for {report_url} with the remaining retries {retries} times.")
            retries -= 1            
            time.sleep(RETRY_TIMER)
    sys.exit(f"BlackDuck report for {report_url} was not generated after retries {RETRY_TIMER} sec * {retry_count} times!")

def get_version_detail_report(hub_client, project_id, version_id, retries):
    """ Create and get BOM component and BOM source file report in json. """
    create_version_url = blackduck_create_version_report_api.replace("{projectVersionId}", version_id)
    body = {
        'reportFormat' : 'JSON',
        'locale' : 'en_US',
        'versionId' : f'{version_id}',
        'categories' : [ 'COMPONENTS', 'FILES' ]
    }
    report_url = report_create(hub_client, create_version_url, body)
    # Zipped report content is received and write the content to a local zip file 
    content = report_download(hub_client, report_url, project_id, version_id, retries)
    output_file = blackduck_version_report_filename.replace("{projectVersionId}", version_id)
    with open(output_file, "wb") as f:
        f.write(content)
        return output_file

def get_discovery_report(hub_client, project_id, version_id, retries, copyright):
    """ Create and get discovery report for licenses and copyrights in json. """
    create_discoveries_url = blackduck_create_discoveries_report_api.replace("{projectVersionId}", version_id)
    body = {
        'reportFormat' : 'JSON',
        'locale' : 'en_US',
        'versionId' : f'{version_id}',
        'categories' : [ 'FILE_LICENSE_DATA', 'DEEP_LICENSE_DATA', 'UNMATCHED_FILE_DISCOVERIES' ]
    }
    if copyright == 1:
        body['categories'].append('COPYRIGHT_TEXT')
    elif copyright ==2:
        body['categories'].extend(['COPYRIGHT_TEXT', 'FILE_COPYRIGHT_TEXT'])
    report_url = report_create(hub_client, create_discoveries_url, body)
    content = report_download(hub_client, report_url, project_id, version_id, retries)
    output_file = blackduck_discoveries_report_filename.replace("{projectVersionId}", version_id)
    with open(output_file, "wb") as f:
        f.write(content)
        return output_file
    
def get_folder_size(path="."):
    """
    Calculate the size of the given folder by summing up belonging files.
    Remarks: Calculated folder size maybe shows different figure from OS command line because 
             OS commands may take the file system's chunk into consideration. 
    """
    total_size = 0
    with os.scandir(path) as it:
        for entry in it:
            if entry.is_file():
                size = entry.stat().st_size
                total_size = total_size + size
            elif entry.is_dir():
                size = get_folder_size(entry.path)
                total_size = total_size + size            
    return total_size
    
def get_os_path_for_unmatched(parent_dir, matched_paths):
    """
    Traverse within the provided directory and yield OS folder or file data if it is not a matched path by BlackDuck.
    """
    os_path_data = {
        'path': "",
        'sizeInBytes': 0
    }
    os_path_stats = {
        'matched_folders': 0,
        'matched_files': 0,
        'unmatched_folders': 0,
        'unmatched_files': 0,
        'total_folders': 0,
        'total_files': 0
    }

    log_onerror = lambda err: logging.error(f"An error reported during OS folder and file traverse. OS file report may be uncompleted.{str(err)}")
    for path, folder_names, file_names in os.walk(parent_dir, onerror=log_onerror):
        os_path_stats['total_folders'] = os_path_stats['total_folders'] + len(folder_names)
        os_path_stats['total_files'] = os_path_stats['total_files'] + len(file_names)

        for folder_name in folder_names:
            file_data = copy.deepcopy(os_path_data)
            try:
                abs_path = os.path.join(path, folder_name)
                # Removal of parent path and add a slash for comparison with BlackDuck reported path
                rel_path = abs_path.replace(f"{parent_dir}/", "") + "/"
                if rel_path in matched_paths:
                    os_path_stats['matched_folders'] = os_path_stats['matched_folders'] + 1
                    continue
                file_data['path'] = rel_path
                file_data['sizeInBytes'] = get_folder_size(abs_path)
                os_path_stats['unmatched_folders'] = os_path_stats['unmatched_folders'] + 1
                # Keep the following log if something is wrong with the size
                # logging.debug(f"filepath {file_data['path']} with size {file_data['sizeInBytes']} bytes")
                yield file_data
            except Exception as err:
                logging.warning(f"An exception raised during OS folder report. {str(err)}")
                continue

        for file_name in file_names:
            file_data = copy.deepcopy(os_path_data)
            try:
                abs_path = os.path.join(path, file_name)
                # Removal of parent path for comparison with BlackDuck reported file path
                rel_path = abs_path.replace(f"{parent_dir}/", "")
                if rel_path in matched_paths:
                    os_path_stats['matched_files'] = os_path_stats['matched_files'] + 1
                    continue
                file_data['path'] = rel_path
                file_data['sizeInBytes'] = os.path.getsize(abs_path)
                os_path_stats['unmatched_files'] = os_path_stats['unmatched_files'] + 1
                #logging.debug(f"filepath {file_data['path']} with size {file_data['sizeInBytes']} bytes")
                yield file_data
            except Exception as err:
                logging.warning(f"An exception raised during OS file report. {str(err)}")
                continue
    
    logging.debug(f"Matched folders: {os_path_stats['matched_folders']}, Matched files: {os_path_stats['matched_files']}, "
                  f"Unmatched folders: {os_path_stats['unmatched_folders']}, Unmatched files: {os_path_stats['unmatched_files']}, "
                  f"Total folders under the parent path: {os_path_stats['total_folders']}, "
                  f"Total files under the parent path: {os_path_stats['total_files']}, "
                  f"Number of matched paths by BlackDuck: {len(matched_paths)}")
    return

def pull_component_bom(component_bom):
    """ 
    Extract BOM component data from BD project version report.
    Remarks: Component BOM data includes components for SNIPPET matching which can outnumber the number of the components
             in BlackDuck project version BOM UI.
    """
    component_info = {
        'componentName': '',
        'componentVersionNames': [],
        'matchTypes': [],
        'licenses': []
    }
    license_info = {
        'licenseType': '',
        'name': '',
        'licenseFamily': '',
        'licenses': [],
        'licenseDisplay': ''
    }
    license_nested = {
        'name': '',
        'licenseFamily': '',
        'licenses': [],
        'licenseDisplay': ''
    }
 
    component_bom_data = copy.deepcopy(component_info)
    component_bom_data['componentName'] = component_bom['producerProject']['name'] \
        if 'producerProject' in component_bom.keys() and 'name' in component_bom['producerProject'].keys() else ""
    if 'producerReleases' in component_bom.keys():
        for release in component_bom['producerReleases']:
            component_bom_data['componentVersionNames'].append(release['version'])
    if 'matchTypes' in component_bom.keys():
        for match in component_bom['matchTypes']:
            component_bom_data['matchTypes'].append(match)
    if 'licenses' in component_bom.keys():
        for license in component_bom['licenses']:
            license_data = copy.deepcopy(license_info)
            license_data['licenseType'] = license['licenseType'] if 'licenseType' in license.keys() else ""
            license_data['name'] = license['name'] if 'name' in license.keys() else ""
            license_data['licenseFamily'] = license['codeSharing'] if 'codeSharing' in license.keys() else ""
            if 'licenses' in license.keys():
                for in_license in license['licenses']:
                    nested_license_data = copy.deepcopy(license_nested)
                    nested_license_data['name'] = in_license['name'] if 'name' in in_license.keys() else ""
                    nested_license_data['licenseFamily'] = in_license['codeSharing'] if 'codeSharing' in in_license.keys() else ""
                    nested_license_data['licenseDisplay'] = in_license['licenseDisplay'] if 'licenseDisplay' in in_license.keys() else ""
                    nested_license_data['licenses'] = in_license['licenses'] if 'licenses' in in_license.keys() else []
                    license_data['licenses'].append(nested_license_data)
            license_data['licenseDisplay']= license['licenseDisplay'] if 'licenseDisplay' in license.keys() else ""
            component_bom_data['licenses'].append(license_data)
    return component_bom_data

def pull_file_bom(file_bom):
    """ 
    Extract BOM file data from BD project version report.
    Remarks: If reported path is ended with '/', then that is folder path. If not, that is file path.
    """
 
    file_info = {
        'path' : '',
        'archiveContext' : '',
        'projectName' : '',
        'projectVersion' : '',
        'channelReleaseExternalNamespace' : '',
        'channelReleaseExternalId' : '',
        'matchType' : '',
        'snippetReviewStatus' : '',
        'licenses' : [],
        'copyrights' : {
            'copyrightTexts' : [],
            'fileCopyrightTexts' : []
        } 
    }

    file_bom_data = copy.deepcopy(file_info)
    file_bom_data['path'] = file_bom['path'] if 'path' in file_bom.keys() else ""
    file_bom_data['archiveContext'] = file_bom['archiveContext'] if 'archiveContext' in file_bom.keys() else ""
    file_bom_data['projectName'] = file_bom['projectName'] if 'projectName' in file_bom.keys() else ""
    file_bom_data['projectVersion'] = file_bom['version'] if 'version' in file_bom.keys() else ""
    file_bom_data['matchType'] = file_bom['matchType'] if 'matchType' in file_bom.keys() else ""
    if 'matchType' in file_bom.keys() and file_bom['matchType'] == "SNIPPET":
        file_bom_data['snippetReviewStatus'] = file_bom['snippetReviewStatus']
    file_bom_data['channelReleaseExternalNamespace'] = file_bom['channelReleaseExternalNamespace'] \
        if 'channelReleaseExternalNamespace' in file_bom.keys() else ""
    file_bom_data['channelReleaseExternalId'] = file_bom['channelReleaseExternalId'] \
        if 'channelReleaseExternalId' in file_bom.keys() else ""
    return file_bom_data

def pull_discovery_licenses(comp_license):
    """
    Extract component licenses from discoveries.
    """
    comp_license_info = {
        'projectName' : '',
        'versionName' : '',
        'licenses' : []
    }
    license_info = {
        'name' : '',
        'sources' : []
    }
    comp_license_data = copy.deepcopy(comp_license_info)
    comp_license_data['projectName'] = comp_license['component']['projectName'] \
        if 'component' in comp_license.keys() and 'projectName' in comp_license['component'].keys() else ""
    comp_license_data['versionName'] = comp_license['component']['versionName'] \
        if 'component' in comp_license.keys() and 'versionName' in comp_license['component'].keys() else ""
    if 'licenses' in comp_license.keys():
        for license in comp_license['licenses']:
            license_data = copy.deepcopy(license_info)
            license_data['name'] = license['name'] if 'name' in license.keys() else ""
            if 'sources' in license.keys():
                for source in license['sources']:
                    license_data['sources'].append(source)
            comp_license_data['licenses'].append(license_data)
    return comp_license_data

def pull_discovery_copyrights(comp_copyright):
    """
    Extract component copyrights from discoveries.
    """
    comp_copyright_info = {
        'originFullName' : '',
        'copyrights' : {
            'copyrightTexts' : [],
            'fileCopyrightTexts' : []
        }
   }
    comp_copyright_data = copy.deepcopy(comp_copyright_info)
    comp_copyright_data['originFullName'] = comp_copyright['originFullName'] if 'originFullName' in comp_copyright.keys() else ""
    if 'copyrightTexts' in comp_copyright.keys():
        for copyright in comp_copyright['copyrightTexts']:
            comp_copyright_data['copyrights']['copyrightTexts'].append(copyright)
    if 'fileCopyrightTexts' in comp_copyright.keys():
        for file_copyright in comp_copyright['fileCopyrightTexts']:
            comp_copyright_data['copyrights']['fileCopyrightTexts'].append(file_copyright)
    return comp_copyright_data

def pull_discovery_unmatched(comp_unmatched):
    """
    Extract unmatched files from discoveries.
    """
    comp_unmatched_info = {
        'fileNames' : [],
        'resourceName' : '',
        'matchType' : '',
        'matchTypeLabel' : ''
    }
    file_name_info = {
        'path' : '',
        'archiveContext' : '',
        'compositePathContext' : '',
        'fileName' : ''      
    }

    comp_unmatched_data = copy.deepcopy(comp_unmatched_info)
    if 'fileNames' in comp_unmatched.keys():
        for file_name in comp_unmatched['fileNames']:
            file_name_data = copy.deepcopy(file_name_info)
            file_name_data['path'] = file_name['path'] if 'path' in file_name.keys() else ""
            file_name_data['archiveContext'] = file_name['archiveContext'] \
                if 'archiveContext' in file_name.keys() else ""
            file_name_data['compositePathContext'] = file_name['compositePathContext'] \
                if 'compositePathContext' in file_name.keys() else ""
            file_name_data['fileName'] = file_name['fileName'] if 'fileName' in file_name.keys() else ""
            comp_unmatched_data['fileNames'].append(file_name_data)
    comp_unmatched_data['resourceName'] = comp_unmatched['resourceName'] if 'resourceName' in comp_unmatched.keys() else ""
    comp_unmatched_data['matchType'] = comp_unmatched['matchType'] if 'matchType' in comp_unmatched.keys() else ""
    comp_unmatched_data['matchTypeLabel'] = comp_unmatched['matchTypeLabel'] if 'matchTypeLabel' in comp_unmatched.keys() else ""
    return comp_unmatched_data

def get_scanned_time(hub_client, codelocations):
    """ Retrieve the scanned time from the codelocations data. """
    res = hub_client.session.get(codelocations)
    if res.status_code == 200 and res.content:
        return json.loads(res.content)['items'][0]['updatedAt']
        # Let's use the 1st element of the list because multiple scans should have taken place at the same time
    else:
        sys.exit(f"Get codelocations failed for codelocations {codelocations} with status {res.status_code}")
    
def get_blackduck_version(hub_client):
    url = hub_client.base_url + BLACKDUCK_VERSION_API
    res = hub_client.session.get(url)
    if res.status_code == 200 and res.content:
        return json.loads(res.content)['version']
    else:
        sys.exit(f"Get BlackDuck version failed with status {res.status_code}")

def generate_file_report(hub_client, project_id, version_id, codelocations, copyright_level, format, retries, detect_params=None):
    """ 
    Create a consolidated file report from BlackDuck project version report and notice report.
    Remarks: 
    """
    if not os.path.exists(REPORT_DIR):
        os.makedirs(REPORT_DIR)
    
    # Report headers
    report_content['configurationSettings']['scanDateTime'] = get_scanned_time(hub_client, codelocations)
    report_content['configurationSettings']['blackDuckVersion'] = get_blackduck_version(hub_client)
    report_content['configurationSettings']['detectParameters'] = detect_params
    blackduck_link_component_ui_api.replace("{projectId}", project_id).replace("{projectVersionId}", version_id)
    report_content['configurationSettings']['linkToBlackDuckProjectVersionInUI'] = \
        hub_client.base_url + blackduck_link_component_ui_api.replace("{projectId}", project_id).replace("{projectVersionId}", version_id)
    report_content['configurationSettings']['linkToBlackDuckSnippetMatchInUI'] = \
        hub_client.base_url + blackduck_link_snippet_ui_api.replace("{projectId}", project_id).replace("{projectVersionId}", version_id) \
        + BLACKDUCK_SNIPPET_FILTER

    # Report body - Component BOM, file BOM with Discoveries data
    version_report_zip = get_version_detail_report(hub_client, project_id, version_id, retries)
    with ZipFile(f"./{version_report_zip}", "r") as vzf:
        vzf.extractall()
    for i, unzipped_version in enumerate(vzf.namelist()):
        if re.search(r"\bversion.+json\b", unzipped_version) is not None:
            break
        if i + 1 >= len(vzf.namelist()):
            sys.exit(f"Version detail file not found in the downloaded report: {version_report_zip}!")
    
    # Report body - Component BOM report
    # Iterated json handling to reduce memory consumption. Remarks: Divided to two file-open sessions for components and files
    # with respective file handles, because if otherwise ijson crashes!
    with open(f"./{unzipped_version}", "r") as uvf:
        for i, comp_bom in enumerate(ijson.items(uvf, 'aggregateBomViewEntries.item')):
            comp_data = pull_component_bom(comp_bom)
            report_component_bom['bomComponentEntries']['bomComponents'].append(comp_data)
        logging.info(f"Number of the reported components {i+1}")
        with open(REPORT_DIR + REPORT_COMPONENT_BOM + f".{format}", "w") as cmf:
            if format == "json":
                cmf.write(json.dumps(report_component_bom))
            else:
                cmf.write(json2html.convert(json = json.dumps(report_component_bom)))
        report_content['fileInventory']['linkToBomComponentEntries'] = \
            "file://" + os.path.abspath(REPORT_DIR + REPORT_COMPONENT_BOM + f".{format}")

    # Discovery data - licenses, copyrights and unmatched files - is fetched and integrated with file BOM report.
    discovery_data = {'discoveries': {'licenses': [], 'copyrights': []}}
    discovery_report_zip = get_discovery_report(hub_client, project_id, version_id, retries, copyright_level)
    with ZipFile(f"./{discovery_report_zip}", "r") as zlf:
        zlf.extractall()
    for i, unzipped_discovery in enumerate(zlf.namelist()):
        if re.search(r"\bversion-license.+json\b", unzipped_discovery) is not None:
            break
        if i + 1 >= len(zlf.namelist()):
            sys.exit(f"License file not found in downloaded report: {discovery_report_zip}!")
    # Do not reuse TextIoWrapper for ijson to handle multiple items. If do, ijson crashes.
    with open(f"./{unzipped_discovery}", "r") as ulf:
        for i, comp_license in enumerate(ijson.items(ulf, 'componentLicenses.item')):
            comp_license_data = pull_discovery_licenses(comp_license)
            discovery_data['discoveries']['licenses'].append(comp_license_data)
        logging.info(f"Number of the reported discovery licenses {i+1}")
    if copyright_level != 0:
        with open(f"./{unzipped_discovery}", "r") as ucf:
            for i, comp_copyright in enumerate(ijson.items(ucf, 'componentCopyrightTexts.item')):
                comp_copyright_data = pull_discovery_copyrights(comp_copyright)
                discovery_data['discoveries']['copyrights'].append(comp_copyright_data)
            logging.info(f"Number of the reported discovery copyright texts {i+1}")
    with open(f"./{unzipped_discovery}", "r") as uuf:
        for i, comp_unmatched in enumerate(ijson.items(uuf, 'unmatchedFileData.item')):
            comp_unmatched_data = pull_discovery_unmatched(comp_unmatched)
            report_file_bom['bomFileEntries']['unmatchedFileDiscoveries'].append(comp_unmatched_data)
        logging.info(f"Number of the reported discovery unmatched files texts {i+1}")
        
    # Report body - Generate file BOM report. Discovery data is integrated.
    with open(f"./{unzipped_version}", "r") as uvf:
        for i, file_bom in enumerate(ijson.items(uvf, 'detailedFileBomViewEntries.item')):
            file_data = pull_file_bom(file_bom)
            disc_licenses = list(filter(lambda license_x:
                                        license_x['projectName'] == file_data['projectName'] and
                                        license_x['versionName'] == file_data['projectVersion'], 
                                        discovery_data['discoveries']['licenses']))
            if len(disc_licenses) != 0:
                disc_license = disc_licenses[0]
                for license in disc_license['licenses']:
                    file_data['licenses'].append(license)
            else:
                logging.debug(f"No discovery license found for file with this component: {file_data['projectName']} and {file_data['projectVersion']}")
            if len(disc_licenses) > 1:
                logging.warning(f"More than one discovery license: {disc_licenses} found for {file_data['projectName']}" and file_data['projectVersion'])
            
            if copyright_level != 0:
                origin_name = file_data['channelReleaseExternalNamespace'] + ":" + file_data['channelReleaseExternalId']
                disc_copyrights = list(filter(lambda copyright_x:
                                              copyright_x['originFullName'] == origin_name,
                                              discovery_data['discoveries']['copyrights']))
                if len(disc_copyrights) != 0:
                    disc_copyright = disc_copyrights[0]
                    for copyright in disc_copyright['copyrights']['copyrightTexts']:
                        file_data['copyrights']['copyrightTexts'].append(copyright)
                    for file_copyright in disc_copyright['copyrights']['fileCopyrightTexts']:
                        file_data['copyrights']['fileCopyrightTexts'].append(file_copyright)
                else:
                    logging.debug(f"No discovery copyright found for file with this origin: {origin_name}")
                if len(disc_copyrights) > 1:
                    logging.warning(f"More than one discovery copyright: {disc_copyrights} found for the same origin {origin_name}")
    
            report_file_bom['bomFileEntries']['bomFiles'].append(file_data)
        logging.info(f"Number of the reported files {i+1}")        

        with open(REPORT_DIR + REPORT_FILE_BOM + f".{format}", "w") as flf:
            if format == "json":
                flf.write(json.dumps(report_file_bom))
            else:
                flf.write(json2html.convert(json = json.dumps(report_file_bom)))
        report_content['fileInventory']['linkToBomFileEntries'] = \
            "file://" + os.path.abspath(REPORT_DIR + REPORT_FILE_BOM + f".{format}")
    
    # Report body - Paths and sizes for folders and files which are not matched by BlackDuck         
    parent_path = "."
    for param in detect_params:
        if re.search(rf"{BLACKDUCK_SOURCE_PATH}", param) is not None:
            parent_path = param.split("=", 1)[1]
            break
    logging.info("OS file information for the target source is being traversed and reported.")
    matched_paths = []
    for file_bom in report_file_bom['bomFileEntries']['bomFiles']:
        # BlackDuck can match internal folders or files within archive files, e.g., .jar or .zip or .tar.gz.
        # OS unmatched file function does not search inside of the archived contents as it sounds too much.
        if (file_bom['archiveContext']) != "":
            continue
        else:            
            matched_paths.append(file_bom['path'])
    # Let's remove duplicated path entries. BD may report multiple BOM file entries for the same path.
    unique_paths = list(set(matched_paths))
    if len(unique_paths) != len(matched_paths):
        logging.warning("BlackDuck component BOM contains duplicated file paths!")        
    for os_path_data in get_os_path_for_unmatched(parent_path, unique_paths):
        report_os_file['unmatchedOsFileEntries']['unmatched'].append(os_path_data)
    with open(REPORT_DIR + REPORT_OS_FILE + f".{format}", "w") as osf:
            if format == "json":  
                osf.write(json.dumps(report_os_file))
            else:
                osf.write(json2html.convert(json = json.dumps(report_os_file)))
    report_content['fileInventory']['linkToUnmatchedOsFileData'] = \
        "file://" + os.path.abspath(REPORT_DIR + REPORT_OS_FILE + f".{format}")

    with open(REPORT_DIR + REPORT_HEADER + f".{format}", "w") as rf:
            if format == "json":
                rf.write(json.dumps(report_content))
            else:
                rf.write(json2html.convert(json = json.dumps(report_content)))

def main():
    args = parse_parameter()

    try:
        if args.copyright_level >= 3:
            sys.exit("please provide the copyright level which is either 0 or 1 or 2!")
        if (args.report_format).lower() != "json" and (args.report_format).lower() != "html":
            sys.exit("Please set either 'json' or 'html' to the report format")

        with open(".restconfig.json", "r") as f:
            config = json.load(f)
            # Remove last slash if there is, otherwise REST API may fail.
            if re.search(r".+/$", config['baseurl']):
                bd_url = config['baseurl'][:-1]
            else:
                bd_url = config['baseurl']
            bd_token = config['api_token']
            bd_insecure = not config['insecure']
            debug = 1 if config['debug'] else 0
        
        log_config(debug)    

        if not args.skip_detect:
            run_detect(args.project, args.version, bd_url, bd_token, args.detect_version, args.detect_parameters)

        hub_client = Client(token=bd_token,
                            base_url=bd_url,
                            verify=bd_insecure,
                            timeout=args.timeout,
                            retries=args.retries)
        
        project_id, version_id, codelocations = get_bd_project_data(hub_client, args.project, args.version)

        generate_file_report(hub_client,
                             project_id,
                             version_id,
                             codelocations,
                             args.copyright_level,
                             args.report_format.lower(),
                             args.report_retries,
                             args.detect_parameters
                             )

    except (Exception, BaseException) as err:
        logging.error(f"Exception by {str(err)}. See the stack trace")
        traceback.print_exc()

if __name__ == '__main__':
    sys.exit(main())
