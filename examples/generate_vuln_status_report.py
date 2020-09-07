'''
Created on Jan 15, 2020

@author: gsnyder

Generate vulnerability status report
'''

from blackduck.HubRestApi import HubInstance

import argparse
import json
import time

parser = argparse.ArgumentParser("A program to create a vulnerability status report")
parser.add_argument("--file_name", default="vuln_status_report")
parser.add_argument('-f', '--format', default='CSV', choices=["CSV", "JSON"], help="Report format")
parser.add_argument('-t', '--tries', default=4, type=int, help="How many times to retry downloading the report, i.e. wait for the report to be generated")
parser.add_argument('-s', '--sleep_time', default=5, type=int, help="The amount of time to sleep in-between (re-)tries to download the report")

args = parser.parse_args()

hub = HubInstance()

class FailedReportDownload(Exception):
	pass

def download_report(location, report_format, filename, retries=args.tries):
	report_id = location.split("/")[-1]

	if retries:
		print("Retrieving generated report from {}".format(location))
		# response = hub.download_vuln_status_report(location)
		response = hub.execute_get(location)

		if response.status_code == 200:
			report_obj = response.json()
			download_url = hub.get_link(report_obj, "download") + ".json"
			content_url = hub.get_link(report_obj, "content")
			if report_format == "CSV":
				download_filename = filename + ".zip"
				response = hub.execute_get(download_url,  {'Content-Type': 'application/zip'})
			else:
				download_filename = filename + ".json"
				response = hub.execute_get(content_url)

			if response.status_code == 200:
				if report_format == "CSV":
					with open(download_filename, "wb") as f:
						f.write(response.content)
					print("Successfully downloaded zip file to {} for report {}".format(
						download_filename, report_id))
				else:
					with open(download_filename, "w") as f:
						json.dump(response.json(), f, indent=3)
					print("Successfully downloaded json report data to {} for report {}".format(
						download_filename, report_id))
			else:
				print("Failed to retrieve report {}".format(report_id))
				print(f"Probably not ready yet, waiting {args.sleep_time} seconds then retrying...")
				time.sleep(args.sleep_time)
				retries -= 1
				download_report(location, report_format, filename, retries)
		else:
			print("Failed to find report information at location {}, status code: {}".format(location, response.status_code))
	else:
		raise FailedReportDownload("Failed to retrieve report {} after {} retries".format(report_id, args.tries))

response = hub.create_vuln_status_report(format=args.format)

if response.status_code == 201:
	print("Successfully created vulnerability status report")
	location = response.headers['Location']
	download_report(location, args.format, args.file_name)
else:
	print("Failed to create vulnerability status report, status code returned: {}".format(response.status_code))
