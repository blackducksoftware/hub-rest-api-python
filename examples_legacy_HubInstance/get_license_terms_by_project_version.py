import argparse
import csv
import glob
import logging
import os
import shutil
import requests
import sys
import time
import timeit

import pandas
from pandas.errors import EmptyDataError

from blackduck.HubRestApi import HubInstance

parser = argparse.ArgumentParser("A program that pulls license terms (including FulfillmentRequired and Fulfilled) for each of the licenses attached to each of the "
                                 "components in a specified project version ")
parser.add_argument("project")
parser.add_argument("version")
parser.add_argument('-r', '--refresh', action='store_true',
                    help='delete existing reports in the results directory and regenerate')
parser.add_argument('-v', '--verbose', action='store_true', default=False, help='turn on DEBUG logging')

args = parser.parse_args()


def set_logging_level(log_level):
    logging.basicConfig(stream=sys.stderr, level=log_level)


if args.verbose:
    set_logging_level(logging.DEBUG)
else:
    set_logging_level(logging.INFO)

projname = args.project
timestamp = time.strftime('%m_%d_%Y_%H_%M')
file_out = (projname + '_' + "Consolidated_license_report-" + timestamp)
file_out = (file_out + ".csv")
hub = HubInstance()
rootDir = os.getcwd()


def do_refresh(dir_name):
    temp_dir = os.path.join(rootDir, dir_name)
    print("tempDir=%s" % temp_dir)
    for fileName in os.listdir(temp_dir):
        print("Removing stale files %s" % fileName)
        os.remove(os.path.join(temp_dir, fileName))


def check_dirs():
    os.chdir(rootDir)
    if not os.path.isdir('./temp'):
        os.makedirs('./temp')
        print('made temp directory')
    elif len(os.listdir('./temp')) != 0:
        do_refresh('temp')
    else:
        print('temp directory already exists')

    if not os.path.isdir('./license_terms_results'):
        os.makedirs('./license_terms_results')
        print('made license_terms_results directory')
    elif args.refresh and len(os.listdir('./license_terms_results')) != 0:
        print('refreshing license_terms_results')
        do_refresh('license_terms_results')
    else:
        print('license_terms_results directory already exists')


def get_header():
    return ["Component Name", "Component Version", "Name", "Description", "Responsibility",
            "Deactivated", "Deprecated", "FulfillmentRequired", "Fulfilled"]


def get_license_terms(component_licenses):
    license_terms_json = []
    try:
        license_name_key = [*component_licenses.keys()][0]
        license_terms_links = [cl for cl in component_licenses[license_name_key]['license_info']['_meta']['links']
                               if cl.get("rel") == "bom-component-license-terms"]
        url = license_terms_links[0]['href']
    except (KeyError, IndexError) as err:
        logging.debug("no license name for:{}, with {}, writing an empty field ".format(component_licenses, err))
        return license_terms_json
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,'
                  'application/signed-exchange;v=b3;q=0.9'}
    response = hub.execute_get(url, custom_headers=headers)
    try:
        if response.status_code in [200, 201]:
            license_terms_json = response.json()
        else:
            response.raise_for_status()
        return license_terms_json
    except requests.exceptions.HTTPError as err:
        logging.debug("no license terms for:{}, with {}, writing an empty field ".format(license_name_key, err))
    return license_terms_json


def genreport():
    project = hub.get_project_by_name(args.project)
    version = hub.get_version_by_name(project, args.version)
    bom_components = hub.get_version_components(version)
    print("Component count returned for {} {} = {} ".format(args.project, args.version,
                                                            bom_components['totalCount']))
    all_licenses = dict()
    curdir = os.getcwd()
    tempdir = os.path.join(curdir, 'temp')
    os.chdir(tempdir)
    with open(file_out, 'a', newline='') as f:
        writer = csv.writer(f)
        first_file = True
        for bom_component in bom_components['items']:
            # Retrieve the licenses and license text for this bom component and insert the license info along with
            # the bom component info into the all_licenses dictionary
            component_licenses = hub.get_license_info_for_bom_component(bom_component)
            component_name = bom_component['componentName']
            component_version_name = bom_component['componentVersionName']
            name_version_key = "{}, {}".format(component_name, component_version_name)
            license_terms = get_license_terms(component_licenses)

            all_licenses.update({name_version_key: {
                "component_info": bom_component,
                "component_licenses": component_licenses,
                "license_terms": license_terms
            }
            })
            if first_file:
                header = get_header()
                writer.writerow(header)
                first_file = False

            for lt in all_licenses[name_version_key]['license_terms']:
                row_list = [component_name, component_version_name, lt['name'], lt['description'], lt['responsibility'],
                            lt['deactivated'], lt['deprecated'], lt['fulfillmentRequired'], lt['fulfilled']]
                writer.writerow(row_list)


def concat():
    curdir = os.getcwd()
    os.chdir(curdir)
    all_csvs = glob.glob(os.path.join(curdir, '*.csv'))
    all_data_frames = []
    for a_csv in all_csvs:
        try:
            data_frame = pandas.read_csv(a_csv, index_col=None)
        except EmptyDataError:
            data_frame = pandas.DataFrame()

        all_data_frames.append(data_frame)
    data_frame_concat = pandas.concat(all_data_frames, axis=0, ignore_index=True)
    data_frame_concat.to_csv(file_out, index=False)
    shutil.move(file_out, '../license_terms_results/')
    shutil.rmtree('../temp', ignore_errors=True)


def main():
    check_dirs()
    start = timeit.default_timer()
    genreport()
    print("Time spent generating license report: {} seconds".format(int(timeit.default_timer() - start)))
    concat()


main()
