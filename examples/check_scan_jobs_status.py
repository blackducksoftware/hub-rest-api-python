#!/usr/bin/env python

'''
Created on May 16, 2019

@author: gsnyder

Check scan (job) processing results for all scan locations
'''

import argparse
from datetime import datetime
import json
import logging
import sys
import time
import timestring
from terminaltables import AsciiTable

from blackduck.HubRestApi import HubInstance, object_id

class CodeLocationStatusChecker(object):
    '''Check the status of the code (scan) location processing - i.e. check that relevant jobs to ensure
    they completed successfully.
    '''
    jobs = None 
    hub = None 

    @classmethod
    def initialize(cls):
        if not cls.hub:
            logging.debug("setting hub")
            cls.hub = HubInstance()

        if not cls.jobs:
            logging.debug("retrieving jobs")
            cls.jobs = cls.hub.get_jobs().get('items', [])

    def __init__(self, code_location_obj):
        self.initialize()
        self.code_location_obj = code_location_obj
        self.scan_history = self._get_scans(self.code_location_obj)
        self.most_recent_scans = self._most_recent_scans(self.scan_history)
        self.project_name, self.version_name = self._get_project_and_version_name()
        self.related_jobs = self._get_related_jobs(self.most_recent_scans, self.project_name, self.version_name)
        self.failed_scans = self.failed_jobs = self.inprogress_jobs = None

    def _get_project_and_version_name(self):
        # Get the project and version name and return them concatenated for use to lookup relevant jobs
        if 'mappedProjectVersion' not in self.code_location_obj:
            raise Exception("This code location is unmapped so checking on status is not meaningful")
        else:
            response = self.hub.execute_get(self.code_location_obj['mappedProjectVersion'])
            if response.status_code == 200:
                project_version_obj = response.json()
            else:
                raise Exception("Unable to retrieve project version at URL {}".format(
                    project_version_url))

            version_name = project_version_obj['versionName']
            project_url = hub.get_link(project_version_obj, "project")
            response = hub.execute_get(project_url)
            if response.status_code == 200:
                project_obj = response.json()
            else:
                raise Exception("Could not find the project associated with the project version")

            project_name = project_obj['name']
            return project_name, version_name

    def _get_scans(self, code_location_obj):
        # TODO: Scans are returned in reverse chronological order, but should we be safe and sort here?
        scan_summaries = self.hub.get_codelocation_scan_summaries(code_location_obj = code_location_obj).get("items", [])
        for scan_summary in scan_summaries:
            scan_id = object_id(scan_summary)
            url = self.hub.get_apibase() + "/v1/scans/{}".format(scan_id)
            response = hub.execute_get(url)
            scan_details = response.json() if response.status_code == 200 else None
            scan_summary['scan_details'] = scan_details

        # Check that they all share the same code (scan) location name
        names = set([s['scan_details']['name'] for s in scan_summaries])
        assert len(names) == 1, "Uh oh, all the scans for a given code (scan) location should have the same name"

        return scan_summaries

    def _most_recent_scans(self, scan_history):
        '''Scan history is assumed to be list of prior scans, sorted reverse chronological order
        '''
        if self.has_snippet_scan(scan_history):
            return scan_history[:2]
        else:
            return scan_history[-1:]

    def _get_most_recent_jobs(self, job_types, jobs):
        most_recent_l = list()
        for job_type in job_types:
            filtered_to_type = list(filter(lambda j: j['jobSpec']['jobType'] == job_type, jobs))
            most_recent = sorted(filtered_to_type, key = lambda j: j['startedAt'])[-1]
            most_recent_l.append(most_recent)
        return most_recent_l

    def _get_related_jobs(self, most_recent_scans, project_name, version_name):
        later_than = min([s['createdAt'] for s in most_recent_scans])
        later_than = timestring.Date(later_than).date
        pv_name = "{} {}".format(project_name, version_name)
        scan_loc_name = most_recent_scans[0]['scan_details']['name']
        scan_ids = [mrs['scan_details']['scanSourceId'] for mrs in most_recent_scans]

        jobs = CodeLocationStatusChecker.jobs

        jobs_with_job_descriptions = list(filter(lambda j: 'jobEntityDescription' in j, jobs))

        pv_jobs = list(filter(
            lambda j: pv_name in j.get('jobEntityDescription', []) and timestring.Date(j['createdAt']).date > later_than, 
            jobs_with_job_descriptions))
        pv_job_types = set([pj['jobSpec']['jobType'] for pj in pv_jobs])

        s_jobs = list(filter(
            lambda j: scan_loc_name in j.get('jobEntityDescription', []) or j['jobSpec']['entityKey']['entityId'] in scan_ids,
            jobs))
        # TODO: Filter again for later_than? or pre-filter for later_than?
        s_job_types = set([sj['jobSpec']['jobType'] for sj in s_jobs])

        most_recent_pv_jobs = self._get_most_recent_jobs(pv_job_types, pv_jobs)
        most_recent_s_jobs = self._get_most_recent_jobs(s_job_types, s_jobs)

        combined_recent_jobs = most_recent_pv_jobs + most_recent_s_jobs
        # de-dup; see https://stackoverflow.com/questions/11092511/python-list-of-unique-dictionaries
        combined_recent_jobs = list({j['id']: j for j in combined_recent_jobs}.values())

        return combined_recent_jobs

    def has_snippet_scan(self, scan_history):
        return any([s['scan_details']['scanType'].lower() == "snippet" for s in scan_history[:2]])

    def status(self):
        if self.has_snippet_scan(self.scan_history):
            scans_to_check = self.scan_history[:2]
        else:
            scans_to_check = self.scan_history[-1:]

        assert len(scans_to_check) > 0, "Uh oh, no scans to check. That shouldn't happen."
        assert len(self.related_jobs) > 0, "Uh oh, no related jobs to check. That shouldn't happen."

        self.completed_scans = [s['status'].lower() == "complete" for s in scans_to_check] 
        self.completed_jobs = [j['status'].lower() == "completed" for j in self.related_jobs]

        self.failed_jobs = [j for j in self.related_jobs if j['status'].lower() == "failed"]
        self.failed_scans = [s for s in scans_to_check if 'fail' in s['status'].lower()]
        self.incomplete_scans = [s for s in scans_to_check if s['status'].lower() != "complete"]
        self.incomplete_jobs = [j for j in self.related_jobs if j['status'].lower() != "completed"]

        if any(self.failed_jobs + self.failed_scans):
            return "failed"
        elif any(self.incomplete_jobs + self.incomplete_scans):
            return "in-progress"
        elif all(self.completed_jobs + self.completed_scans):
            return "succeeded"


