#!/usr/local/bin/python3
# encoding: utf-8
'''
examples.custom_signatures_export -- Exports project scan data for projects that have custom signatures enabled

examples.custom_signatures_export 

Exports scans for all projects that have custom signature enabled
All scans will be placed in the output directory.
A metadata file will be written to specify project names and versions.
Metadata will be used to identify projects that will require custom signature flag enabled

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
    
'''
'''
    
def get_custom_signatures(hub):
    projects=hub.get_projects()
    custom_signatures=list()
    for project in projects['items']:
        if project["customSignatureEnabled"]:
            custom_signatures.append(project)
    return custom_signatures
    
def download_project_scans(project):
    pass

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
        parser.add_argument(dest="output_path", help="path to folder to store exported data")

        # Process arguments
        args = parser.parse_args()

        output_path = args.output_path

        ## Do shit
        # print (output_path)
        # print (args)
        
        workdir = os.path.abspath(output_path)
        
        print(workdir)
        
        hub=HubInstance()
                
        projects = get_custom_signatures(hub)
        
        metadata = {"magic": "CSMD001", "content": {}}
        metadata_path = os.path.join(workdir, "metadata.json")
        
        for project in projects:
            project_name = project['name']
            versions = hub.get_project_versions(project)
            version_metadata = []
            metadata['content'][project_name] = version_metadata
            for version in versions['items']:
                version_name = version['versionName']
                version_metadata.append(version_name)
                codelocations = hub.get_version_codelocations(version)
                for codelocation in codelocations['items']:
                    #print(json.dumps(codelocation,indent=2))
                    scanurl=codelocation['_meta']['href'].replace('codelocations','scan/data') + ".bdio"
                    print (scanurl)
                    filename = scanurl.split('/')[6]
                    if not os.path.exists(workdir):
                        os.mkdir(workdir)
                    pathname = os.path.join(workdir, filename)
                    responce = hub.execute_get(scanurl, custom_headers=hub.get_headers())
                    with open(pathname, "wb") as f:
                        for data in responce.iter_content():
                            f.write(data)
                    print("File {} written".format(pathname))
                
        # print(json.dumps(get_custom_signatures(hub),indent=2))
        
        print("Writing metadata file")
        with open(metadata_path, 'w') as outfile:
            json.dump(metadata, outfile)
        print("Done.")
        
        ### handle keyboard interrupt ###
        return 0
    except Exception as e:
        import traceback
        traceback.print_exc()
        if DEBUG or TESTRUN:
            raise(e)
        indent = len(program_name) * " "
        sys.stderr.write(program_name + ": " + repr(e) + "\n")
        sys.stderr.write(indent + "  for help use --help")
        return 2

if __name__ == "__main__":
    if DEBUG:
        sys.argv.append("-h")
        sys.argv.append("-v")
    if TESTRUN:
        import doctest
        doctest.testmod()
    if PROFILE:
        import cProfile
        import pstats
        profile_filename = 'examples.custom_signatures_export_profile.txt'
        cProfile.run('main()', profile_filename)
        statsfile = open("profile_stats.txt", "wb")
        p = pstats.Stats(profile_filename, stream=statsfile)
        stats = p.strip_dirs().sort_stats('cumulative')
        stats.print_stats()
        statsfile.close()
        sys.exit(0)
    sys.exit(main())
