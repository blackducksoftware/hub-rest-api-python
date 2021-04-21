'''
Created on Feb 28, 2019

@author: gsnyder

Get job statistics

'''
import argparse
import json
import logging
import sys

from terminaltables import AsciiTable

from blackduck.HubRestApi import HubInstance

logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', stream=sys.stderr, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

hub = HubInstance()

try:
	job_statistics = hub.get_job_statistics()
except:
	job_statistics = None
	logging.error("Failed to retreive job statistics", exc_info=True)

if job_statistics and 'items' in job_statistics:
	job_table = [[
		"jobType",
		"totalRuns",
		"totalSuccess",
		"totalFailures",
		"totalInProgress",
		"averageRunTime"
	]]
	for job in job_statistics['items']:
		job_table_row = [v for k,v in job.items()]
		job_table.append(job_table_row)

	print(AsciiTable(job_table).table)
else:
	logging.error("Ruh roh, didn't get the job statistics!")