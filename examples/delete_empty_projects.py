'''
Created on March 4, 2019

@author: kumykov

Delete all project that have no components in any versions

This program will scan Blackduck server and delete all projects that have 
no components in any versions.


Usage:

delete_empty_projects.py [-h] [--before YYYY-MM-DD]

optional arguments:
  -h, --help           show this help message and exit
  --before YYYY-MM-DD  Scan projects before specified date only

'''

from blackduck.HubRestApi import HubInstance
import sys
from argparse import ArgumentParser
from datetime import datetime
from datetime import timedelta
import logging

def delete_empty_projects(before=None):
    
    hub = HubInstance()
    logging.basicConfig(level=logging.DEBUG)
    
    projects = hub.get_projects(limit=500)
    print (projects)
    if before:
        aDate = datetime.strptime(before, '%Y-%m-%d')
    else:
        aDate = datetime.now() + timedelta(days=1)
    
    for project in projects['items']:
        name = project['name']
        # uuid = project['_meta']['href'].split('/')[5]
        updatedAt = project['updatedAt']
        uDate = datetime.strptime(updatedAt, '%Y-%m-%dT%H:%M:%S.%fZ')
        componentCount = 0
        if uDate < aDate:
            print ("Processing {} ".format(name))
            versions = hub.get_project_versions(project)
            for version in versions['items']:
                components = hub.get_version_components(version, limit=1)
                componentCount += components['totalCount']
            if componentCount == 0:
                print ("Project {} has {} components".format(name, componentCount))
                print ("attempting to delete")
                hub.delete_project_by_name(name, save_scans=True)


def main(argv=None):
    
    if argv is None:
        argv = sys.argv
    else:
        argv.extend(sys.argv)
        
    parser = ArgumentParser()
    parser.add_argument('--before', default=None, help="Remove empty projects older than specified date YYYY-MM-DD  ")
    args = parser.parse_args()
    
    delete_empty_projects(before=args.before)
    
if __name__ == "__main__":
    sys.exit(main())