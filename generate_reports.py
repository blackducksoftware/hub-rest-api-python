#!/usr/bin/python3 

import sys
import argparse
import json
import datetime
import time
import logging

import os.path
from os import path

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
project name[;version][;filename]

# The default version is master but can be overridden with --version
# The default filenema is the project-version name with .zip e.g. "my proj-master.zip"
'''
)

group = parser.add_mutually_exclusive_group(required=True)
group.add_argument('--project_name', '-p', type=str, help='Add a single project')
group.add_argument('--project_file', '-f', type=argparse.FileType(), help='Add all projects listed in the file')
parser.add_argument('--version', '-v', default='master', type=str, help='Version to use if not specified in the file. Default: master')

group_reports = parser.add_argument_group('reports', description='Select 1 or more to generate')
group_reports.add_argument('--summary', '-s', default=None, choices=["short", "full"], help='Create a summary report json (default) or csv file of the project(s). short option only lists the CRITICAL and HIGH issues.')
group_reports.add_argument('--detailed', '-d', action="store_true", help='Generate and fetch the detailed reports.')
group_reports.add_argument('--licence', '-l', action="store_true", help='Generate and fetch the licence report (aka Notices file).')

parser.add_argument('--output', '-o', default='.', type=str, help='Output folder to download the reports into. Default: .')
parser.add_argument('--format', '-m', default='JSON', choices=["CSV", "JSON"], help="Report format. 1 JSON file or multiple CSV files")
parser.add_argument('--skip_cleanup', '-c', action="store_true", help='Do not remove reports generated on BlackDuck')
parser.add_argument('--prefix', '-x', default='', type=str, help='String to add to the start of all project names')
parser.add_argument('--sleep_time', '-t', default=30, type=int, help="Time in seconds to sleep between download attempts")
parser.add_argument('--log', action="store_true", help="Debug log output")

args = parser.parse_args()
# create logger
log = logging.getLogger('log')
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


if not (args.summary or args.detailed or args.licence):
    print(f"ERROR: Must specify at least 1 report to generate")
    sys.exit()

if not path.isdir(args.output):
    print(f"ERROR: Invalid output folder: {args.output}")
    sys.exit()


hub = HubInstance()

class ProjectVersion:
    reports = [
        'VERSION',
        'CODE_LOCATIONS',
        'COMPONENTS',
        'SECURITY',
        'FILES',
        #'ATTACHMENTS',
        # 'CRYPTO_ALGORITHMS',
        'PROJECT_VERSION_CUSTOM_FIELDS',
        'BOM_COMPONENT_CUSTOM_FIELDS',
        'LICENSE_TERM_FULFILLMENT',
    ]
    
    SUMMARY_SHORT = [
        'Project Name', 
        'Version',
        'Internal Version',
        'Policy Violation',
        'VULNERABILITY Risk CRITICAL',
        'VULNERABILITY Risk HIGH',
        'LICENSE Risk CRITICAL',
        'LICENSE Risk HIGH',
        'Last Scan',
    ]
    
    SUMMARY_LONG = [
        'Project Name', 
        'Version',
        'Internal Version',
        'Policy Violation',
        'VULNERABILITY Risk CRITICAL',
        'VULNERABILITY Risk HIGH',
        'VULNERABILITY Risk MEDIUM',
        'VULNERABILITY Risk LOW',
        'VULNERABILITY Risk OK',
        'VULNERABILITY Risk UNKNOWN',
        'LICENSE Risk CRITICAL',
        'LICENSE Risk HIGH',
        'LICENSE Risk MEDIUM',
        'LICENSE Risk LOW',
        'LICENSE Risk OK',
        'LICENSE Risk UNKNOWN',
        'Last Scan',
    ]
   
    def __init__(self, project_name, version_name, filename=None):
        log.debug(f"Initialising ProjectVersion: {project_name} - {version_name}")
        self.project_name = project_name 
        self.version_name = version_name
        self.filename = filename
        
        self.error = None
        self.detailed_complete = False
        self.licence_complete = False
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
            
        self.generate_summary()
            
        if self.error:
            log.debug(self.error)
    
    def name(self):
        return f"{self.project_name}-{self.version_name}"
            
    def generate_summary(self):
        if not args.summary:
            return False
            
        print(f"Generating summary for: {self.name()}")
        
        self.summary = { 'Project Name': self.project_name, 'Version': self.version_name }
        
        #log.debug(self.links.keys())
        for key, link in self.links.items():
            func_name = f"_parse_{key.replace('-','_')}"
            func = getattr(self, func_name, None)
            if func:
                response = hub.execute_get(link)
                if response and response.status_code == 200:
                    data = response.json()
                    func(data)
                else:
                    log.warning(f"Failed to get {key} for {self.name()}")
       
        
    def _parse_policy_status(self, data):
        log.debug("_parse_policy_status")
        self.summary['Policy Violation'] = data['overallStatus']
         
    def _parse_custom_fields(self, data):
        log.debug("_parse_custom_fields")

        self.summary['Internal Version'] = None
        for item in data['items']:
            if item['label'] == 'Internal_Version' and len(item['values']) > 0:
                self.summary['Internal Version'] = item['values'][0]
        
    def _parse_riskProfile(self, data):
        log.debug("_parse_riskProfile")

        for category in ('LICENSE', 'VULNERABILITY'):
            for risk, value in data['categories'][category].items():
                self.summary[f"{category} Risk {risk}"] = value       
        
    def _parse_codelocations(self, data):
        log.debug("_parse_codelocations")
        
        self.summary['Last Scan'] = 'No scan'
        for item in data['items']:      
            udpatedAt = datetime.datetime.strptime(item['updatedAt'], '%Y-%m-%dT%H:%M:%S.%fZ')
            if self.summary['Last Scan'] == 'No scan' or udpatedAt > self.summary['Last Scan']:
                self.summary['Last Scan'] = udpatedAt

        if self.summary['Last Scan'] != 'No scan':
            self.summary['Last Scan'] = self.summary['Last Scan'].date().isoformat()

    def get_summary_header(self):
        if not args.summary or args.format == 'JSON':
            return ""

        fields = (self.SUMMARY_SHORT if args.summary == 'short' else self.SUMMARY_LONG)
        return ",".join(fields)

    def get_summary(self):
        if not args.summary:
            return ""

        if args.format == "CSV":
            csv = None
            for field in (self.SUMMARY_SHORT if args.summary == 'short' else self.SUMMARY_LONG):
                if csv:
                    csv = f"{csv},{str(self.summary.get(field, 'n/a'))}"
                else:
                    csv = str(self.summary.get(field,'n/a'))
                    
            return csv
        else:
            json = None
            for field in (self.SUMMARY_SHORT if args.summary == 'short' else self.SUMMARY_LONG):
                if json:
                    json = f"{json},\"{field}\":\"{str(self.summary.get(field, 'n/a'))}\""
                else:
                    json = f"\"{field}\":\"{str(self.summary.get(field, 'n/a'))}\""
                    
            return f"{{{json}}}"


    def generate_detailed_report(self):
        if not args.detailed:
            self.detailed_complete = True
            return False
            
        if not self.version_object:
            return
        
        print(f"Generating detailed report for: {self.name()}")
        response = hub.create_version_reports(self.version_object, self.reports, args.format)
        
        if response.status_code == 201:
            log.debug(f"Reports requested for: {self.name()}")
            self.links['downloadMeta'] = response.headers['Location']
        else:
            self.error = f"Failed to request: {self.name()} ({response.status_code})"
            return False

   
    def fetch_detailed_report(self):
        if self.detailed_complete:
            return
            
        if not self.links.get('downloadMeta'):
            log.debug(f"No download link for: {self.name()}")
            self.detailed_complete = True
            return
 
        log.debug(f"Fetching report for: {self.name()}") 
        if not self.filename:
            self.filename = f"{pv.name()}.zip"
        
        response = hub.execute_get(self.links['downloadMeta'])
        data = response.json() 
        
        if response.status_code == 200 and data['status'] == 'COMPLETED':
            self.links['download-href'] = data['_meta']['links'][1]['href']
            response = hub.execute_get(self.links['download-href'])
            if response.status_code == 200:
                dest = path.join(args.output, self.filename)
                with open(dest, "wb") as f:
                    f.write(response.content)
                    
                print(f"Completed download to: {dest}")
            else:
                self.error = f"Unable to download report ({response.status_code})"
            
            self.detailed_complete = True
        else:
            log.debug(f"Report not ready for: {self.name()}")

            
    def generate_licence_report(self):
        if not args.licence:
            self.licence_complete = True
            return False
            
        if not self.version_object:
            return
        
        print(f"Generating licence report for: {self.name()}")
        fmt = args.format
        if fmt == 'CSV':
            fmt = 'TEXT'
            
        response = hub.create_version_notices_report(self.version_object, fmt)
        
        if response.status_code == 201:
            log.debug(f"Reports requested for: {self.name()}")
            self.links['downloadMeta2'] = response.headers['Location']
        else:
            self.error = f"Failed to request for: {self.name()}  ({response.status_code})"
            return False
            
            
    def fetch_licence_report(self):
        if self.licence_complete:
            return
            
        if not self.links.get('downloadMeta2'):
            log.debug(f"No download link for: {self.name()}")
            self.licence_complete = True
            return
 
        log.debug(f"Fetching licence report for: {self.name()}") 
        if not self.filename:
            self.filename = f"{pv.name()}.zip"
        
        filename = f"licence.{self.filename}"
        response = hub.execute_get(self.links['downloadMeta2'])
        data = response.json() 
        
        if response.status_code == 200 and data['status'] == 'COMPLETED':
            self.links['download-href2'] = data['_meta']['links'][1]['href']
            response = hub.execute_get(self.links['download-href2'])
            if response.status_code == 200:
                dest = path.join(args.output, filename)
                with open(dest, "wb") as f:
                    f.write(response.content)
                    
                print(f"Completed download to: {dest}")
            else:
                self.error = f"Unable to download report ({response.status_code})"
            
            self.licence_complete = True
               
        else:
            log.debug(f"Report not ready for: {self.name()}")
            
    def clean_up(self):
        if self.error:
            log.critical(f"'{self.name()}' generated error: {self.error}")
            
        if args.skip_cleanup:
            log.debug(f"Skipping clean up of online report for: {self.name()}")
        else:
            if self.links.get('download-href'):
                log.debug(f"Cleaning up online detailed report for: {self.name()}")
                hub.execute_delete(self.links.get('download-href'))
                
            if self.links.get('download-href2'):
                log.debug(f"Cleaning up online licence report for: {self.name()}")
                hub.execute_delete(self.links.get('download-href2'))
            
        self.version_object = None
            


# ------------------------------------------------------------------------------  
# Main code

if args.project_name:
    print('Generating report...')
    pv = None
    try:
        pv = ProjectVersion(f"{args.prefix}{args.project_name}", args.version)

        if pv.generate_detailed_report() != False:
            log.info(pv.links.get('downloadMeta'))
            while not pv.detailed_complete:
                time.sleep(args.sleep_time)
                pv.fetch_detailed_report()
                
            print(f"{pv.name()} download complete")
            
        if pv.generate_licence_report() != False:
            log.info(pv.links.get('downloadMeta2'))
            while not pv.licence_complete:
                time.sleep(args.sleep_time)
                pv.fetch_licence_report()
                
            print(f"{pv.name()} download complete")
            
        if args.summary:
            print("Writing summary")
            if args.format == 'CSV':
                dest = path.join(args.output, 'summary.csv')
            else:
                dest = path.join(args.output, 'summary.json')
            
            with open(dest, "w") as f:
                f.write(pv.get_summary_header() + "\n")
                f.write(pv.get_summary() + "\n")

    finally:
        if pv:
            pv.clean_up()

else:
    print('Generating reports...')
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
        pv = None
        try:
            pv = ProjectVersion(project_name, version_name, destination)
            pv.generate_detailed_report()
            pv.generate_licence_report()
            all_pv.append(pv)
        except:
            log.critical(f"Unable to generate report for: {project_name} - {version_name}")
            if pv:
                pv.clean_up()
                
    if args.detailed:
        while True:
            all_complete = True
            count = 0
            for pv in all_pv:
                pv.fetch_detailed_report()
                if pv.detailed_complete:
                    count += 1
                else:
                    all_complete = False
           
            if all_complete:
                break
            else:
                print(f"{count}/{len(all_pv)} detailed reports downloaded")
                time.sleep(args.sleep_time)
        
        print(f"All detailed report downloads complete")

    if args.licence:
        while True:
            all_complete = True
            count = 0
            for pv in all_pv:
                pv.fetch_licence_report()
                if pv.licence_complete:
                    count += 1
                else:
                    all_complete = False
           
            if all_complete:
                break
            else:
                print(f"{count}/{len(all_pv)} licence reports downloaded")
                time.sleep(args.sleep_time)
        
        print(f"All licence report downloads complete")
    
    if args.summary:
        print("Writing summary")
        if args.format == 'CSV':
            dest = path.join(args.output, 'summary.csv')
        else:
            dest = path.join(args.output, 'summary.json')
            
        with open(dest, "w") as f:
            first = True
            if args.format == 'JSON':
                f.write("{\"Projects\":[")
                
            for pv in all_pv:
                if args.format == 'CSV':
                    if first:
                        first = False
                        f.write(pv.get_summary_header() + "\n")
                    
                    f.write(pv.get_summary() + "\n")
                else:
                    if first:
                        first = False
                        f.write(pv.get_summary())
                    else:
                        f.write("," + pv.get_summary())
            
            if args.format == 'JSON':
                f.write("]}\n")
                

    for pv in all_pv:
        pv.clean_up()
