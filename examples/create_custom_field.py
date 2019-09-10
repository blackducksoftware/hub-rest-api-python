
#!/usr/bin/env python

import argparse
import json
import logging
import sys

from blackduck.HubRestApi import HubInstance

parser = argparse.ArgumentParser("Work with custom fields")
parser.add_argument("object", choices=["BOM Component", "Component", "Component Version", "Project", "Project Version"], help="The object that the custom field should be attached to")
parser.add_argument("field_type", choices=["BOOLEAN", "DATE", "DROPDOWN", "MULTISELECT", "RADIO", "TEXT", "TEXTAREA"])
parser.add_argument("description")
parser.add_argument("label")
parser.add_argument("-i", "--initial_options", action='append', nargs=2, metavar=('label', 'position'), help="Set the initial options by repeatedly using the -i option, supply a label and position for each possible selection. Used for DROPDOWN, MULTISELECT, and RADIO field types.")
parser.add_argument("-a", "--active", action='store_true', default=False, help="Use the --active option to make the created field active (dafault: Inactive")
parser.add_argument("-p", "--position", default=0, type=int, help="Use the --position option to specify what numeric position the custom field should be displayed in")
args = parser.parse_args()


logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stderr, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.DEBUG)
logging.getLogger("urllib3").setLevel(logging.WARNING)


hub = HubInstance()

logging.debug("Creating custom field using arguments: {}".format(args))

initial_options = [{"label": io[0], "position": io[1]} for io in args.initial_options]

import pdb; pdb.set_trace()

response = hub.create_cf(
    args.object, 
    args.field_type, 
    args.description, 
    args.label, 
    position=args.position,
    active=args.active,
    initial_options=initial_options)

logging.debug("status code: {}".format(response.status_code))




