#!/usr/bin/env python

'''
Created on May 1, 2019

@author: gsnyder

Wait for scannning results, i.e. after uploading a scan, wait for all the jobs that
process the scan results to complete
'''

import argparse
from datetime import datetime
import json
import logging
import sys
import time
import timestring

from blackduck.HubRestApi import HubInstance, object_id

parser = argparse.ArgumentParser("Wait for scan processing to complete for a given code (scan) location/name")
parser.add_argument("scan_location_name", help="The scan location name")
parser.add_argument('-m', '--max_checks', type=int, default=10, help="Set the maximum number of checks before quitting")
parser.add_argument('-t', '--time_between_checks', default=5, help="Set the number of seconds to wait in-between checks")
parser.add_argument('-s', '--snippet_scan', action='store_true', help="Select this option if you want to wait for a snippet scan to complete along with it's corresponding component scan.")
args = parser.parse_args()

logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stderr, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

hub = HubInstance()

def get_project_and_version_name(project_version_url):
    # Get the project and version name and return them concatenated for use to lookup relevant jobs
    response = hub.execute_get(project_version_url)
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
    return "{} {}".format(project_name, version_name)

def get_jobs_from_scan(scan_location, scan_summary_ids, project_version_id, project_version_url, later_than):
    '''Get the most recent jobs pertaining to the processing of scans for the given scan location
    and the BOM processing for the given the project-version id
    '''

    # TODO: Refactor

    assert isinstance(later_than, str), "later_than should be a date/time string parseable by timestring"
    later_than = timestring.Date(later_than).date

    # See https://jira.dc1.lan/browse/HUB-14263 - Rest API for Job status
    # The below is using a private endpoint that could change on any release and break this code
    jobs_url = hub.get_urlbase() + "/api/v1/jobs?limit={}".format(100)
    response = hub.execute_get(jobs_url)
    jobs = []
    if response.status_code == 200:
        jobs = response.json().get('items', [])
    else:
        logging.error("Failed to retrieve jobs, status code: {}".format(response.status_code))

    jobs_with_job_descriptions = list(filter(lambda j: 'jobEntityDescription' in j, jobs))

    #
    # Get jobs related to the project-version this scan is mapped to
    #
    if project_version_url:
        pv_name = get_project_and_version_name(project_version_url)

        pv_jobs = list(filter(
            lambda j: pv_name in j.get('jobEntityDescription', []) and timestring.Date(j['createdAt']).date > later_than, 
            jobs_with_job_descriptions))
        pv_job_types = set([pj['jobSpec']['jobType'] for pj in pv_jobs])
    else:
        pv_jobs = []
        pv_job_types = set()

    #
    # Get most recent scanning jobs
    #

    #   SnippetScanAutoBomJob does not have the code (scan) location name associated with it
    #   so we have to pass in the scan id's and find job that way
    #   For the other scan jobs they have a description that includes the code location name
    #

    # TODO: filter for later_than?

    s_jobs = list(filter(
        lambda j: scan_location in j.get('jobEntityDescription', []) or j['jobSpec']['entityKey']['entityId'] in scan_summary_ids,
        jobs))
    s_job_types = set([sj['jobSpec']['jobType'] for sj in s_jobs])

    # Get most recent job for each job type to trim off the historic jobs
    most_recent_pv_jobs = get_most_recent_jobs(pv_job_types, pv_jobs)
    most_recent_s_jobs = get_most_recent_jobs(s_job_types, s_jobs)

    return most_recent_pv_jobs + most_recent_s_jobs

def get_most_recent_jobs(job_types, jobs):
    most_recent_l = list()
    for job_type in job_types:
        filtered_to_type = list(filter(lambda j: j['jobSpec']['jobType'] == job_type, jobs))
        most_recent = sorted(filtered_to_type, key = lambda j: j['startedAt'])[-1]
        most_recent_l.append(most_recent)
    return most_recent_l

def get_scan_summaries(scan_location, snippet_scan=False):
    '''Find and return scan summary information and project-version information for the given scan location (name)
    '''
    scan_locations = hub.get_codelocations(parameters={'q':'name:{}'.format(
        scan_location)})
    all_scan_summaries = []
    most_recent_scan_summaries = []
    all_project_version_ids = set()
    all_project_version_urls = set()
    for scan_location in scan_locations.get('items', []):
        mapped_project_version = scan_location.get('mappedProjectVersion')

        if mapped_project_version:
            mapped_project_version_id = mapped_project_version.split('/')[-1]
            all_project_version_ids.add(mapped_project_version_id)
            all_project_version_urls.add(mapped_project_version)

        scan_location_id = object_id(scan_location)
        
        scan_summaries = hub.get_codelocation_scan_summaries(scan_location_id)
        scan_summaries = scan_summaries.get('items', [])
        scan_summaries = sorted(scan_summaries, key=lambda ss: ss['updatedAt'])

        all_scan_summaries.extend(scan_summaries)
        if snippet_scan:
            # When using a snippet scan we need to look at the two most recent
            most_recent = scan_summaries[-2:]
        else:
            # Otherwise, we can look at the single most recent
             most_recent = scan_summaries[-1:]
        most_recent_scan_summaries.extend(most_recent)

    all_scan_summary_ids = list(set(
            [object_id(ss) for ss in all_scan_summaries]
        ))
    most_recent_scan_summary_ids = list(set(
        [object_id(ss) for ss in most_recent_scan_summaries]
    ))

    if all_project_version_ids:
        assert len(all_project_version_ids) == 1, "The must be one, and only one, project-version this scan location is mapped to"

        project_version_id = list(all_project_version_ids)[0]
    else:
        project_version_id = None

    if all_project_version_urls:
        assert len(all_project_version_urls) == 1, "The must be one, and only one, project-version this scan location is mapped to"
        project_version_url = list(all_project_version_urls)[0]
    else:
        project_version_url = None

    # To find the right jobs we use the "oldest" createdAt dt from the
    # pertinent scan summaries
    later_than = min([ss['createdAt'] for ss in most_recent_scan_summaries])

    return {
        'all_scan_summaries': all_scan_summaries, 
        'all_scan_summary_ids': all_scan_summary_ids, 
        'most_recent_scan_summaries': most_recent_scan_summaries, 
        'most_recent_scan_summary_ids': most_recent_scan_summary_ids, 
        'project_version_id': project_version_id,
        'project_version_url': project_version_url,
        'later_than': later_than
    }

