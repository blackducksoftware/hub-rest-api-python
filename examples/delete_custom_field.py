
#!/usr/bin/env python

import argparse
import json
import logging
import sys

from blackduck.HubRestApi import HubInstance

parser = argparse.ArgumentParser("Work with custom fields")
parser.add_argument("object", choices=["BOM Component", "Component", "Component Version", "Project", "Project Version"], help="The object that the custom field should be attached to")
parser.add_argument("field_id")
args = parser.parse_args()


logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stderr, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.DEBUG)
logging.getLogger("urllib3").setLevel(logging.WARNING)


hub = HubInstance()

if args.field_id == "all":
    # delete all custom fields for the specified object type
    custom_fields = hub.get_custom_fields(args.object).get('items', [])
    for custom_field in custom_fields:
        logging.debug("Deleting custom field")
        custom_field_url = custom_field['_meta']['href']
        response = hub.execute_delete(custom_field_url)
        logging.debug("status code for deleting {} is {}".format(custom_field_url, response.status_code))
else:
    response = hub.delete_cf(args.object, args.field_id)
    logging.debug("status code: {}".format(response.status_code))