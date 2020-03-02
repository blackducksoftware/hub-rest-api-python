
#!/usr/bin/env python

import argparse
import json
import logging
import sys

from blackduck.HubRestApi import HubInstance

parser = argparse.ArgumentParser("Modify a custom field")
parser.add_argument("object", choices=["BOM Component", "Component", "Component Version", "Project", "Project Version"], help="The object that the custom field should be attached to")
parser.add_argument("field_id", help="The ID of the custom field to modify")
parser.add_argument("-l", "--label", help="The new label to apply")
parser.add_argument("-d", "--description", help="The new description to apply")
args = parser.parse_args()


logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stderr, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.DEBUG)
logging.getLogger("urllib3").setLevel(logging.WARNING)


hub = HubInstance()

# delete all custom fields for the specified object type
custom_fields = hub.get_custom_fields(args.object).get('items', [])
for custom_field in custom_fields:
    url = custom_field['_meta']['href']
    field_id = url.split("/")[-1]
    if field_id == args.field_id:
        field_obj = hub.execute_get(url).json()
        if args.label:
            field_obj['label'] = args.label
        if args.description:
            field_obj['description'] = args.description
        response = hub.execute_put(url, data=field_obj)
        if response.status_code == 200:
            print("Successfully updated field {}".format(url))
        else:
            print("Failed to update field {}, status code: {}".format(response.status_code))
