#!/usr/bin/env python3
'''

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
'''

program_description = \
'''
This script will scan a multi-container project into 
hierarchical structure.

Project Name
      Project Version
           Sub-project Name
                Sub-project Version
                    Base Image
                        Base Image Version
                    Add on Image
                        Add on Image Version

Sub-projects are specified as sub-project:[container]:[tag]
if container name omitted it will be set to sub-project
if tag omitted it would be set to 'latest'

Sub-projects an be specified in excel file with -ssf --subproject-spec-file parameter.
Excel file should contain one worksheet with first row containing column names as following:
Container Name, Image ID, Version, Project Name
and subsequent rows containing data

Sub-projects could be specified in a text file with -ssf --subproject-spec-file parameter
Each line will have to contain full image specification.
Specification will be parsed and image name prefixed by -str parameter will be used as a sub-project name
In this mode any image that is not residing on ciena.com repository will be skipped.
If -str parameter is empty, Project Name will be used instead.

Container image name scanned will be written into project version nickname field

'''

import argparse
import json
import logging
import sys
import arrow

from io import StringIO

from blackduck import Client
from pprint import pprint,pformat

class MultiImageProjectManager():

    def __init__(self, args):
        self.debug = args.debug
        self.binary = args.binary
        self.individual_file_matching = args.individual_file_matching
        self.log_config()
        self.base_url = args.base_url
        with open(args.token_file, 'r') as tf:
            self.access_token = tf.readline().strip()
        self.no_verify = args.no_verify
        self.reprocess_run_file = args.reprocess_run_file
        self.connect()
        if self.reprocess_run_file:
            self.load_project_data()
        else:
            self.init_project_data(args)

    def connect(self):
        self.client = Client(base_url=self.base_url, token=self.access_token, verify=self.no_verify, timeout=60.0, retries=4)

    def load_project_data(self):
        with open(self.reprocess_run_file, "r") as f:
            data = json.load(f)
        self.project_data = data
        self.project_data.pop('log', None)
        discard = list()
        for name, subproject in self.project_data['subprojects'].items():
            if not self.has_errors(subproject):
                discard.append(name)
            else:
                self.project_data['subprojects'][name].pop('log', None)
                self.project_data['subprojects'][name].pop('status', None)
                self.project_data['subprojects'][name].pop('scan_results',None)
        for name in discard:
            del self.project_data['subprojects'][name]

    def has_errors(self, subproject):
        structure = False
        runtime = False
        if subproject['status'] != 'PRESENT':
            structure = True
        if not subproject.get('scan_results', None):
            runtime = True
        else:
            rcodes = [r['scan_results']['returncode'] for r in subproject['scan_results'] if r.get('scan_results', None)]
            if sum(rcodes) > 0:
                runtime = True
        if structure or runtime:
            return True
        else:
            return False

    def init_project_data(self,args):
        self.project_data = dict()
        self.project_data['project_name'] = args.project_name
        self.project_data['version_name'] = args.version_name
        self.project_data['project_group'] = args.project_group
        self.project_data['clone_from'] = args.clone_from
        self.project_data['dry_run'] = args.dry_run
        self.project_data['strict'] = args.strict
        self.project_data['remove'] = args.remove

        subprojects = dict()
        child_spec_list = self.get_child_spec_list(args)
        # pprint (child_spec_list)
        for child_spec in [x.split(':') for x in child_spec_list]:
            subproject = dict()
            i = iter(child_spec)
            i = iter(child_spec)
            child = next(i)
            repo = next(i, child)
            tag = next(i,'latest')
            container_spec = f"{repo}:{tag}"
            while child in subprojects:
                child += "_"
            subproject['image'] = container_spec
            subproject['project_name'] = child
            subproject['version_name'] = args.version_name
            subproject['project_group'] = args.project_group
            subproject['clone_from'] = args.clone_from
            subprojects[child] = subproject

        self.project_data['subprojects'] = subprojects

    def log_config(self):
        if self.debug:
            logging.basicConfig(format='%(asctime)s:%(levelname)s:%(module)s: %(message)s', stream=sys.stderr, level=logging.DEBUG)
        else:
            logging.basicConfig(format='%(asctime)s:%(levelname)s:%(module)s: %(message)s', stream=sys.stderr, level=logging.INFO)
        logging.getLogger("requests").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("blackduck").setLevel(logging.WARNING)

    def log(self, level, msg, target=None):
        if target:
            target_log = target.get('log', None)
            if not target_log:
                target_log = list()
                target['log'] = target_log
            target_log.append(msg)
        log_function = getattr(logging, level)
        log_function(msg)

    def remove_project_structure(self, project_name, version_name):
        project = self.find_project_by_name(project_name)

        if not project:
            logging.debug(f"Project {project_name} does not exist.")
            return
        num_versions = self.client.get_resource('versions', project, items=False)['totalCount']
        version = self.find_project_version_by_name(project,version_name)
        if not version:
            logging.debug(f"Project {project_name} with version {version_name} does not exist.")
            return
        components = [
            c for c in self.client.get_resource('components',version) if c['componentType'] == "SUB_PROJECT"
        ]
        logging.debug(f"Project {project_name}:{version_name} has {len(components)} subprojects")
        for component in components:
            component_name = component['componentName']
            component_version_name = component['componentVersionName']
            logging.debug(f"Removing subproject {component_name} from {project_name}:{version_name}")
            component_url = component['_meta']['href']
            response = self.client.session.delete(component_url) 
            logging.debug(f"Operation completed with {response}")
            self.remove_project_structure(component_name, component_version_name)
        logging.debug(f"Removing {project_name}:{version_name}")
        if num_versions > 1:
            response = self.client.session.delete(version['_meta']['href'])
        else:
            response = self.client.session.delete(project['_meta']['href'])
        logging.debug(f"Operation completed with {response}")

    def remove_codelocations_recursively(self, version):
        components = self.client.get_resource('components', version)
        subprojects = [x for x in components if x['componentType'] == 'SUB_PROJECT']
        logging.debug(f"Found {len(subprojects)} subprojects")
        self.unmap_all_codelocations(version)
        for subproject in subprojects:
            subproject_name = subproject['componentName']
            subproject_version_name = subproject['componentVersionName']
            project = self.find_project_by_name(subproject_name)
            if not project:
                logging.debug(f"Project {subproject_name} does not exist.")
                return
            subproject_version = self.find_project_version_by_name(project, subproject_version_name)   
            if not subproject_version:
                logging.debug(f"Project {subproject_name} with version {subproject_version_name} does not exist.")
                return
            self.remove_codelocations_recursively(subproject_version)

    def unmap_all_codelocations(self, version):
        codelocations = self.client.get_resource('codelocations',version)
        for codelocation in codelocations:
            logging.debug(f"Un-mapping of code location {codelocation['name']}")
            codelocation['mappedProjectVersion'] = ""
            response = self.client.session.put(codelocation['_meta']['href'], json=codelocation)
            logging.debug(f"Un-mapping of code location {codelocation['name']} completed with {response}")


    def find_or_create_project_group(self, group_name):
        url = '/api/project-groups'
        params = {
            'q': [f"name:{group_name}"]
        }
        groups = [p for p in self.client.get_items(url, params=params) if p['name'] == group_name]
        if len(groups) == 0:
            headers = {
                'Accept': 'application/vnd.blackducksoftware.project-detail-5+json',
                'Content-Type': 'application/vnd.blackducksoftware.project-detail-5+json'
            }
            data = {
                'name': group_name
            }
            response = self.client.session.post(url, headers=headers, json=data)
            return response.headers['Location'] 
        else:
            return groups[0]['_meta']['href']

    def find_project_by_name(self, project_name):
        params = {
            'q': [f"name:{project_name}"]
        }
        projects = [p for p in self.client.get_resource('projects', params=params) if p['name'] == project_name]
        if len(projects) == 1:
            return projects[0]
        else:
            return None

    def find_project_version_by_name(self, project, version_name):
        params = {
            'q': [f"versionName:{version_name}"]
        }
        versions = [v for v in self.client.get_resource('versions', project, params=params) if v['versionName'] == version_name]
        if len(versions) == 1:
            return versions[0]
        else:
            return None

    def create_project_version(self,project_name,version_name,nickname = None):
        version_data = {"distribution": "EXTERNAL", "phase": "DEVELOPMENT", "versionName": version_name}
        if nickname:
            version_data['nickname'] = nickname
        url = '/api/projects'
        project = self.find_project_by_name(project_name)
        if project:
            data = version_data
            url = project['_meta']['href'] + '/versions'
        else:
            data = {"name": project_name,
                    "projectGroup": self.find_or_create_project_group(self.project_data['project_group']),
                    "versionRequest": version_data}
        return self.client.session.post(url, json=data)

    def add_component_to_version_bom(child_version, version):
        url = version['_meta']['href'] + '/components'
        data = { 'component': child_version['_meta']['href']}
        return self.client.session.post(url, json=data)

    def process_excel_spec_file(self,wb):
        ws = wb.active
        project_list = []
        row_number = 0
        for row in ws.values:
            row_number += 1
            if (row_number == 1 and
                row[0] == 'Container Name' and
                row[1] == 'Image ID' and
                row[2] == 'Version' and
                row[3] == 'Project Name'):
                logging.info(f"File Format checks out (kind of)")
                continue
            elif row_number > 1:
                project_list.append(f"{row[3]}:{row[0]}:{row[2]}")
            else:
                logging.error(f"Could not parse input file ")
                sys.exit(1)
        return (project_list)

    def process_text_spec_file(self,args):
        project_list = []
        prefix = args.string_to_put_in_front_of_subproject_name
        if not prefix:
            prefix = args.project_name
        with open(args.subproject_spec_file, "r") as f:
            lines = f.read().splitlines()
        for line in lines:
            image_name = line.split('/')[-1].split(':')[0]   # Don't look at me, you wrote it!
            sub_project_name = "_".join((prefix, image_name))
            spec_line = ":".join((sub_project_name, line))
            if "ciena.com" in spec_line:
                project_list.append(spec_line)    
        return (project_list)

    def get_child_spec_list(self,args):
        if args.subproject_list:
            return args.subproject_list.split(',')
        else:
            # Excel and plaintext
            logging.debug(f"Processing excel file {args.subproject_spec_file}")
            import openpyxl
            try:
                wb = openpyxl.load_workbook(args.subproject_spec_file)
                return self.process_excel_spec_file(wb)
            except Exception:
                return self.process_text_spec_file(args)

    def create_and_add_child_projects(self,version):
        version_url = version['_meta']['href'] + '/components'
        version_name = self.project_data['version_name']
        for child_name, child in self.project_data['subprojects'].items():
            child_name = child['project_name']
            container_spec = child['image']
            project = self.find_project_by_name(child_name)
            if project:
                version = self.find_project_version_by_name(project,version_name)
                if version:
                    if self.project_data['strict']:
                        self.log('error', f"Child project {project['name']} with version {version_name} exists.", child)
                        sys.exit(1)
                    else:
                        self.log('debug',f"Child project {project['name']} with version {version_name} found.", child)
                        self.log('debug',f"Recursively removing codelocations for {project['name']} with version {version_name} ", child)
                        try:
                            self.log('debug',f"Adding project {child_name} {version_name} to the parent project", child)
                            child_version_url = version['_meta']['href']
                            response = self.client.session.post(version_url,json={'component': child_version_url})
                            self.log('debug',f"Adding {child_name} : {version_name} to parent project completed with {response}", child)
                        except Exception as e:
                            self.log('debug',f"Adding {child_name} : {version_name} to parent project completed with exception {e}", child)
                        self.remove_codelocations_recursively(version)
                else:
                    response = self.create_project_version(child_name,version_name, nickname=container_spec)
                    self.log('debug',f"Creating project {child_name} : {version_name} completed with {response}", child)
                    if response.ok:
                        child_version = self.find_project_version_by_name(self.find_project_by_name(child_name),version_name)
                        child_version_url = child_version['_meta']['href']
                        response = self.client.session.post(version_url,json={'component': child_version_url})
                        self.log('debug',f"Adding {child_name} : {version_name} to parent project completed with {response}", child)
            else:
                response = self.create_project_version(child_name,version_name, nickname=container_spec)
                self.log('debug',f"Creating project {child_name} : {version_name} completed with {response}",child)
                if response.ok:
                    child_version = self.find_project_version_by_name(self.find_project_by_name(child_name),version_name)
                    child_version_url = child_version['_meta']['href']
                    response = self.client.session.post(version_url,json={'component': child_version_url})
                    self.log('debug',f"Adding {child_name} : {version_name} to parent project completed with {response}", child)

    def create_project_structure(self):
        project_name = self.project_data['project_name']
        version_name = self.project_data['version_name']

        project = self.find_project_by_name(project_name)
        if project:
            self.log('debug', f"Project {project_name} located", self.project_data)
            version = self.find_project_version_by_name(project,version_name)
            if version:
                if self.project_data['strict']:
                    self.log('error', f"Project {project['name']} with version {version_name} exists.", self.project_data)
                    sys.exit(1) 
                else:
                    self.log('debug',f"Found Project {project['name']} with version {version_name}.", self.project_data)
            else:
                response = self.create_project_version(project_name,version_name)
                if response.ok:
                    version = self.find_project_version_by_name(self.find_project_by_name(project_name),version_name)
                    self.log('debug', f"Project {project_name} : {version_name} created", self.project_data)
                else:
                    self.log('debug',f"Failed to create Project {project_name} : {version_name} created", self.project_data)
                    sys.exit(1)
        else:
            self.log('debug',f"Project {project_name} was not found, creating ...", self.project_data)
            response = self.create_project_version(project_name,version_name)
            if response.ok:
                version = self.find_project_version_by_name(self.find_project_by_name(project_name),version_name)
                self.log('debug',f"Project {project_name} : {version_name} created", self.project_data)
            else:
                self.log('debug',f"Failed to create Project {project_name} : {version_name} created", self.project_data)
                sys.exit(1)
        self.log('debug',f"Checking/Adding subprojects to {project_name} : {version['versionName']}", self.project_data)
        self.create_and_add_child_projects(version)

    def validate_project_structure(self):
        parent_project = self.find_project_by_name(self.project_data['project_name'])
        parent_version = self.find_project_version_by_name(parent_project, self.project_data['version_name'])
        components = [c for c in self.client.get_resource('components', parent_version) if c['componentType'] == 'SUB_PROJECT']
        for spn, sp in self.project_data['subprojects'].items():
            spn = sp['project_name']
            spvn = sp['version_name']
            ca = [c for c in components if spn == c['componentName'] and spvn == c['componentVersionName']]
            if len(ca) == 1:
                sp['status'] = 'PRESENT'
                self.log('debug',f"Sub-project project {spn} : {spvn} is present in the BOM ", sp)
            else:
                sp['status'] = 'ABSENT'
                self.log('debug',f"Sub-project project {spn} : {spvn} could not be added to the BOM ", sp)

    def scan_container_images(self):
        from scan_docker_image_lite import scan_container_image
        from blackduck.HubRestApi import HubInstance
        hub = HubInstance(self.base_url, api_token=self.access_token, insecure= not self.no_verify, debug=self.debug)

        for child_name, child in self.project_data['subprojects'].items():
            parent_project = child['project_name']
            parent_version = child['version_name']
            image_name = child['image']
            clone_from = child['clone_from']
            project_group = child['project_group']
            detect_options =    (f"--detect.parent.project.name={parent_project} "
                                f"--detect.parent.project.version.name={parent_version} " 
                                f"--detect.project.version.nickname={image_name}")
            if self.individual_file_matching:
                detect_options += f" --detect.blackduck.signature.scanner.individual.file.matching=ALL"
            if clone_from:
                detect_options += f" --detect.clone.project.version.name={clone_from}"
            if project_group:
                detect_options += f" --detect.project.group.name=\"{project_group}\""
            try:
                results = scan_container_image(
                    image_name, 
                    None, 
                    None, 
                    None, 
                    parent_project, 
                    parent_version,
                    detect_options,
                    hub=hub,
                    binary=self.binary
                )
                child['scan_results'] = results
            except Exception as e:
                # import traceback
                # traceback.print_exc()
                self.log('error', repr(e), child)
                logging.error(f"Scanning of {image_name} failed, skipping")

    def proceed(self):
        if self.project_data['remove']:
            project_name = self.project_data['project_name']
            version_name = self.project_data['version_name']
            self.remove_project_structure(project_name, version_name)
        else:
            self.create_project_structure()
            self.validate_project_structure()
            self.scan_container_images()
        
