import argparse
import json
import logging
import sys

from blackduck.HubRestApi import HubInstance

parser = argparse.ArgumentParser("Work with custom fields")
parser.add_argument("object_url", help="The URL to the specific object (e.g. project, project-version, component, BOM component) whose custom field you want to update")
parser.add_argument("field_label", help="The label of the custom field to update on the object")
parser.add_argument("new_value", help="The new value to assign to the custom field. Note: In some cases the new value is a URL, e.g. to a custom field selection value")
args = parser.parse_args()


logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stderr, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.DEBUG)
logging.getLogger("urllib3").setLevel(logging.WARNING)


hub = HubInstance()

obj = hub.execute_get(args.object_url).json()

custom_fields = hub.get_cf_values(obj).get('items', [])

cf_to_modify = None
for cf in custom_fields:
    if cf['label'].lower() == args.field_label.lower():
        cf_to_modify = cf
        break

import pdb; pdb.set_trace()

if cf_to_modify:
    logging.debug("Updating custom field {} with value {}".format(cf_to_modify, args.new_value))
    cf_to_modify['values'] = [args.new_value]
    url = cf_to_modify['_meta']['href']
    response = hub.put_cf_value(url, cf_to_modify)
    if response.status_code == 200:
        logging.info("succeeded updating custom field {} at {} with new value {}".format(args.field_label, args.object_url, args.new_value))
    else:
        logging.error("succeeded updating custom field {} at {} with new value {}. status code returned was: {}".format(
            args.field_label, args.object_url, args.new_value, response.status_code))
else:
    logging.error("Failed to find a custom field with label={} at {}".format(args.field_label, args.object_url))