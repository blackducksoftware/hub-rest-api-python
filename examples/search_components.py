#!/usr/bin/env python

import argparse
import json
import logging
import sys

from blackduck.HubRestApi import HubInstance

parser = argparse.ArgumentParser("A program that uses the Black Duck search API to find components...and other things")
parser.add_argument("search_str")

parser.add_argument("-l", "--loglevel", choices=["CRITICAL", "DEBUG", "ERROR", "INFO", "WARNING"], default="DEBUG", help="Choose the desired logging level - CRITICAL, DEBUG, ERROR, INFO, or WARNING. (default: DEBUG)")

args = parser.parse_args()

logging_levels = {
    'CRITICAL': logging.CRITICAL,
    'DEBUG': logging.DEBUG,
    'ERROR': logging.ERROR,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
}
logging.basicConfig(stream=sys.stdout, format='%(threadName)s: %(asctime)s: %(levelname)s: %(message)s', level=logging_levels[args.loglevel])
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

hub = HubInstance()


search_results = hub.search_components(args.search_str)
print(json.dumps(search_results))