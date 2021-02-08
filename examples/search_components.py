#!/usr/bin/env python

import argparse
import json
import logging
import math
import sys

from blackduck.HubRestApi import HubInstance

parser = argparse.ArgumentParser("A program that uses the Black Duck search API to find components...and other things")
parser.add_argument("search_str")
parser.add_argument("-l", "--limit", type=int, default=100, help="Set the per call limit on number of results")
parser.add_argument("--loglevel", choices=["CRITICAL", "DEBUG", "ERROR", "INFO", "WARNING"], default="DEBUG", help="Choose the desired logging level - CRITICAL, DEBUG, ERROR, INFO, or WARNING. (default: DEBUG)")

args = parser.parse_args()

logging_levels = {
    'CRITICAL': logging.CRITICAL,
    'DEBUG': logging.DEBUG,
    'ERROR': logging.ERROR,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
}
logging.basicConfig(stream=sys.stderr, format='%(threadName)s: %(asctime)s: %(levelname)s: %(message)s', level=logging_levels[args.loglevel])
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

hub = HubInstance()

offset=0

hits = []
num_results_found = math.inf
first = True

while offset < num_results_found:
    parameters = {
        'limit': args.limit,
        'offset': offset,
    }
    search_results = hub.search_components(args.search_str, parameters=parameters)
    if first:
        first = False
        num_results_found = search_results['items'][0]['searchResultStatistics']['numResultsFound']
        logging.debug(f"Search ({args.search_str}) numResultsFound: {num_results_found}")

    hits.extend(search_results['items'][0]['hits'])
    num_results_this_page = search_results['items'][0]['searchResultStatistics']['numResultsInThisPage']

    offset += args.limit
    logging.debug(f"Retrieved {num_results_this_page} out of {num_results_found}, setting offset to {offset}")

logging.debug(f"Retreived a total of {len(hits)} hits")
print(json.dumps(hits))



