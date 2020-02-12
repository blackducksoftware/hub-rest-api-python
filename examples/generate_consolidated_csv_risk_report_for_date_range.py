"""

Created on December 6, 2019

@author: AMacDonald

A report generator that allows for user to input date range and get information on how many Code Locations have been
created in this time, as well as the counts of high, medium, and low vulnerabilities for the related scans.

Script requires input "start date" and "end date" (though default for end date is today's date), and will document how
many scans were run in that time, specifying the number that were mapped to a project, as well as the counts of how many
components contain at least 1 critical, high, medium and low vulnerability, based on the highest vulnerability score.

CSV report will be generated in the working directory

For this script to run, the hub-rest-api-python library and pandas library will need to be installed.

"""

import argparse
import datetime
import pandas as pd
import time

from blackduck.HubRestApi import HubInstance

hub = HubInstance()
today = datetime.date.today()
timestamp = time.strftime('%m_%d_%Y_%H_%M')
file_out = ('consolidated_risk_report-' + timestamp + '.csv')


parser = argparse.ArgumentParser("Input start date and end date for range you would like report to be generated")
parser.add_argument("--start_date", type=str, help="start date")
parser.add_argument("--end_date", type=str, help="end date, default value is today's date", default=today.strftime('%Y-%m-%d'))
args = parser.parse_args()

scancount = []
bomcount = []
aggregatedlow = {}
aggregatedmedium = {}
aggregatedhigh = {}
aggregatedcritical = {}


def get_scan_counts():
    parameters = {}
    start = datetime.datetime.strptime(args.start_date, '%Y-%m-%d').date()
    end = datetime.datetime.strptime(args.end_date, '%Y-%m-%d').date()
    scans = hub.get_codelocations(limit=10000, parameters=parameters)

    for scan in scans['items']:
        scandate = (scan['createdAt'])
        datetime_object = datetime.datetime.strptime(scandate, '%Y-%m-%dT%H:%M:%S.%fZ').date()
        date1 = datetime_object
        if 'mappedProjectVersion' in scan:
            if start < date1 < end:
                bomcount.append(date1)
                rpl = (scan['mappedProjectVersion'] + '/risk-profile')
                url = rpl
                risk_profile = hub.execute_get(url)
                data = risk_profile.json()
                for key, value in data['categories'].items():
                    if key == "VULNERABILITY":
                        aggregatedcritical['CRITICAL'] = aggregatedcritical.get('CRITICAL', 0) + value['CRITICAL']
                        aggregatedhigh['HIGH'] = aggregatedhigh.get('HIGH', 0) + value['HIGH']
                        aggregatedmedium['MEDIUM'] = aggregatedmedium.get('MEDIUM', 0) + value['MEDIUM']
                        aggregatedlow['LOW'] = aggregatedlow.get('LOW', 0) + value['LOW']

        if start < date1 < end:
            scanlist = scancount
            scanlist.append(scandate)

    count = len(bomcount)
    count2 = len(scanlist)
    df = pd.DataFrame({'Start Date': [start],
                       'Dnd Date': [end],
                       'Mapped Scans': [count],
                       'Total Scans': [count2],
                       'Critical Vuln Components': [aggregatedcritical['CRITICAL']],
                       'High Vuln Components': [aggregatedhigh['HIGH']],
                       'Medium Vuln Components': [aggregatedmedium['MEDIUM']],
                       'Low Vuln Components': [aggregatedlow['LOW']]})
    df.to_csv(file_out, encoding='utf-8', index=False)
    print(df)


def main():
    get_scan_counts()


main()
