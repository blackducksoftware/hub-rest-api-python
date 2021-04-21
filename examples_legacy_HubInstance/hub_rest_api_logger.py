#!/usr/bin/env python

#
# Showing how to attach to the logger for HubRestApi and adjust the level of the logging
#
#       python examples/hub_rest_api_logger.py # shows only INFO messages or higher
#       python examples/hub_rest_api_logger.py -l DEBUG # shows only DEBUG messages or higher
#
# Ref: https://docs.python.org/3/library/logging.html#levels
#

import argparse
import logging
import sys

from blackduck.HubRestApi import HubInstance

logging_levels_d = {
    'CRITICAL': logging.CRITICAL,
    'ERROR': logging.ERROR,
    'WARNING': logging.WARNING,
    'INFO': logging.INFO,
    'DEBUG': logging.DEBUG,
    'NOTSET': logging.NOTSET
}


parser = argparse.ArgumentParser("Showing how to attach to and set the logging level for the HubRestApi")
parser.add_argument(
    "-l", 
    "--level", 
    default = 'INFO',
    choices = logging_levels_d.keys(), 
    help="Set the logging level for the HubRestApi"
)

args = parser.parse_args()

logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stderr, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

logging.getLogger("blackduck.HubRestApi").setLevel(logging_levels_d[args.level])

hub = HubInstance()

projects = hub.get_projects()
