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

        logging.debug(f"Scan locations found: {len(scan_locations)}")

        remaining_checks = self.max_checks

        while remaining_checks > 0:

            for scan_location in scan_locations:
            
                scans_url = self.hub.get_link(scan_location, "scans")
                
                scans = self.hub.execute_get(scans_url).json().get('items', [])
                
                newer_scans = list(filter(lambda s: arrow.get(s['updatedAt']) > self.start_time, scans))

                if (len(newer_scans) > 0):
                    if len(newer_scans) > 0 and self.snippet_scan:
                        # We are snippet scanning, we need to check if we should be waiting for another scan.  Only the case if one of them is FS or if one is SNIPPET.  If one is BDIO then it will not have snippet.
                        fs_scans = list(filter(lambda s: s['scanType'] == 'FS', newer_scans))
                        snippet_scans = list(filter(lambda s: s['scanType'] == 'SNIPPET', newer_scans))
                        if len(fs_scans) > 0 or len(snippet_scans) > 0:
                            # This is a candicate for snippet scan
                            expected_scans_seen = len(fs_scans) > 0 and len(snippet_scans) > 0
                            logging.debug(f"Snippet scanning - candidate code location - newer scans {len(newer_scans)}, expected_scans_seen: {expected_scans_seen} for {scan_location['name']}")
                        else:
                            # This is another type of scan. 
                            expected_scans_seen = True
                            logging.debug(f"Snippet scanning - non snippet code location - newer scans {len(newer_scans)}, expected_scans_seen: {expected_scans_seen} for {scan_location['name']}")

                    else:
                        # We have one or more newer scans
                        expected_scans_seen = True
                        logging.debug(f"Not Snippet scanning - newer scans {len(newer_scans)}, expected_scans_seen: {expected_scans_seen} for {scan_location['name']}")
                else:
                    logging.debug(f"No newer scans found for {scan_location['name']}")
                    expected_scans_seen = False

                if expected_scans_seen and all([s['status'] in ['COMPLETE', 'FAILURE'] for s in newer_scans]):
                    logging.info(f"Scans have finished processing for {scan_location['name']}")
                    if all([s['status'] == 'COMPLETE' for s in newer_scans]):
                        # All scans for this code location are complete, remove from the list we are waiting on.
                        scan_locations.remove(scan_location)
                    else:
                        return ScanMonitor.FAILURE
            
            if len(scan_locations) == 0:
                # All code locations are complete.
                return ScanMonitor.SUCCESS

            remaining_checks -= 1
            logging.info(f"Waiting for {len(scan_locations)} code locations.  Sleeping for {self.check_delay} seconds before checking again. {remaining_checks} remaining")
            time.sleep(self.check_delay)

        logging.debug("We timed out, exiting")

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