def write_failure_report(data, output_file_name):
    s = StringIO()
    subprojects = data['subprojects']
    for subproject_name, subproject in subprojects.items():
        structure = False
        runtime = False
        if subproject['status'] != 'PRESENT':
            structure = True
        if not subproject.get('scan_results', None):
            runtime = True
        else:
            rcodes = [r['scan_results']['returncode'] for r in subproject['scan_results'] if r.get('scan_results', None)]
            if sum(rcodes) > 0:
                runtime = True
        if structure or runtime:
            print (f"\nStatus for {subproject['project_name']} {subproject['version_name']}", file = s)
            print (f"\tStructural failures present {structure}", file = s)
            print (f"\t   Runtime failures present {runtime}\n", file = s)
            
            if subproject['status'] != 'PRESENT':
                for line in subproject['log']:
                    print ('\t', line, file = s)
            scan_results = subproject.get('scan_results',[])
            if len(scan_results) == 0:
                print ("No scans were performed", file = s)
            else:
                for invocation in scan_results:
                    returncode = invocation['scan_results']['returncode']
                    if returncode > 0:
                        print (f"\n\tScan for {invocation['name']} failed with returncode {returncode}\n", file = s)
                        stdout = invocation['scan_results']['stdout'].split('\n')
                        for line in stdout:
                            if 'ERROR' in line and 'certificates' not in line:
                                print ('\t', line, file = s)
    with open(output_file_name, "w") as f:
        f.write(s.getvalue())

