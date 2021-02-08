
#!/usr/bin/env python

import argparse
import json
import logging
import sys

from blackduck.HubRestApi import HubInstance

parser = argparse.ArgumentParser("Modify a custom field option")
parser.add_argument("object", choices=["BOM Component", "Component", "Component Version", "Project", "Project Version"], help="The object that the custom field should be attached to")
parser.add_argument("field_id", help="The ID of the custom field to modify")
parser.add_argument("option_id", help="The ID of the custom field option to modify")
args = parser.parse_args()


logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stderr, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.DEBUG)
logging.getLogger("urllib3").setLevel(logging.WARNING)

hub = HubInstance()

# delete all custom fields for the specified object type
custom_fields = hub.get_custom_fields(args.object).get('items', [])
for custom_field in custom_fields:
    field_url = custom_field['_meta']['href']
    field_id = field_url.split("/")[-1]
    if field_id == args.field_id:
        field_obj = hub.execute_get(field_url).json()

        options_url = hub.get_link(field_obj, "custom-field-option-list")
        options = hub.execute_get(options_url).json().get('items', [])
        for option in options:
            option_url = option['_meta']['href']
            option_id = option_url.split("/")[-1]
            if option_id == args.option_id:
                response = hub.execute_delete(option_url)
                if response.status_code == 204:
                    print("Deleted option {}".format(option_url))
                else:
                    print("Failed to delete option {}, status code: {}".format(option_url, response.status_code))
