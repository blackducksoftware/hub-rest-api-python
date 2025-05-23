# Iterate through components within a named project (or all) and named version (or all)
# and refresh the copyrights of each - equivalent to clicking the UI refresh button
# Use --debug for some feedback on progress
# Ian Ashworth, May 2025
#
import http.client
from sys import api_version
import sys
import csv
import datetime
from blackduck import Client
import argparse
import logging
from pprint import pprint
import array as arr

http.client._MAXHEADERS = 1000

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] {%(module)s:%(lineno)d} %(levelname)s - %(message)s"
)

def RepDebug(level, msg):
    if hasattr(args, 'debug') and level <= args.debug:
        print("dbg{" + str(level) + "} " + msg)
        return True
    return False

def RepWarning(msg):
    print("WARNING: " + msg)
    return True


# Parse command line arguments
parser = argparse.ArgumentParser("Refresh copyrights for project/version components")

parser.add_argument("--base-url", required=True, help="BD Hub server URL e.g. https://your.blackduck.url")
parser.add_argument("--token-file", dest='token_file', required=True, help="File containing your access token")

parser.add_argument("--dump-data", dest='dump_data', action='store_true', help="Retain analysed data")
parser.add_argument("--csv-file", dest='csv_file', help="File name for dumped data formatted as CSV")

parser.add_argument("--project", dest='project_name', help="Project name")
parser.add_argument("--version", dest='version_name', help="Version name")

parser.add_argument("--max-projects", dest='max_projects', type=int, help="Maximum projects to inspect else all")
parser.add_argument("--max-versions-per-project", dest='max_versions_per_project', type=int, help="Maximum versions per project to inspect else all")
parser.add_argument("--max-components", dest='max_components', type=int, help="Maximum components to inspect in total else all")

parser.add_argument("--debug", dest='debug', type=int, default=0, help="Debug verbosity (0=none 'n'=level)")
parser.add_argument("--dryrun", dest='dry_run', type=int, default=0, help="Dry run test (0=no 1=yes)")

parser.add_argument("--no-verify", dest='verify', action='store_false', help="Disable TLS certificate verification")
parser.add_argument("-t", "--timeout", default=15, type=int, help="Adjust the (HTTP) session timeout value (default: 15s)")
parser.add_argument("-r", "--retries", default=3, type=int, help="Adjust the number of retries on failure (default: 3)")

args = parser.parse_args()

# open the access token file
with open(args.token_file, 'r') as tf:
    access_token = tf.readline().strip()

# access the Black Duck platform
bd = Client(
    base_url=args.base_url,
    token=access_token,
    verify=args.verify,
    timeout=args.timeout,
    retries=args.retries,
)

# initialise
all_my_comp_data = []
my_statistics = {}


# version of components API to call
comp_api_version = 6

comp_accept_version = "application/vnd.blackducksoftware.bill-of-materials-" + str(comp_api_version) + "+json"
#comp_accept_version = "application/json"

comp_content_type = comp_accept_version

# header keys
comp_lc_keys = {}
comp_lc_keys['accept'] = comp_accept_version
comp_lc_keys['content-type'] = comp_accept_version

# keyword arguments to pass to API call
comp_kwargs={}
comp_kwargs['headers'] = comp_lc_keys


# version of API to call
refresh_api_version = 4

refresh_accept_version = "application/vnd.blackducksoftware.copyright-" + str(refresh_api_version) + "+json"
#refresh_accept_version = "application/json"

refresh_content_type = refresh_accept_version


# header keys
refresh_lc_keys = {}
refresh_lc_keys['accept'] = refresh_accept_version
refresh_lc_keys['content-type'] = refresh_accept_version

# keyword arguments to pass to API call
refresh_kwargs={}
refresh_kwargs['headers'] = refresh_lc_keys


# zero our main counters
my_statistics['_cntProjects'] = 0
my_statistics['_cntVersions'] = 0
my_statistics['_cntComponents'] = 0
my_statistics['_cntRefresh'] = 0
my_statistics['_cntNoOrigins'] = 0
my_statistics['_cntNoIDs'] = 0


# record any control values
if args.project_name:
    my_statistics['_namedProject'] = args.project_name
if args.version_name:
    my_statistics['_namedVersion'] = args.version_name

if args.max_projects:
    my_statistics['_maxProjects'] = args.max_projects
if args.max_versions_per_project:
    my_statistics['_maxVersionsPerProject'] = args.max_versions_per_project
if args.max_components:
    my_statistics['_maxComponents'] = args.max_components

now = datetime.datetime.now()
print('Started:  %s' % now.strftime("%Y-%m-%d %H:%M:%S"))

# check named project of specific interest
if args.project_name:
    params = {
        'q': [f"name:{args.project_name}"]
    }
    projects = [p for p in bd.get_resource('projects', params=params) if p['name'] == args.project_name]

    # must exist
    assert len(projects) > 0, f"There should be at least one - {len(projects)} project(s) noted"
