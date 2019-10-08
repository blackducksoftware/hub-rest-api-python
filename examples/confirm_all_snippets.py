#!/usr/local/bin/python3
# encoding: utf-8
'''
Created on October 3, 2019

@author: ylei

Confirm all snippet matched automatically.
Use case is, in CI flow like Jenkis, user would like to check if any
file violates pre-defined policy after Black Duck scan process, without 
logging into server and go through each of snippet match on by one.

Example usage:
    python confirm_all_snippets.py <Project> <Version>
'''
import argparse

from blackduck.HubRestApi import HubInstance

parser = argparse.ArgumentParser("Confirm all snippet matches for the given project and version")
parser.add_argument("project_name")
parser.add_argument("version")

args = parser.parse_args()

hub = HubInstance()

project = hub.get_project_by_name(args.project_name)
version = hub.get_version_by_name(project, args.version)

project_id = project['_meta']['href'].split("/")[-1]
version_id = version['_meta']['href'].split("/")[-1]

def confirm_snippet(snippet, component):
    put_data = {
            "component": component,
            "ignored": False,
            "reviewStatus": "reviewed"
        }
    response = hub.execute_put(snippet, data=put_data)


def main():
    url = hub.get_urlbase() + "/api/projects/{project}/versions/{version}/matched-files?limit={limit}".format(
                                    project=project_id, version=version_id, limit=1000)
    response = hub.execute_get(url)
    jobs = []
    count = 0
    if response.status_code == 200:
        matched_files = response.json().get('items', [])
        for matched_file in matched_files:
            for match in matched_file['matches']:
                if match['matchType'] == 'SNIPPET':
                    confirm_snippet(match['snippet'], match['component'])
                    count += 1
                    print("Snippet " + str(count) + ": " + str(matched_file['uri']))
    else:
        logging.error("Failed to retrieve matched files, status code: {}".format(response.status_code))

if __name__ == "__main__":
    main()