def exit_status(scan_location, snippet_scan=False):
    '''Determine the exit status value. If all of the related jobs or scan summaries
    are 'complete' (successful) we return 0, otherwise 1
    '''
    summary_info = get_scan_summaries(scan_location, snippet_scan)
    scan_summaries = summary_info['most_recent_scan_summaries']
    scan_ids = summary_info['all_scan_summary_ids']
    pv_id = summary_info['project_version_id']
    pv_url = summary_info['project_version_url']
    later_than = summary_info['later_than']
    log_scan_summary_info(scan_summaries)

    related_jobs = get_jobs_from_scan(
        scan_location, scan_ids, pv_id, pv_url, later_than)
    log_related_jobs_info(related_jobs)
    if all([ss['status'] == 'COMPLETE' for ss in scan_summaries]) and all([j['status'] == 'COMPLETED' for j in related_jobs]):
        return 0
    else:
        return 1

def log_related_jobs_info(related_jobs):
    jobs_status_view = [
        {
            'status': j['status'],
            'createdAt': j['createdAt'],
            'jobType': j['jobSpec']['jobType'],
            'jobEntityDescription': j.get('jobEntityDescription')
        } for j in related_jobs
    ]
    logging.debug("Related job statuses: {}".format(jobs_status_view))

def log_scan_summary_info(scan_summaries):
    scan_status_view = [
        {
            'status': ss['status'],
            'createdAt': ss['createdAt'],
            'statusMessage': ss.get('statusMessage'),
            'scanId': object_id(ss),
        } for ss in scan_summaries
    ]
    logging.debug("Scan statuses: {}".format(scan_status_view))

#
# Main
# 
not_completed = True
something_has_run = False
completed = False

max_checks = args.max_checks
while max_checks > 0:
    summary_info = get_scan_summaries(args.scan_location_name, args.snippet_scan)
    scan_summaries = summary_info['most_recent_scan_summaries']
    scan_ids = summary_info['all_scan_summary_ids']
    pv_id = summary_info['project_version_id']
    pv_url = summary_info['project_version_url']
    later_than = summary_info['later_than']

    related_jobs = get_jobs_from_scan(
        args.scan_location_name, scan_ids, pv_id, pv_url, later_than)

    log_scan_summary_info(scan_summaries)
    log_related_jobs_info(related_jobs)

    if not something_has_run:
        logging.info("Checking if anything has run yet. If we missed it, we will stop checking after {} more retries".format(max_checks))
        something_has_run = any(
                j['status'] == 'RUNNING' for j in related_jobs
            )
        logging.debug('Something has run: {}'.format(something_has_run))
        if something_has_run:
            continue
        else:
            logging.info("Waiting {} seconds before checking again for a running job".format(
                args.time_between_checks))
            time.sleep(args.time_between_checks)
    else:
        # TODO: Find out what a 'failed' scan summary produces and incorporate that below
        if args.snippet_scan:
            logging.debug("snippet scan")
            rj_completed = all([j['status'] == 'COMPLETED' or j['status'] == 'FAILED' for j in related_jobs])
            logging.debug("rj_completed: {}".format(rj_completed))
            ss_completed = all([ss['status'] == 'COMPLETE' for ss in scan_summaries])
            logging.debug("ss_completed: {}".format(ss_completed))
            completed = rj_completed and ss_completed
        else:
            logging.debug("component scan")
            completed = all([ss['status'] == 'COMPLETE' for ss in scan_summaries])
        logging.debug("completed: {}".format(completed))
        if completed:
            break
        logging.info("Waiting {} seconds before checking status again".format(
            args.time_between_checks))
        time.sleep(args.time_between_checks)
    max_checks -= 1
    logging.debug('checks remaining {}'.format(max_checks))

exit_status_value = exit_status(args.scan_location_name, args.snippet_scan)
logging.debug("Setting exit status to {}".format(exit_status_value))
sys.exit(exit_status_value)