else:
    # all projects are in scope
    projects = bd.get_resource('projects')

# loop through projects list
for this_project in projects:

    # check if we have hit any limit
    if args.max_components and my_statistics['_cntComponents'] >= args.max_components:
        break

    if args.max_projects and my_statistics['_cntProjects'] >= args.max_projects:
        break

    my_statistics['_cntProjects'] += 1
    RepDebug(1, '## Project %d: %s' % (my_statistics['_cntProjects'], this_project['name']))

    if args.version_name:
        # note the specific project version of interest
        params = {
            'q': [f"versionName:{args.version_name}"]
        }
        versions = [v for v in bd.get_resource('versions', this_project, params=params) if v['versionName'] == args.version_name]

        # it must exist
        assert len(versions) > 0, f"There should be at least one - {len(versions)} version(s) noted"
    else:
        # all versions for this project are in scope
        versions = bd.get_resource('versions', this_project)

    nVersionsPerProject = 0

    for this_version in versions:

        # check if we have hit any limit
        if args.max_components and my_statistics['_cntComponents'] >= args.max_components:
            # exit component loop - at the limit
            break

        if args.max_versions_per_project and nVersionsPerProject >= args.max_versions_per_project:
            # exit loop - at the version per project limit
            break

        nVersionsPerProject += 1
        my_statistics['_cntVersions'] += 1

        # Announce
#        logging.debug(f"Found {this_project['name']}:{this_version['versionName']}")
        RepDebug(3, '   Version: %s' % this_version['versionName'])


        # iterate through all components for this project version
        for this_comp_data in bd.get_resource('components', this_version, **comp_kwargs):

            if args.max_components and my_statistics['_cntComponents'] >= args.max_components:
                # exit component loop - at the limit
                break

            my_statistics['_cntComponents'] += 1
            RepDebug(4, '     Component: %s (%s)' %
                     (this_comp_data['componentName'], this_comp_data['componentVersionName']))

            if this_comp_data['inputExternalIds'].__len__() > 0:
                inputExternalIds = this_comp_data['inputExternalIds'][0]
            else:
                my_statistics['_cntNoIDs'] += 1
                inputExternalIds = "n/a"
            RepDebug(2, '       ID: %s' % inputExternalIds)


            # refresh the copyrights for this component
            if this_comp_data['origins'].__len__() > 0:
                url = this_comp_data['origins'][0]['origin']
            else:
                # no origins
                RepWarning('No origin defined for [%s]' % this_comp_data['componentVersion'])
#                url = this_comp_data['componentVersion']
                url = ''

            if len(url) > 0:
                # refresh end point
                url += "/copyrights-refresh"

                if args.dry_run != 0:
                    RepDebug(1, "DryRun: %s" % url)
                else:
                    try:
                        response = bd.session.put(url, data=None, **refresh_kwargs)
                        RepDebug(5,'Refresh response %s' % response)
                    except ReadTimeoutError:
                        print('Failed to confirm copyrights refresh')

                    my_statistics['_cntRefresh'] += 1

            else:
                my_statistics['_cntNoOrigins'] += 1
                url = 'n/a'


            # if recording the data - perhaps outputting to a CSV file
            if args.dump_data:
                my_data = {}
                my_data['componentName'] = this_comp_data['componentName']
                my_data['componentVersion'] = this_comp_data['componentVersionName']
                my_data['url'] = url

                if hasattr(args, 'debug') and 5 <= args.debug:
                    pprint(my_data)

                # add to our list
                all_my_comp_data.append(my_data)


# end of processing loop

now = datetime.datetime.now()
print('Finished: %s' % now.strftime("%Y-%m-%d %H:%M:%S"))
print('Summary:')
pprint(my_statistics)

# if dumping data
if args.dump_data:
    # if outputting to a CSV file
    if args.csv_file:
        '''Note: See the BD API doc and in particular .../api-doc/public.html#_bom_vulnerability_endpoints
            for a complete list of the fields available. The below code shows a subset of them just to
            illustrate how to write out the data into a CSV format.
        '''
        logging.info(f"Exporting {len(all_my_comp_data)} records to CSV file {args.csv_file}")

        with open(args.csv_file, 'w') as csv_f:
            field_names = [
                'Component',
                'Component Version',
                'Url'
            ]

            writer = csv.DictWriter(csv_f, fieldnames=field_names)
            writer.writeheader()

            for my_comp_data in all_my_comp_data:
                row_data = {
                    'Component': my_comp_data['componentName'],
                    'Component Version': my_comp_data['componentVersion'],
                    'Url': my_comp_data['url']
                }
                writer.writerow(row_data)
    else:
        # print to screen
        pprint(all_my_comp_data)

#end
