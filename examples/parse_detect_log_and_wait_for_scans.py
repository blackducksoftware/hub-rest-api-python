#!/usr/bin/env python

'''
Created on Sep 2, 2020

@author: gsnyder

Parse the Synopsys Detect log to get the status.json file emitted and use status.json to monitor
the scans (codelocations) and wait for the scan processing to complete
'''

import argparse
import arrow
import json
import logging
import re
import sys
import time
from tzlocal import get_localzone # pip install tzlocal

from blackduck.HubRestApi import HubInstance, object_id

# Ensure your PYTHONPATH includes the folder where this class is defined
from wait_for_scan_results import ScanMonitor


parser = argparse.ArgumentParser("Parse the Synopsys Detect log, load status.json, and wait for all scan processing to complete")
parser.add_argument("-d", "--detect_log", help="By default, this script will read the detect log from stdin, but you can alternatively supply a detect log filename")
# parser.add_argument('-m', '--max_checks', type=int, default=10, help="Set the maximum number of checks before quitting")
# parser.add_argument('-t', '--time_between_checks', type=int, default=5, help="Set the number of seconds to wait in-between checks")
# parser.add_argument('-s', '--snippet_scan', action='store_true', help="Select this option if you want to wait for a snippet scan to complete along with it's corresponding component scan.")
args = parser.parse_args()

logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stderr, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

if args.detect_log:
    detect_log = open(args.detect_log, 'r')
else:
    detect_log = sys.stdin

snippet_scan = False
status_file_path = None
start_time = None

for line in detect_log.readlines():
    if not start_time:
        start_time_re = re.search("(.*) INFO .*", line)
        if start_time_re:
            start_time = arrow.get(start_time_re[1], tzinfo=get_localzone())
            logging.debug(f"Found detect start time {start_time}")

    cleanup_prop = re.search(".*detect.cleanup = (true|false).*", line)
    if cleanup_prop:
        if cleanup_prop[1] == 'true':
            logging.error("You must use --detect.cleanup=false to preserve the status.json file, exiting")
            sys.exit(1)

    snippet_matching_re = re.search(".*detect.blackduck.signature.scanner.snippet.matching = (.*)", line)
    if snippet_matching_re:
        if 'SNIPPET' in snippet_matching_re[1]:
            snippet_scan = True
            logging.debug("Found snippet scanning option")

    status_file_re = re.search(".*Creating status file: (.*)", line)
    if status_file_re:
        status_file_path = status_file_re[1]
        logging.debug(f"Found status.json path {status_file_path}")

assert start_time, "Hmm, not sure how that happened but we need a start time"

logging.debug(f"detect start time: {start_time}")
logging.debug(f"snippet_scan: {snippet_scan}")
logging.debug(f"status.json path: {status_file_path}")

hub = HubInstance()

with open(status_file_path, 'r') as status_file:
    status_info = json.load(status_file)

    # Monitoring status serially cause it's simpler (i.e. than spawning multiple threads and waiting for them)
    for code_location in status_info['codeLocations']:
        logging.debug(f"Waiting for scan to finish at scan/code location {code_location['codeLocationName']}")
        scan_monitor = ScanMonitor(
            hub, 
            start_time=start_time, 
            scan_location_name=code_location['codeLocationName'],
            snippet_scan=snippet_scan)
        scan_monitor.wait_for_scan_completion()


