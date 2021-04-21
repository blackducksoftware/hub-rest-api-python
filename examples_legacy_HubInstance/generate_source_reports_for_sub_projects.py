"""
generate_source_report_for_sub_projects

Created on November 6, 2019

@author: AMacDonald

Script designed to generate and collate Source reports for sub-projects that are part of a master project.

To run this script, you will need to pass arguments for the master project name and the master project version.  Once
they are specified, the script will investigate to see if the master project contains sub-projects and will generate
reports for all sub-projects it discovers. Finally, it will combine them into a single report, saving it to a "results"
sub-directory.

For this script to run, the hub-rest-api-python library and pandas library will need to be installed.

"""

import argparse
from blackduck.HubRestApi import HubInstance
import time
from zipfile import ZipFile
import shutil
import os
import glob
import pandas

parser = argparse.ArgumentParser("A program to create consolidated Source report for sub projects")
parser.add_argument("project_name")
parser.add_argument("version_name")

args = parser.parse_args()
hub = HubInstance()
FILES = ["FILES"]  # as hub.create_version_reports requires the parameters to be an array/list
projversion = hub.get_project_version_by_name(args.project_name, args.version_name)
components = hub.get_version_components(projversion)
csv_list = []
projname = args.project_name
timestamp = time.strftime('%m_%d_%Y_%H_%M')
file_out = (projname + '_' + "Consolidated_src_report-" + timestamp)
file_out = (file_out + ".csv")


class FailedReportDownload(Exception):
    pass


def download_report(location, filename, retries=4):
    report_id = location.split("/")[-1]

    if retries:
        print("Retrieving generated report from {}".format(location))
        response = hub.download_report(report_id)
        if response.status_code == 200:
            with open(filename, "wb") as f:
                f.write(response.content)

            print("Successfully downloaded zip file to {} for report {}".format(filename, report_id))
        else:
            print("Failed to retrieve report {}".format(report_id))
            print("Probably not ready yet, waiting 5 seconds then retrying...")
            time.sleep(5)
            retries -= 1
            download_report(location, filename, retries)
    else:
        raise FailedReportDownload("Failed to retrieve report {} after multiple retries".format(report_id))


def genreport():
    for component in components['items']:
        subname = (component['componentName'] + '_' + component['componentVersionName'] + '.zip')
        subname = (subname.replace(" ", ""))
        # Above step is to generate the output from the get_version_components and specifically look at the activityData
        # portion to indicate whether a component is a KB component, or a subproject.
        if len(component['activityData']) == 0:
            # Above checks length of output from activityData is >0. If equals 0, is sub-project.
            print('activityData is empty, is subproject')
            version = hub.get_project_version_by_name(component['componentName'],component['componentVersionName'])
            # Above determines the project name from hub.get_project_version_by_name, passing the component name
            # and component version name pieces.
            result = hub.create_version_reports(version=version, report_list=FILES, format="CSV")
            # Generates reports in subprojects for FILES (source) report,
            # Using the version object (line 21) to say which reports are needed
            # prints out success/error code.
            if result.status_code == 201:
                print("Successfully created reports ({}) for project {} and version {}".format(
                    FILES, args.project_name, args.version_name))
                location = result.headers['Location']
                download_report(location, subname)
            else:
                print("Failed to create reports for project {} version {}, status code returned {}".format(
                args.project_name, args.version_name, result.status_code))
        elif len(component['activityData']) != 0:
            print('is OSS component, no report to download')


def checkdirs():
    if os.path.isdir('./temp') == False:
        os.makedirs('./temp')
        print('made temp directory')
    else:
        print('temp directory already exists')
    if os.path.isdir('./results') == False:
        os.makedirs('./results')
        print('made results directory')
    else:
        print('results directory already exists')


def unzip():
    for filename in os.listdir("."):
        if filename.endswith(".zip"):
            shutil.move(filename, './temp/')
    curdir = (os.getcwd() + './temp/')
    os.chdir(curdir)
    for zipfile in os.listdir(curdir):
        with ZipFile(zipfile, 'r') as zipObj:
            zipObj.extractall()


def concat():
    for csv in glob.iglob('**/*.csv'):
        csv_list.append(csv)
    consolidated = pandas.concat([pandas.read_csv(csv) for csv in csv_list])
    consolidated.to_csv(file_out, index=False, encoding="utf-8")
    shutil.move(file_out, '../results/')
    shutil.rmtree('../temp', ignore_errors=True)


def main():
    checkdirs()
    genreport()
    unzip()
    concat()


main()
