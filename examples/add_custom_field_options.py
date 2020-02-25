
#!/usr/bin/env python

import argparse
import json
import logging
import sys

from blackduck.HubRestApi import HubInstance

parser = argparse.ArgumentParser("Modify a custom field")
parser.add_argument("object", choices=["BOM Component", "Component", "Component Version", "Project", "Project Version"], help="The object that the custom field should be attached to")
parser.add_argument("field_id", help="The ID of the custom field to modify")
parser.add_argument("-o", "--options", action='append', nargs=2, metavar=('label', 'position'), help="The options to add. To add more than one option repeat the -o option, supply a label and position for each possible selection. Used for DROPDOWN, MULTISELECT, and RADIO field types.")
args = parser.parse_args()


logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stderr, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.DEBUG)
logging.getLogger("urllib3").setLevel(logging.WARNING)

options = [{"label": io[0], "position": io[1]} for io in args.options]

hub = HubInstance()

# delete all custom fields for the specified object type
custom_fields = hub.get_custom_fields(args.object).get('items', [])
for custom_field in custom_fields:
    url = custom_field['_meta']['href']
    field_id = url.split("/")[-1]
    if field_id == args.field_id:
        field_obj = hub.execute_get(url).json()

        options_url = hub.get_link(field_obj, "custom-field-option-list")
        for option in options:
            response = hub.execute_post(options_url, data=option)
            if response.status_code == 201:
                print("Successfully added option {} to custom field {}".format(option, url))
            else:
                print("Failed to add option {} for custom field {}, status code: {}".format(
                    option, url, response.status_code))

