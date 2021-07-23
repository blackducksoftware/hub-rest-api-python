
#!/usr/bin/env python

import argparse
import json
import logging
from pprint import pprint
import sys

from blackduck.HubRestApi import HubInstance

parser = argparse.ArgumentParser("Get custom field options")
parser.add_argument("object", choices=["BOM Component", "Component", "Component Version", "Project", "Project Version"], help="The object that the custom field should be attached to")
parser.add_argument("field_id", help="The ID of the custom field to modify")
args = parser.parse_args()


logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stderr, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.DEBUG)
logging.getLogger("urllib3").setLevel(logging.WARNING)

hub = HubInstance()

# get all custom fields for the specified object type
custom_fields = hub.get_custom_fields(args.object).get('items', [])
for custom_field in custom_fields:
    field_url = custom_field['_meta']['href']
    field_id = field_url.split("/")[-1]
    import pdb; pdb.set_trace()
    if field_id == args.field_id:
        field_obj = hub.execute_get(field_url).json()

        options_url = hub.get_link(field_obj, "custom-field-option-list")
        options = hub.execute_get(options_url).json().get('items', [])
        options_info = [{'option_url': o['_meta']['href'], 'label': o['label'], 'position': o['position']} for o in options]
        pprint(options_info)