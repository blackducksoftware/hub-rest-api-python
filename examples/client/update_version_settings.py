#!/usr/bin/env python

'''
Copyright (C) 2021 Synopsys, Inc.
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
import argparse
import json
import logging
import sys

from blackduck import Client
from blackduck.constants import PROJECT_VERSION_SETTINGS, VERSION_DISTRIBUTION, VERSION_PHASES

class InvalidVersionSetting(Exception):
    pass


def validate_settings(settings):
    # convert to a dict
    settings_d = {s[0]:s[1] for s in settings}
    invalid_settings = [s for s in settings_d.keys() if s not in PROJECT_VERSION_SETTINGS]
    if invalid_settings:
        raise InvalidVersionSetting(f"The settings - {invalid_settings} - are not in the list of valid settings = {PROJECT_VERSION_SETTINGS}")
    
    if 'phase' in settings_d and settings_d['phase'] not in VERSION_PHASES:
        raise InvalidVersionSetting(f"The phase {settings_d['phase']} is not in the list of valid phases = {VERSION_PHASES}")
    if 'distribution' in settings_d and settings_d['distribution'] not in VERSION_DISTRIBUTION:
        raise InvalidVersionSetting(f"The distribution {settings_d['distribution']} is not in the list of valid distribution types = {VERSION_DISTRIBUTION}")
    return settings_d

parser = argparse.ArgumentParser("Update one or more of the settings on a given project-version in Black Duck")
parser.add_argument("base_url", help="Hub server URL e.g. https://your.blackduck.url")
parser.add_argument("token_file", help="containing access token")
parser.add_argument("project_name")
parser.add_argument("version_name")
parser.add_argument("-s", "--settings", required=True, action="append", nargs=2,metavar=('setting', 'value'), 
    help=f"Settings you can change are {PROJECT_VERSION_SETTINGS}. Possible phases are {VERSION_PHASES}. Possible distribution values are {VERSION_DISTRIBUTION}")
parser.add_argument("--no-verify", dest='verify', action='store_false', help="disable TLS certificate verification")
args = parser.parse_args()

settings_d = validate_settings(args.settings)

logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stdout, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("blackduck").setLevel(logging.WARNING)

with open(args.token_file, 'r') as tf:
    access_token = tf.readline().strip()

bd = Client(
    base_url=args.base_url,
    token=access_token,
    verify=args.verify
)

params = {
    'q': [f"name:{args.project_name}"]
}
projects = [p for p in bd.get_resource('projects', params=params) if p['name'] == args.project_name]
assert len(projects) == 1, f"There should be one, and only one project named {args.project_name}. We found {len(projects)}"
project = projects[0]

params = {
    'q': [f"versionName:{args.version_name}"]
}
versions = [v for v in bd.get_resource('versions', project, params=params) if v['versionName'] == args.version_name]
assert len(versions) == 1, f"There should be one, and only one version named {args.version_name}. We found {len(versions)}"
version = versions[0]

logging.debug(f"Found {project['name']}:{version['versionName']}")

for setting, new_value in settings_d.items():
    version[setting] = new_value

logging.debug(f"Updating {project['name']}:{version['versionName']} settings to {settings_d}")
try:
    r = bd.session.put(version['_meta']['href'], json=version)
    r.raise_for_status()
    logging.debug(f"updated version settings to the new values ({settings_d})")
except requests.HTTPError as err:
    bd.http_error_handler(err)



