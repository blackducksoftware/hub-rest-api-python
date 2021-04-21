import argparse
import json
import os
import shutil
import sys
import logging
import zipfile
import uuid
from zipfile import ZIP_DEFLATED
from urllib.parse import quote

parser = argparse.ArgumentParser("Take a directory of bdio files, copy and unzip each file,"
                                 "update the project and project version name to the name specified by the user,"
                                 "zip each jsonld file into a bdio of the same name as the source bdio. ")
parser.add_argument('-d', '--bdio-directory', required=True, help="Directory path containing source bdio files")
parser.add_argument('-n', '--project-name', required=True, default=None, help="Project name")
parser.add_argument('-p', '--project-version', required=True, default=None, help="Target project version name")
parser.add_argument('-v', '--verbose', action='store_true', default=False, help='turn on DEBUG logging')

args = parser.parse_args()


def set_logging_level(log_level):
    logging.basicConfig(stream=sys.stderr, level=log_level)


if args.verbose:
    set_logging_level(logging.DEBUG)
else:
    set_logging_level(logging.INFO)

# examples
working_dir = os.getcwd()
bdio_dir = os.path.join(working_dir, args.bdio_directory)
project_name = args.project_name
target_version = args.project_version
temp_dir = os.path.join(working_dir, 'temp')
renamed_directory = os.path.join(bdio_dir, "renamed_bdio")


def do_refresh(dir_name):
    dir = os.path.join(working_dir, dir_name)
    for fileName in os.listdir(dir):
        print("Removing stale files {}".format(os.path.join(dir, fileName)))
        os.remove(os.path.join(dir, fileName))


def check_dirs():
    os.chdir(working_dir)
    if not os.path.isdir('{}'.format(bdio_dir)) or len(os.listdir('{}'.format(bdio_dir))) <= 0:
        parser.print_help(sys.stdout)
        sys.exit(1)

    if not os.path.isdir(temp_dir):
        os.makedirs(temp_dir)
        print('Made temp directory')
    elif len(os.listdir(temp_dir)) != 0:
        do_refresh(temp_dir)
        pass
    else:
        print('Temp directory already exists')

    if not os.path.isdir(renamed_directory):
        os.makedirs(renamed_directory)
        print('Made renamed bdio directory')
    elif len(os.listdir(renamed_directory)) != 0:
        do_refresh(renamed_directory)
    else:
        print('Renamed bdio directory already exists')


def zip_extract_files(zip_file, dir_name):
    print("Extracting content of {} into {}".format(zip_file, dir_name))
    with zipfile.ZipFile(zip_file, 'r') as zip_ref:
        zip_ref.extractall(dir_name)


def zip_create_archive(zip_file, dir_name):
    print("Writing content of {} into {} file".format(dir_name, zip_file))
    with zipfile.ZipFile(zip_file, mode='a', compression=ZIP_DEFLATED) as zipObj:
        for folderName, subfolders, filenames in os.walk(dir_name):
            jsonld_list = [x for x in filenames if x.endswith('.jsonld')]
            for filename in jsonld_list:
                filePath = os.path.join(folderName, filename)
                zipObj.write(filePath, os.path.basename(filePath))


def jsonld_update_project_name(data, name):
    content_array = data['@graph']
    if not content_array:
        return
    for counter, array_entry in enumerate(content_array):
        if array_entry['@type'][0] == 'https://blackducksoftware.github.io/bdio#Project':
            logging.debug(counter)
            logging.debug(content_array[counter].keys())
            if "https://blackducksoftware.github.io/bdio#hasName" in content_array[counter]:
                content_array[counter]["https://blackducksoftware.github.io/bdio#hasName"][0]['@value'] = name
                logging.debug(content_array[counter])


def jsonld_update_uuid(data, new_uuid):
    logging.debug("Updating jsonld file to new UUID: {}".format(new_uuid))
    data.update({'@id': new_uuid})


def jsonld_update_version_name_in_header(data, version):
    scan_name_dict = {k: v[0].get('@value') for (k, v) in data.items() if
                      k == 'https://blackducksoftware.github.io/bdio#hasName'}
    if not scan_name_dict:
        return
    try:
        version_link = scan_name_dict.popitem()[1].split('/')
        version_link[1] = version
    except IndexError as index_error:
        logging.debug("Could not get version link for this header file {} with error {}, header files are not "
                      "required for upload".format(scan_name_dict, index_error))
        return
    else:
        version_list = [{'@value': '/'.join(version_link)}]
        data.update({'https://blackducksoftware.github.io/bdio#hasName': version_list})


def jsonld_update_project_version(data, version):
    content_array = data['@graph']
    if not content_array:
        return
    for counter, array_entry in enumerate(content_array):
        if array_entry['@type'][0] == 'https://blackducksoftware.github.io/bdio#Project':
            logging.debug(counter)
            logging.debug(content_array[counter].keys())
            if "https://blackducksoftware.github.io/bdio#hasVersion" in content_array[counter]:
                content_array[counter]["https://blackducksoftware.github.io/bdio#hasVersion"][0]['@value'] = version
                logging.debug(content_array[counter])


def read_json_object(filepath):
    with open(os.path.join(temp_dir, filepath)) as jsonfile:
        data = json.load(jsonfile)
    return data


def write_json_file(filepath, data):
    with open(filepath, "w") as outfile:
        json.dump(data, outfile)


# copy .bdio file to temp directory
# unzip it
# change the project version in jsonld file
# zip files back in to a bdio file of the same name
# copy from temp in to a directory named "renamed-bdios"
# do the next bdio file
# delete the contents of the temp directory
def bdio_update_project_version():
    file_list = [x for x in os.listdir(bdio_dir) if x.endswith('.bdio')]
    for file in file_list:
        zip_extract_files(os.path.join(bdio_dir, file), temp_dir)
        os.chdir(temp_dir)
        output_bdio = os.path.join(temp_dir, file)
        jsonld_files = [y for y in os.listdir(temp_dir) if y.endswith('.jsonld')]
        new_uuid = uuid.uuid1()
        for jsonld_file in jsonld_files:
            jsonld_path = os.path.join(temp_dir, jsonld_file)
            data = read_json_object(jsonld_path)
            jsonld_update_project_name(data, project_name)
            jsonld_update_uuid(data, "urn:uuid:{}".format(new_uuid))
            if jsonld_file.split('-')[1] == 'header.jsonld':
                jsonld_update_version_name_in_header(data, target_version)
            else:
                jsonld_update_project_version(data, target_version)
            write_json_file(jsonld_path, data)
        zip_create_archive(output_bdio, temp_dir)
        shutil.copy(output_bdio, renamed_directory)
    print('Cleaning up temp directory ')
    do_refresh('temp')
    os.chdir(working_dir)
    shutil.rmtree('temp')


def main():
    check_dirs()
    bdio_update_project_version()


main()
