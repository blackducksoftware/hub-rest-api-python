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

from blackduck.HubRestApi import HubInstance, object_id

parser = argparse.ArgumentParser("Get custom field value from a project version")
parser.add_argument("project")
parser.add_argument("version")
parser.add_argument("field_label")
args = parser.parse_args()


logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stderr, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("blackduck").setLevel(logging.WARNING)

hub = HubInstance()

project_version = hub.get_project_version_by_name(args.project, args.version)
custom_fields_url = hub.get_link(project_version, "custom-fields")
custom_fields = hub.execute_get(custom_fields_url).json().get('items', [])

cfs = list(filter(lambda cf: cf['label'] == args.field_label, custom_fields))
assert len(cfs) == 1, f"We did not find the field labeled {args.field_label} or we found more than one and that shouldn't happen!"
custom_field = cfs[0]
print(f"Custom field {args.field_label} on project-version {args.project}-{args.version} has value(s) {custom_field['values']}")
print(f"Refer to the BD REST API doc for more details on how to interact with the different custom field types, {hub.get_urlbase()}/api-doc/public.html#_reading_a_single_project_version_custom_field")