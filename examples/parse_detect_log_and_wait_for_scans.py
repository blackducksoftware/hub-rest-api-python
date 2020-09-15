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
parser.add_argument("-m", "--max_checks", default=10, type=int, help="Set the maximum number of checks before timing out. Applies to each code/scan location")
parser.add_argument("-c", "--check_delay", default=5, type=int, help="The number of seconds between each check")
args = parser.parse_args()

logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stderr, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

if args.detect_log:
    detect_log = open(args.detect_log, 'r')
else:
    detect_log = sys.stdin

snippet_scan_option_set = False
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
            snippet_scan_option_set = True
            logging.debug("Found snippet scanning option")

    status_file_re = re.search(".*Creating status file: (.*)", line)
    if status_file_re:
        status_file_path = status_file_re[1]
        logging.debug(f"Found status.json path {status_file_path}")

assert start_time, "Hmm, not sure how that happened but we need a start time"

logging.debug(f"detect start time: {start_time}")
logging.debug(f"snippet_scan_option_set: {snippet_scan_option_set}")
logging.debug(f"status.json path: {status_file_path}")

hub = HubInstance()

with open(status_file_path, 'r') as status_file:
    status_info = json.load(status_file)

    # Monitoring status serially cause it's simpler (i.e. than spawning multiple threads and waiting for them)
    scan_results = []
    for code_location in status_info['codeLocations']:
        logging.debug(f"Waiting for scan to finish at scan/code location {code_location['codeLocationName']}")
        is_signature_scan = code_location['codeLocationName'].endswith("scan")
        snippet_scan = is_signature_scan and snippet_scan_option_set
        logging.debug(f"is_signature_scan: {is_signature_scan}, snippet_scan: {snippet_scan}")
        scan_monitor = ScanMonitor(
            hub, 
            start_time=start_time, 
            scan_location_name=code_location['codeLocationName'],
            snippet_scan=snippet_scan,
            max_checks=args.max_checks,
            check_delay=args.check_delay)
        scan_result = scan_monitor.wait_for_scan_completion()
        logging.debug(f"scan result for {code_location['codeLocationName']} was {scan_result}")

    if sum(scan_results) > 0:
        sys.exit(1) # failure
    else:
        sys.exit(0)


