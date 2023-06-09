#!/usr/bin/env python

'''
Purpose: Update project versions with licenses of their subprojects (components)

usage: update_project_with_component_licenses.py [-h] -u BASE_URL -t TOKEN_FILE [-nv] 

options:
  -h, --help            show this help message and exit
  -u BASE_URL, --base-url BASE_URL
                        Hub server URL e.g. https://your.blackduck.url
  -t TOKEN_FILE, --token-file TOKEN_FILE
                        containing access token
  -nv, --no-verify      disable TLS certificate verification
  -p PROJECT_NAME, --project-name PROJECT_NAME
                        Project Name
  -pv VERSION_NAME, --version-name VERSION_NAME
                        Project Version Name
 '''

import argparse
import json
import logging
import sys
import requests

from pprint import pprint
from blackduck import Client

licenselist = []

def checkforsubprojects(s):
    #Simple Check to see if subproject also has child subprojects
    subcomponents = getcomponents(s,"Sub")
    if len(subcomponents)>0:
        check = True
    else:
        check= False
    return check

def getcomponents(spj, test):
    #Returns Versions of a given project
    if test == "Version":
        components = [ sp for sp in bd.get_resource('components',spj) if sp['componentType'] == "SUB_PROJECT" ]
    #Returns Subprojects for a given Project Version
    elif test == "Sub":
        version = bd.session.get(returnsubprojecturl(spj)).json()
        components = [ sp for sp in bd.get_resource('components',version) if sp['componentType'] == "SUB_PROJECT" ]
    #Returns license data for a given Project Version
    elif test == "License":
        version = bd.session.get(returnsubprojecturl(spj)).json()
        components = bd.get_resource('components',version)
    return components

def getlicensesfromprojectversion(subproject):
    license_components = getcomponents(subproject,"License")
    #check for subprojects
    if checkforsubprojects(subproject) == True:
        #First Process Licenses of the components
        for license_component in license_components:  
            for license in license_component['licenses']:
                if license.get("licenseType",None) :
                    for innerlicense in license['licenses']:
                        licenselist.append(innerlicense)   
                else:
                    licenselist.append(license)
        #Now Loop Through the nested projects
        loops = getcomponents(subproject,"Sub")
        for loop in loops:
            getlicensesfromprojectversion(loop)
    #When No SubProjects
    else:
        for license_component in license_components:
            for license in license_component['licenses']:
                if license.get("licenseType",None):
                    for innerlicense in license['licenses']:
                        licenselist.append(innerlicense)
                else:
                    licenselist.append(license)
    return licenselist

def getprojects(project_name):
    #Returns all Projects for a given Project Name
    params = {
        'q': [f"name:{project_name}"]
    }
    projects = [p for p in bd.get_resource('projects', params=params) if p['name'] == project_name]
    return projects

def getversions(project, version_name):
    #Returns all Versions from a Project with given Version Name
    params = {
        'q': [f"versionName:{version_name}"]
    }
    versions = [v for v in bd.get_resource('versions', project, params=params) if v['versionName'] == version_name]
    return versions

def main():
    args = parse_command_args()
    with open(args.token_file, 'r') as tf:
        access_token = tf.readline().strip()
    global bd
    bd = Client(base_url=args.base_url, token=access_token, verify=args.no_verify, timeout=60.0, retries=4)
    process_project_version(args)

def parse_command_args():
    parser = argparse.ArgumentParser("update_project_with_component_licenses.py [-h] -u BASE_URL -t TOKEN_FILE [-nv] ")
    parser.add_argument("-u", "--base-url", required=True, help="Hub server URL e.g. https://your.blackduck.url")
    parser.add_argument("-t", "--token-file", dest='token_file', required=True, help="containing access token")
    parser.add_argument("-nv", "--no-verify", dest='no_verify', action='store_false', help="disable TLS certificate verification")
    parser.add_argument("-p", "--project_name", required=True, help="Provide Project Name here")
    parser.add_argument("-v", "--version_name"). help="Provide Project Version here"
    return parser.parse_args()

def process_project_version(args):
    #Validating only 1 Project
    projects = getprojects(args.project_name)
    assert len(projects) == 1, f"There should be one, and only one project named {args.project_name}. We found {len(projects)}"
    project = projects[0]
    
    #Validates only 1 Version
    versions = getversions(project, args.version_name)
    assert len(versions) == 1, f"There should be one, and only one version named {args.version_name}. We found {len(versions)}"
    version = versions[0]
    
    pprint("Currently processing SubProjectes of Project " + project['name'] + " version " + version['versionName'])
    #Return only sub-projects, not components
    components = getcomponents(version, "Version")  

    for subproject in components:
        #Setting URL for API call
        url = subproject['_meta']['href']
        #Retrieve Licenses
        subprojectlicenses = getlicensesfromprojectversion(subproject)
        #Defaulting licenseblock to correct format
        licenseblock = [
        {
            "licenseType": "CONJUNCTIVE",
            "licenses": subproject['licenses'][0]['licenses']}]
        #Adding each license to array
        for license in subprojectlicenses:
            licenseblock[0]['licenses'].append(license)
        #Adding licenses to JSON body
        subproject['licenses']=licenseblock
        try: 
            r = bd.session.put(url,json=subproject)
            print("Updated SubProject " + subproject['componentName'] + " with child licenses")
        except KeyError as err:
            pprint (err)
            

def returnsubprojecturl(x):
    xurl=x['_meta']['href']
    x = xurl.split("/")
    del x[5]
    del x[5]
    del x[5]
    del x[5]
    xurl = "/".join(x)
    return xurl

if __name__ == "__main__":
    sys.exit(main())