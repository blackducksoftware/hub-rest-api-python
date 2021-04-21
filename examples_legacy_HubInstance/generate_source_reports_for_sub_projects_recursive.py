"""
generate_source_report_for_sub_projects_recursive

Created on February 15, 2021

Adapted from generate_source_report_for_sub_projects.py written by AMacDonald

@author: DNicholls

Script designed to generate and collate Source reports for the master project and it's sub-projects recursively. 

If a project has source but also sub projects with source that also have sub projects with source this utility will
generate source reports for each level of project and combine to a consolidated source report.  It will also generate
security and components reports for the master project (these automatically include subprojects).  It will output the 
results to a ./results folder and uses ./temp for work in progress.  These can be modified in the below checkdirs, unzip
and concat functions.  If you are finding the reports are not generated in time by default it will wait 5 seconds and 
retry 10 times, if this is not long enough as your projects are large then increase the retries_per_download variable.

To run this script, you will need to pass arguments for the master project name and the master project version.  Once
they are specified, the script will investigate to see if the master project contains sub-projects and will generate
reports for all sub-projects it discovers. Finally, it will combine them into a single report, saving it to a "results"
sub-directory.

For this script to run, the hub-rest-api-python (blackduck) library and pandas library will need to be installed.

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
csv_list = []
timestamp = time.strftime('%m_%d_%Y_%H_%M')
retries_per_download=10
file_out = (args.project_name + '_' + "Consolidated_src_report-" + timestamp)
file_out = (file_out + ".csv")


class FailedReportDownload(Exception):
    pass


def download_report(location, filename, retries=retries_per_download):
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

def genreportsforversion(projectname,versionname,reportlist):
    print("Generating source report for project {} version {}".format(projectname, versionname))

    projversion = hub.get_project_version_by_name(projectname, versionname)
    components = hub.get_version_components(projversion)

    subname = (projectname + '_' + versionname + '.zip')

    # Generates reports in the main project for SECURITY, COMPONENTS and FILES (source) report and just FILES for subprojects.
    result = hub.create_version_reports(version=projversion, report_list=reportlist, format="CSV")
    
    # prints out success/error code.
    if result.status_code == 201:
        print("Successfully created reports ({}) for project {} and version {}".format(
            reportlist, projectname, versionname))
        location = result.headers['Location']
        download_report(location, subname)
    else:
        print("Failed to create reports for project {} version {}, status code returned {}".format(
        projectname, versionname, result.status_code))

    for component in components['items']:
        # NOTE THIS REQUIRES pip blackduck 0.0.56 to have the correct request header to obtain the componentType attribute.
        if component['componentType'] == 'SUB_PROJECT':
            print("is subproject, {} version {}".format(component['componentName'],component['componentVersionName']))
            genreportsforversion(component['componentName'],component['componentVersionName'],reportlist=['FILES'])
        else:
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
    for csv in glob.iglob('**/source*.csv'):
        csv_list.append(csv)
    consolidated = pandas.concat([pandas.read_csv(csv) for csv in csv_list])
    consolidated.to_csv(file_out, index=False, encoding="utf-8")
    shutil.move(file_out, '../results/')

    for csv in glob.iglob('**/components*.csv'):
        shutil.move(csv, '../results/')
    for csv in glob.iglob('**/security*.csv'):
        shutil.move(csv, '../results/')

    # If you do not want the original source reports for each project exclude this loop.
    #for csv in glob.iglob('**/source*.csv'):
    #    shutil.move(csv, '../results/')

    # Clean up after    
    shutil.rmtree('../temp', ignore_errors=True)


def main():
    checkdirs()
    genreportsforversion(args.project_name, args.version_name,reportlist=['FILES','COMPONENTS','SECURITY'])
    unzip()
    concat()


main()
