'''
Created on May 28, 2020

bdio_update_project_name  - updates project name referenced in bdio file

@parameters

bdio_in              - original bdio file
--bdio-out  bdio_ot  - output bdio file
--project-name projetc_name  - new Project name

Invoked without --bdio-out and --project-name will read project name referenced in bdio file


@author: kumykov
'''
import errno
import json
import os
import shutil
import sys
import zipfile
from argparse import ArgumentParser
from zipfile import ZIP_DEFLATED
from email.policy import default

bdio_in = '/Users/kumykov/Downloads/e9c96cab-8d7c-3247-ac17-fca205fabd62.bdio'
bdio_out = '/Users/kumykov/Downloads/renamed.bdio'
workdir = 'workdir'
inputdir = 'workdir/input'
outputdir = 'workdir/output'

def zip_extract_files(zip_file, dir_name):
    print("Extracting content of {} into {}".format(zip_file, dir_name))
    with zipfile.ZipFile(zip_file, 'r') as zip_ref:
        zip_ref.extractall(dir_name)

def zip_create_archive(zip_file, dir_name):
    print ("writing content of {} into {} file".format(dir_name, zip_file))
    with zipfile.ZipFile(zip_file, mode='w', compression=ZIP_DEFLATED) as zipObj:
        for folderName, subfolders, filenames in os.walk(dir_name):
            for filename in filenames:
                filePath = os.path.join(folderName, filename)
                zipObj.write(filePath, os.path.basename(filePath))

def read_json_object(filepath):
    with open(os.path.join(workdir,filepath)) as jsonfile:
        data = json.load(jsonfile)
    return data

def write_json_file(filepath, data):
    with open(filepath, "w") as outfile:
        json.dump(data, outfile)

def update_project_name(data, name):
    content_array = data['@graph']

    for counter, array_entry in enumerate(content_array):
        if array_entry['@type'][0] == 'https://blackducksoftware.github.io/bdio#Project':
            #print (counter)
            #print (content_array[counter].keys())
            if "https://blackducksoftware.github.io/bdio#hasName" in content_array[counter]:
                content_array[counter]["https://blackducksoftware.github.io/bdio#hasName"][0]['@value'] = name
            #print (content_array[counter])

def get_project_name(data):
    content_array = data['@graph']
    names = []
    for counter, array_entry in enumerate(content_array):
        if array_entry['@type'][0] == 'https://blackducksoftware.github.io/bdio#Project':
            #print (counter)
            #print (content_array[counter].keys())
            if "https://blackducksoftware.github.io/bdio#hasName" in content_array[counter]:
                names.append(content_array[counter]["https://blackducksoftware.github.io/bdio#hasName"][0]['@value'])
            #print (content_array[counter])
    return names
            
def setup_workspace():
    global workdir
    global inputdir
    global outputdir
    try:
        current_dir = os.getcwd()
        workdir = os.path.join(current_dir, 'workdir')
        inputdir = os.path.join(workdir, "input")
        outputdir = os.path.join(workdir, "output")
        if os.path.exists(inputdir):
            shutil.rmtree(inputdir)
        os.makedirs(inputdir)
        if os.path.exists(outputdir):
            shutil.rmtree(outputdir)
        os.makedirs(outputdir)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise
        
def cleanup_workspace():
    try:
        shutil.rmtree(workdir)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise    

def bdio_read_project_name(bdio_in):
    zip_extract_files(bdio_in, inputdir)
    filelist = os.listdir(inputdir)
    names = []
    for filename in filelist:
        #print ("processing {}".format(filename))
        filepath_in = os.path.join(inputdir, filename)
        data = read_json_object(filepath_in)
        names.extend(get_project_name(data))
    return names

def bdio_update_project_name(bdio_in, bdio_out, new_project_name):
    zip_extract_files(bdio_in, inputdir)
    filelist = os.listdir(inputdir)
    for filename in filelist:
        print ("processing {}".format(filename))
        filepath_in = os.path.join(inputdir, filename)
        filepath_out = os.path.join(outputdir, filename)
        data = read_json_object(filepath_in)
        update_project_name(data,new_project_name)
        write_json_file(filepath_out, data)

    zip_create_archive(bdio_out, outputdir)
    
def main(argv=None):
    
    if argv is None:
        argv = sys.argv
    else:
        sys.argv.extend(argv)

    try:
        # Setup argument parser
        parser = ArgumentParser()
        parser.add_argument("bdio_in", help="Path to the original BDIO file")
        parser.add_argument("--bdio-out", default=None, help="Path to the output file to be written")
        parser.add_argument("--project-name", default=None, help="New project name")

        args = parser.parse_args()
        
        if not args.bdio_in:
            parser.print_help(sys.stdout)
            sys.exit(1)

        if not args.project_name:
            if not args.bdio_out:
                setup_workspace()
                print ("Project names found {}".format(set(bdio_read_project_name(args.bdio_in))))
                cleanup_workspace()
            else:
                parser.print_help(sys.stdout)
                sys.exit(1)
        else:
            if args.bdio_out:
                setup_workspace()
                bdio_update_project_name(args.bdio_in, args.bdio_out, args.project_name)
                cleanup_workspace()
            else:
                parser.print_help(sys.stdout)
                sys.exit(1) 

        return 0
    except Exception as e:
        pass

    
if __name__ == "__main__":
    sys.exit(main())
