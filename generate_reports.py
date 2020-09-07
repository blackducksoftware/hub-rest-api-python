#!/usr/bin/python3 

import argparse
import json
import time
import logging

from blackduck.HubRestApi import HubInstance

const_project_roles = [ "Project Code Scanner", "BOM Manager", "Project Viewer", "Project Manager", "Security Manager", "Policy Violation Reviewer"]

# ------------------------------------------------------------------------------
# Parse command line

parser = argparse.ArgumentParser(
    formatter_class=argparse.RawDescriptionHelpFormatter,
    description='Generates and downloads reports for project(s) on blackduck.com',
    epilog='''\
Note: When using the --project_file option the file format per line MUST be:

# Lines starting # are ignored, so are empty lines
project name[;version][;destination]
'''
)

group = parser.add_mutually_exclusive_group(required=True)
group.add_argument('--project_name', '-p', type=str, help='Add a single project')
group.add_argument('--project_file', '-f', type=argparse.FileType(), help='Add all projects listed in the file')

parser.add_argument('--prefix', '-x', default='', type=str, help='String to add to the start of all project names')
parser.add_argument('--version', '-v', default='master', type=str, help='Version to use if not specified in the file. Default: master')
parser.add_argument('--sleep_time', '-s', default=5, type=int, help="Time in seconds to sleep between download attempts")
parser.add_argument('--log', '-l', action="store_true", help="Debug log output")

args = parser.parse_args()
# create logger
log = logging.getLogger('debug')
if args.log:
    log.setLevel(logging.DEBUG)
else:
    log.setLevel(logging.CRITICAL)

# create console handler and set level to debug
ch = logging.StreamHandler()
if args.log:
    ch.setLevel(logging.DEBUG)
else:
    ch.setLevel(logging.CRITICAL)
    
# create formatter
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
# add formatter to ch
ch.setFormatter(formatter)
# add ch to logger
log.addHandler(ch)


hub = HubInstance()

class ProjectVersion:
    reports = [
        'VERSION',
        'CODE_LOCATIONS',
        'COMPONENTS',
        'SECURITY',
        'FILES',
        'ATTACHMENTS',
        # 'CRYPTO_ALGORITHMS',
        'PROJECT_VERSION_CUSTOM_FIELDS',
        'BOM_COMPONENT_CUSTOM_FIELDS',
        'LICENSE_TERM_FULFILLMENT',
    ]
   
    def __init__(self, project_name, version_name, filename=None):
        log.debug(f"Initialising ProjectVersion: {project_name} - {version_name}")
        self.project_name = project_name 
        self.version_name = version_name
        self.filename = filename
        
        self.error = None
        self.report_complete = False
        self.links = {}
        
        project_object = hub.get_project_by_name(self.project_name)
        if project_object:
            self.version_object = hub.get_version_by_name(project_object, self.version_name)
            if self.version_object:
                links = self.version_object['_meta']['links']
                for link in links:
                    self.links[link['rel']] = link['href']
            else:
                self.error = f"Project '{self.project_name}' has no version: {self.version_name}"
        else:
            self.error = f"Unknown project: {self.project_name}"
            
        if self.error:
            log.debug(self.error)
    
    def name(self):
        return f"{self.project_name} - {self.version_name}"
            
    def generate_report(self):
        if not self.version_object:
            self.error = "No version object"
            raise Exception(self.error)
        
        log.debug(f"Generating report for: {self.name()}")
        response = hub.create_version_reports(self.version_object, self.reports, 'CSV')
        
        if response.status_code == 201:
            log.debug(f"Reports requested for: {self.name()}")
            self.links['downloadMeta'] = response.headers['Location']
        else:
            self.error(f"Failed to request for: {self.name()}")

    
    def fetch_report(self):
        if self.report_complete:
            return
            
        log.debug(f"Fetching report for: {self.name()}")
        if not self.links.get('downloadMeta'):
            self.error = "No download link"
            raise Exception(self.error)
            
        if not self.filename:
            self.filename = f"{pv.name()}.zip"
        
        response = hub.execute_get(self.links['downloadMeta'])
        data = response.json() 
        
        if response.status_code == 200 and data['status'] == 'COMPLETED':
            self.links['download-href'] = data['_meta']['links'][1]['href']
            response = hub.execute_get(self.links['download-href'])
            if response.status_code == 200:
                with open(self.filename, "wb") as f:
                    f.write(response.content)
                    
                log.debug(f"Completed download to: {self.filename}")
            else:
                self.error = f"Unable to download report ({response.status_code})"
            
            self.report_complete = True
               
        else:
            log.debug(f"Waiting... : {self.name()}")
            
    def clean_up(self):
        if self.error:
            log.warning(f"'{self.name()}' generated error: {self.error}")
            
        if self.links.get('download-href'):
            log.debug(f"Cleaning up online report for: {self.name()}")
            hub.execute_delete(self.links.get('download-href'))
            
        self.version_object = None
            

print('Generating report(s)...')

if args.project_name:
    try:
        pv = ProjectVersion(f"{args.prefix}{args.project_name}", args.version)
        pv.generate_report()
        log.info(pv.links.get('downloadMeta'))
        while not pv.report_complete:
            time.sleep(args.sleep_time)
            pv.fetch_report()

    finally:
        pv.clean_up()
        
    print(f"{pv.name()} download complete")
else:
    all_pv = []
    f = args.project_file
    log.debug(f"Parsing input file: {f.name}")
    for line in f.readlines():
        line = line.strip()
        if not line or line[0] == "#":
            continue
            
        log.debug(f">> {line}")
            
        index=0
        params = line.split(";")
        project_name = f"{args.prefix}{params[0]}"
        
        version_name = None
        if len(params) > 1:
            version_name = params[1]
        
        if not version_name:
            version_name = args.version
            
        if len(params) > 2:
            destination = params[2]
        else:
            destination = None

        log.debug(f">>> {project_name} - {version_name} => {destination}")
        pv = ProjectVersion(project_name, version_name, destination)
        pv.generate_report()
        all_pv.append(pv)

    while True:
        all_complete = True
        for pv in all_pv:
            pv.fetch_report()
            all_complete = all_complete and pv.report_complete
            
        time.sleep(args.sleep_time)
        
        if all_complete:
            break
        
    for pv in all_pv:
        pv.clean_up()
