#!/usr/bin/env python

'''
Created on May 1, 2019

@author: gsnyder

Wait for scannning results, i.e. after uploading a scan, wait for all the jobs that
process the scan results to complete
'''

import argparse
import arrow
from datetime import datetime
import json
import logging
import sys
import time

from blackduck.HubRestApi import HubInstance, object_id

class ScanMonitor(object):
    def __init__(self, hub, scan_location_name, max_checks=10, check_delay=5, snippet_scan=False):
        self.hub = hub
        self.scan_location_name = scan_location_name
        self.max_checks = max_checks
        self.check_delay = check_delay
        self.snippet_scan = snippet_scan

    def wait_for_scan_completion(self):
        now = arrow.now()

        scan_locations = self.hub.get_codelocations(parameters={'q':f'name:{args.scan_location_name}'}).get('items', [])

        scan_location = scan_locations[0]

        remaining_checks = self.max_checks
        scans_url = self.hub.get_link(scan_location, "scans")
        latest_scan_url = self.hub.get_link(scan_location, "latest-scan")

        if args.snippet_scan:
            logging.debug("Looking for snippet scan which means there will be 2 expected scans")
            number_expected_newer_scans = 2
        else:
            logging.debug("Not looking for snippet scan which means there will be 1 expected scans")
            number_expected_newer_scans = 1

        while remaining_checks > 0:
            scans = self.hub.execute_get(scans_url).json().get('items', [])

            newer_scans = list(filter(lambda s: arrow.get(s['createdAt']) > now, scans))
            logging.debug(f"Found {len(newer_scans)} newer scans")
            
            expected_scans_seen = len(newer_scans) == number_expected_newer_scans
            logging.debug(f"expected_scans_seen: {expected_scans_seen}")

            if expected_scans_seen and all([s['status'] == 'COMPLETE' for s in newer_scans]):
                logging.info("Scans have finished processing")
                break
            else:
                remaining_checks -= 1
                logging.debug(f"Sleeping for {args.time_between_checks} seconds before checking again. {remaining_checks} remaining")
                time.sleep(args.time_between_checks)


if __name__ == "__main__":
    parser = argparse.ArgumentParser("Wait for scan processing to complete for a given code (scan) location/name")
    parser.add_argument("scan_location_name", help="The scan location name")
    parser.add_argument('-m', '--max_checks', type=int, default=10, help="Set the maximum number of checks before quitting")
    parser.add_argument('-t', '--time_between_checks', type=int, default=5, help="Set the number of seconds to wait in-between checks")
    parser.add_argument('-s', '--snippet_scan', action='store_true', help="Select this option if you want to wait for a snippet scan to complete along with it's corresponding component scan.")
    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stderr, level=logging.DEBUG)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    hub = HubInstance()

    scan_monitor = ScanMonitor(hub, args.scan_location_name, args.max_checks, args.time_between_checks, args.snippet_scan)
    scan_monitor.wait_for_scan_completion()