if __name__ == "__main__":
    parser = argparse.ArgumentParser("Check scan processing results")
    parser.add_argument("-l", "--scan_location_name", help="A scan location name for if you only want to check one")
    parser.add_argument('-s', '--snippet_scans', action='store_true', help="Select this option if you want to wait for a snippet scan to complete along with it's corresponding component scan.")
    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stderr, level=logging.DEBUG)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    hub = HubInstance()

    logging.debug("Retrieving code locations")
    code_locations = hub.get_codelocations(limit=9999).get('items', [])
    code_location_checks = {}

    ttable = [[
        "scan location",
        "scan types",
        "status",
        "details"
    ]]

    for code_location in code_locations:
        logging.debug("Checking code location {}".format(code_location['name']))
        checker = CodeLocationStatusChecker(code_location)
        checker_status = checker.status()
        code_location_checks.update({code_location['name']: checker_status})

        related_job_types = [j['jobSpec']['jobType'] for j in checker.related_jobs]
        scan_types = ",".join([s['scan_details']['scanType'] for s in checker.most_recent_scans])

        if checker_status == "succeeded":
            details = "Jobs " + ",".join(related_job_types) + " all succeeded"
        elif checker_status == "in-progress":
            if checker.incomplete_jobs:
                incomplete_jobs = [ipj['jobSpec']['jobType'] for ipj in checker.incomplete_jobs]
                details = "Jobs " + ",".join(incomplete_jobs) + " are still in-progress"
            if checker.incomplete_scans:
                incomplete_scans = [
                    "name '{}'; id {}: status {}".format(
                        s['scan_details']['name'], s['scan_details']['scanSourceId'], s['status'])
                        for s in checker.incomplete_scans
                ]
                details = "Scans not completed. " + ",".join(incomplete_scans)
        elif checker_status == "failed":
            if checker.failed_scans:
                failed_scans = [
                    "name '{}'; id {}: status {}".format(
                        s['scan_details']['name'], s['scan_details']['scanSourceId'], s['status'])
                        for s in checker.failed_scans
                ]
                details = "Scans failed. " + ",".join(failed_scans)
            if checker.failed_jobs:
                failed_jobs = [fj['jobSpec']['jobType'] for fj in checker.failed_jobs]
                details += "Jobs " + ",".join(failed_jobs) + " failed"
        logging.debug("{} {}".format(code_location['name'], details))
        ttable.append([code_location['name'], scan_types, checker_status, details])

    print(AsciiTable(ttable).table)

    if all([status for k,status in code_location_checks.items()]):
        sys.exit(0)
    else:
        sys.exit(1)



