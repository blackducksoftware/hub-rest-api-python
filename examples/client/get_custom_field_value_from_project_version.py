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

parser = argparse.ArgumentParser("Get custom field value from a project version")
parser.add_argument("bd_url")
parser.add_argument("user_api_token")
parser.add_argument("project")
parser.add_argument("version")
parser.add_argument("field_label")
parser.add_argument("-v", "--verify", default=False, help="Set this to verify the SSL certificate. In production you should always use this. In dev/test the default (False) is ok.")
args = parser.parse_args()


logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stderr, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("blackduck").setLevel(logging.WARNING)

def get_project_version_by_name(project_name, version_name):
    params = {
        'q': [f"name:{project_name}"]
    }
    projects = [p for p in bd.get_resource('projects', params=params) if p['name'] == project_name]
    assert len(projects) == 1, f"There should be one, and only one project named {project_name}. We found {len(projects)}"
    project = projects[0]

    params = {
        'q': [f"versionName:{version_name}"]
    }
    versions = [v for v in bd.get_resource('versions', project, params=params) if v['versionName'] == version_name]
    assert len(versions) == 1, f"There should be one, and only one version named {version_name}. We found {len(versions)}"
    version = versions[0]
    return project, version


bd = Client(
    base_url=args.bd_url,
    token=args.user_api_token,
    verify=args.verify
)

project, version = get_project_version_by_name(args.project, args.version)
custom_fields = [cf for cf in bd.get_resource("custom-fields", version)]

cfs = list(filter(lambda cf: cf['label'] == args.field_label, custom_fields))
assert len(cfs) == 1, f"We did not find the field labeled {args.field_label} or we found more than one and that shouldn't happen!"
custom_field = cfs[0]
print(f"Custom field {args.field_label} on project-version {args.project}-{args.version} has value(s) {custom_field['values']}")
print(f"Refer to the BD REST API doc for more details on how to interact with the different custom field types, {bd.base_url}/api-doc/public.html#_reading_a_single_project_version_custom_field")

