#!/usr/local/bin/python3
# encoding: utf-8
'''
examples.custom_signatures_import -- imports scan data for custom signatures

examples.custom_signatures_import 

Used output of custom_signature_export 
It will create project structure according to the metadata.json file
and enable custom signature flags for each project created

Then it will upload all scan files to Blackduck instnce.
Once scan files are processed, custom signatures will be ready to use.

@author:     kumykov

@copyright:  2020 Synopsys Inc. All rights reserved.

@license:    Apache License 2.0

@contact:    kumykov@synopsys.com
@deffield    updated: Updated
'''

import sys
import os

from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter
from blackduck.HubRestApi import HubInstance
import json

__all__ = []
__version__ = 0.1
__date__ = '2020-05-05'
__updated__ = '2020-05-05'

DEBUG = 0
TESTRUN = 0
PROFILE = 0

class CLIError(Exception):
    '''Generic exception to raise and log different fatal errors.'''
    def __init__(self, msg):
        super(CLIError).__init__(type(self))
        self.msg = "E: %s" % msg
    def __str__(self):
        return self.msg
    def __unicode__(self):
        return self.msg
    
def read_metadata_file(metadata_path):
    with open(metadata_path) as json_file:
        data = json.load(json_file)
    if data['magic'] == "CSMD001":
        return data
    else:
        raise Exception ("Bad metadata.")
    
def create_projects(hub, metadata):
    for project_name in metadata['content']:
        for version_name in metadata['content'][project_name]:
            try:
                version = hub.get_or_create_project_version(project_name, version_name)
            except:
                print ("Failed to create project {} version {}".format(project_name, version_name))
        try:
            project = hub.get_project_by_name(project_name)
            if not project['customSignatureEnabled']:
                print ("Enabling custom signature for {}".format(project['name']))
                project['customSignatureEnabled'] = True
                response = hub.update_project_settings(project, new_settings=project)
                print (response)
            else:
                print ("Custom signature for {} already enabled".format(project_name))
        except:
            print ("Failed to set custom signature flag for {}".format(project_name))

def upload_scan_data(hub, workdir):
    for entry in os.scandir(workdir):
        pathname = entry.path
        if pathname.endswith('.bdio'):
            print("Uploading {}".format(pathname), end = ". ")
            response = hub.upload_scan(pathname)
            print ("Response {}".format(response))

def main(argv=None): # IGNORE:C0111
    '''Command line options.'''

    if argv is None:
        argv = sys.argv
    else:
        sys.argv.extend(argv)

    program_name = os.path.basename(sys.argv[0])
    program_version = "v%s" % __version__
    program_build_date = str(__updated__)
    program_version_message = '%%(prog)s %s (%s)' % (program_version, program_build_date)
    program_shortdesc = __import__('__main__').__doc__.split("\n")[1]
    program_license = '''%s

  Created by user_name on %s.
  Copyright 2020 organization_name. All rights reserved.

  Licensed under the Apache License 2.0
  http://www.apache.org/licenses/LICENSE-2.0

  Distributed on an "AS IS" basis without warranties
  or conditions of any kind, either express or implied.

USAGE
''' % (program_shortdesc, str(__date__))

    try:
        # Setup argument parser
        parser = ArgumentParser(description=program_license, formatter_class=RawDescriptionHelpFormatter)
        parser.add_argument(dest="input_path", help="path to folder to store exported data")

        # Process arguments
        args = parser.parse_args()

        input_path = args.input_path

        workdir = os.path.abspath(input_path)
        metadata_path = os.path.join(workdir, "metadata.json")
        print("Reading metadata from {} ".format(metadata_path))
        metadata = read_metadata_file(metadata_path)
        
        hub=HubInstance()
        
        create_projects(hub, metadata)
        
        upload_scan_data(hub, workdir)
                

        return 0
    except Exception as e:
        import traceback
        traceback.print_stack()
        if DEBUG or TESTRUN:
            raise(e)
        indent = len(program_name) * " "
        sys.stderr.write(program_name + ": " + repr(e) + "\n")
        sys.stderr.write(indent + "  for help use --help")
        return 2

if __name__ == "__main__":
    if DEBUG:
        sys.argv.append("-v")
        sys.argv.append("-h")
    if TESTRUN:
        import doctest
        doctest.testmod()
    if PROFILE:
        import cProfile
        import pstats
        profile_filename = 'examples.custom_signatures_import_profile.txt'
        cProfile.run('main()', profile_filename)
        statsfile = open("profile_stats.txt", "wb")
        p = pstats.Stats(profile_filename, stream=statsfile)
        stats = p.strip_dirs().sort_stats('cumulative')
        stats.print_stats()
        statsfile.close()
        sys.exit(0)
    sys.exit(main())