def parse_command_args():

    parser = argparse.ArgumentParser(description=program_description, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("-u", "--base-url",     required=True, help="Hub server URL e.g. https://your.blackduck.url")
    parser.add_argument("-t", "--token-file",   required=True, help="File containing access token")
    parser.add_argument("-pg", "--project_group", required=False, default='Multi-Image', help="Project Group to be used")
    parser.add_argument("-p", "--project-name",   required=False, help="Project Name")
    parser.add_argument("-pv", "--version-name",   required=False, help="Project Version Name")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-sp", "--subproject-list",   required=False, help="List of subprojects to generate with subproject:container:tag")
    group.add_argument("-ssf", "--subproject-spec-file",   required=False, help="Excel or txt file containing subproject specification")
    parser.add_argument("-nv", "--no-verify",   action='store_false', help="Disable TLS certificate verification")
    parser.add_argument("-rm", "--remove",   action='store_true', required=False, help="Remove project structure with all subprojects (DANGEROUS!)")
    parser.add_argument("--clone-from", required=False, help="Main project version to use as template for cloning")
    parser.add_argument("--dry-run", action='store_true', required=False, help="Create structure only, do not execute scans")
    parser.add_argument("-str", "--string-to-put-in-front-of-subproject-name", required=False, help="Prefix string for subproject names" )
    parser.add_argument("-d", "--debug", action='store_true', help="Set debug output on")
    parser.add_argument("--strict", action='store_true', help="Fail if existing (sub)project versions already exist")
    parser.add_argument("--binary", action='store_true', help="Use binary scan for analysis")
    parser.add_argument("-ifm", "--individual-file-matching", action='store_true', help="Turn Individual file matching on")
    parser.add_argument("--reprocess-run-file", help="Reprocess Failures from previous run report.")
    args =  parser.parse_args()
    if not args.reprocess_run_file and not (args.project_name and args.version_name):
        parser.error("[ -p/--project-name and -pv/--version-name ] or --reprocess-run-file are required")
    if args.reprocess_run_file and (args.project_name or args.version_name):
        parser.error("[ -p/--project-name and -pv/--version-name ] or --reprocess-run-file are required")
    return args

def main():
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    args = parse_command_args()
    mipm = MultiImageProjectManager(args)
    logging.info(f"Parsed {len(mipm.project_data['subprojects'])} projects from specification data")
    mipm.proceed()

    if not args.remove:
        filename_base = f"{mipm.project_data['project_name']}-{mipm.project_data['version_name']}"
        filename_complete = f"{filename_base}-{timestamp}-full.json"
        filename_failure_report = f"{filename_base}-{timestamp}-failures.txt"
        # write full processing log
        with open (filename_complete, "w") as f:
            json.dump(mipm.project_data, f, indent=2)

        write_failure_report(mipm.project_data, filename_failure_report)

if __name__ == "__main__":
    sys.exit(main())
