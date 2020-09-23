#!/usr/bin/env python

'''
Created on May 1, 2019

@author: gsnyder

Wait for scannning results, i.e. after uploading a scan, wait for all the jobs that
process the scan results to complete
'''

import argparse
import arrow
import json
import logging
import sys
import time

from blackduck.HubRestApi import HubInstance, object_id

class ScanMonitor(object):
    SUCCESS = 0
    FAILURE = 1
    TIMED_OUT = 2

    def __init__(self, hub, scan_location_name, max_checks=10, check_delay=5, snippet_scan=False, start_time = None):
        self.hub = hub
        self.scan_location_name = scan_location_name
        self.max_checks = max_checks
        self.check_delay = check_delay
        self.snippet_scan = snippet_scan
        if not start_time:
            self.start_time = arrow.now()
        else:
            self.start_time = start_time

    def wait_for_scan_completion(self):
        scan_locations = self.hub.get_codelocations(parameters={'q':f'name:{self.scan_location_name}'}).get('items', [])

        scan_location = scan_locations[0]

        remaining_checks = self.max_checks
        scans_url = self.hub.get_link(scan_location, "scans")

        if self.snippet_scan:
            logging.debug("Looking for snippet scan which means there will be 2 expected scans")
            number_expected_newer_scans = 2
        else:
            logging.debug("Not looking for snippet scan which means there will be 1 expected scans")
            number_expected_newer_scans = 1

        while remaining_checks > 0:
            scans = self.hub.execute_get(scans_url).json().get('items', [])

            newer_scans = list(filter(lambda s: arrow.get(s['updatedAt']) > self.start_time, scans))
            logging.debug(f"Found {len(newer_scans)} newer scans")
            
            expected_scans_seen = len(newer_scans) == number_expected_newer_scans
            logging.debug(f"expected_scans_seen: {expected_scans_seen}")

            if expected_scans_seen and all([s['status'] in ['COMPLETE', 'FAILURE'] for s in newer_scans]):
                logging.info("Scans have finished processing")
                if all([s['status'] == 'COMPLETE' for s in newer_scans]):
                    return ScanMonitor.SUCCESS
                else:
                    return ScanMonitor.FAILURE
            else:
                remaining_checks -= 1
                logging.debug(f"Sleeping for {self.check_delay} seconds before checking again. {remaining_checks} remaining")
                time.sleep(self.check_delay)

        return ScanMonitor.TIMED_OUT


if __name__ == "__main__":
    parser = argparse.ArgumentParser("Wait for scan processing to complete for a given code (scan) location/name and provide an exit status - 0 successful, 1 failed, and 2 timed-out")
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
