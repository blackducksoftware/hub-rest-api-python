'''
Created on January 23, 2023
@author: christopher-mackle
Delete the oldest project version (last created or last updated) when you've hit your max version limit
'''

from datetime import datetime
from blackduck.Client import Client
import argparse

parser = argparse.ArgumentParser("Get a specific component and list its vulnerabilities")
parser.add_argument("--url", dest='url', required=True, help="Hub server URL e.g. https://your.blackduck.url")
parser.add_argument("--token", dest='token', required=True, help="Hub server access token")
parser.add_argument("--project", dest='project_name', required=True, help="Name of project")
parser.add_argument("--mode", dest='mode', required=False, default='createdAt', help="Use createdAt or updatedAt")
parser.add_argument("--count", dest='count_total', required=False, default=9, help="Max versions - 1")
args = parser.parse_args()

TOKEN = args.token
BASE_URL = args.url
PROJECT_NAME = args.project_name

try:
    bd = Client(
        token=TOKEN,
        base_url=BASE_URL,
        verify=False  # TLS certificate verification
    )
except:
    print("Could not authenticate to your Black Duck server with the given URL and token.")

def deleteVersion(mode):
    count = 0
    time_format = '%Y-%m-%dT%H:%M:%S.%fZ'
    for version in bd.get_resource('versions', project):
        count = count + 1
        if count == 1:
            oldest_version = version
        else:
            oldestVersionDate = datetime.strptime(oldest_version[mode], time_format)
            currentVersionDate = datetime.strptime(version[mode], time_format)
            if currentVersionDate < oldestVersionDate:
                oldest_version = version
    if count > int(args.count_total):
        print('Too many project versions. Deleting oldest project version before scanning.')
        projectVersionToDelete = oldest_version['_meta']['href']
        r = bd.session.delete(projectVersionToDelete)
        r.raise_for_status()
        print("Project version " + oldest_version['versionName'] + ' has been deleted.')

if __name__ == '__main__':
    found = False
    for project in bd.get_resource('projects'):
        if project['name'] == PROJECT_NAME:
            found = True
            if args.mode == 'createdAt':
                deleteVersion(args.mode)
            elif args.mode == 'updatedAt':
                deleteVersion('settingUpdatedAt')
            else:
                print("Invalid mode: " + args.mode)
                print("Valid modes: createdAt, updatedAt")
    if not found:
        print("Project " + PROJECT_NAME + " not found.")
