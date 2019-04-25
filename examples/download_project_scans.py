#!/usr/local/bin/python2.7
# encoding: utf-8
'''
examples.download_project_scans -- downloads all scans that belong to a project

examples.download_project_scans is a program that will download all scan files that belong to a project. Project is specified by project name and version

It defines classes_and_methods

@author:     kumykov

@copyright:  2019 Synopsys, Inc. All rights reserved.

@license:    Apache 2.0

'''

import sys
import os

from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter

__all__ = []
__version__ = 0.1
__date__ = '2019-04-25'
__updated__ = '2019-04-25'

DEBUG = 1
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
    
def main(argv=None):
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

  Created on %s.
  Copyright 2019 organization_name. All rights reserved.

  Licensed under the Apache License 2.0
  http://www.apache.org/licenses/LICENSE-2.0

  Distributed on an "AS IS" basis without warranties
  or conditions of any kind, either express or implied.

USAGE
''' % (program_shortdesc, str(__date__))

    try:
        # Setup argument parser
        parser = ArgumentParser(description=program_license, formatter_class=RawDescriptionHelpFormatter)
        parser.add_argument("project", help="specify project name")
        parser.add_argument("version", help="specify project version")
        parser.add_argument("-o", "--outputdir", default=None, help="specify output folder")

        # Process arguments
        args = parser.parse_args()

        project = args.project
        version = args.version
        outdir=None
        if args.outputdir:
            outdir = args.outputdir

        from blackduck.HubRestApi import HubInstance
        hub = HubInstance()
        loot = hub.download_project_scans(project, version, outdir)
        print (loot)
        
        

    except KeyboardInterrupt:
        ### handle keyboard interrupt ###
        return 0
    except Exception as e:
        if DEBUG or TESTRUN:
           raise(e)
        indent = len(program_name) * " "
        sys.stderr.write(program_name + ": " + repr(e) + "\n")
        sys.stderr.write(indent + "  for help use --help")
        return 2

if __name__ == "__main__":
    if DEBUG:
        pass
    if TESTRUN:
        import doctest
        doctest.testmod()
    if PROFILE:
        import cProfile
        import pstats
        profile_filename = 'examples.download_project_scans_profile.txt'
        cProfile.run('main()', profile_filename)
        statsfile = open("profile_stats.txt", "w")
        p = pstats.Stats(profile_filename, stream=statsfile)
        p.strip_dirs().sort_stats('cumulative')
        p.print_stats()
        statsfile.close()
        sys.exit(0)
    sys.exit(main())