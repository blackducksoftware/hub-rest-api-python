'''
Created on February 25, 2019

@author: gsnyder

Strip BDSA records from the security.csv file generated in the reports for a specific project-version
See https://github.com/blackducksoftware/hub-rest-api-python/blob/master/examples/generate_csv_reports_for_project_version.py
for an example of generating the reports programmatically
'''

from blackduck.HubRestApi import HubInstance

import argparse
import csv

parser = argparse.ArgumentParser("Strip BDSA records from the securty.csv file generated in the reporst for a specific project-version")
parser.add_argument("security_csv_path")
parser.add_argument("output_path")
args = parser.parse_args()

with open(args.security_csv_path) as security_csv_file:
	reader = csv.DictReader(security_csv_file)
	import pdb; pdb.set_trace()
	with open(args.output_path, "w") as output_csv_file:
		writer = csv.DictWriter(output_csv_file, fieldnames=reader.fieldnames)
		writer.writeheader()
		for row in reader:
			if row['Vulnerability source'] != 'BDSA':
				writer.writerow(row)