# Iterate through components within a named project (or all) and named version (or all)
# and refresh the copyrights of each - equivalent to clicking the UI refresh button
# Use --debug for some feedback on progress
# Ian Ashworth, May 2025
#
import http.client
import signal
from sys import api_version
import sys
import csv
import datetime
from blackduck import Client
import argparse
import logging
from pprint import pprint
import array as arr

from urllib3.exceptions import ReadTimeoutError

http.client._MAXHEADERS = 1000

job_status = 0

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] {%(module)s:%(lineno)d} %(levelname)s - %(message)s"
)

# initialise
all_my_comp_data = []
my_statistics = {}


def RepDebug(level, msg):
    if hasattr(args, 'debug') and level <= args.debug:
        print("dbg{" + str(level) + "} " + msg)
        return True
    return False

def RepWarning(msg):
    print("WARNING: " + msg)
    return True

def CompleteTask(job_status):
    now = datetime.datetime.now()
    my_statistics['_jobStatus'] = job_status

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
                    'Status',
                    'Url'
                ]

                writer = csv.DictWriter(csv_f, fieldnames=field_names)
                writer.writeheader()

                for my_comp_data in all_my_comp_data:
                    row_data = {
                        'Component': my_comp_data['componentName'],
                        'Component Version': my_comp_data['componentVersion'],
                        'Status': my_comp_data['status'],
                        'Url': my_comp_data['url']
                    }
                    writer.writerow(row_data)
        else:
            # print to screen
            pprint(all_my_comp_data)

def SignalHandler(sig, frame):
    # Complete the work
    print("Ctrl+C detected!")

    # tidy up and complete the job
    CompleteTask(1)
    sys.exit(job_status)

# ------------------------------------------------------------------------------
# register the signal handler
signal.signal(signal.SIGINT, SignalHandler)


# Parse command line arguments
parser = argparse.ArgumentParser("Refresh copyrights for project/version components")

parser.add_argument("--base-url", required=True, help="BD Hub server URL e.g. https://your.blackduck.url")
parser.add_argument("--token-file", dest='token_file', required=True, help="File containing your access token")

parser.add_argument("--dump-data", dest='dump_data', action='store_true', help="Retain analysed data")
parser.add_argument("--csv-file", dest='csv_file', help="File name for dumped data formatted as CSV")

parser.add_argument("--project", dest='project_name', help="Project name")
parser.add_argument("--version", dest='version_name', help="Version name")

parser.add_argument("--max-projects", dest='max_projects', type=int, help="Maximum number of projects to inspect else all")
parser.add_argument("--max-versions-per-project", dest='max_versions_per_project', type=int, help="Maximum versions per project to inspect else all")
parser.add_argument("--max-components", dest='max_components', type=int, help="Maximum components to inspect in total else all")

parser.add_argument("--skip-projects", dest='skip_projects', type=int, help="Skip first 'n' projects to inspect")

parser.add_argument("--debug", dest='debug', type=int, default=0, help="Debug verbosity (0=none 'n'=level)")
parser.add_argument("--dryrun", dest='dry_run', type=int, default=0, help="Dry run test (0=no 1=yes)")

parser.add_argument("--no-verify", dest='verify', action='store_false', help="Disable TLS certificate verification")
parser.add_argument("--timeout", default=60, type=int, help="Adjust the (HTTP) session timeout value (default: 60s)")
parser.add_argument("--retries", default=3, type=int, help="Adjust the number of retries on failure (default: 3)")

args = parser.parse_args()

# open the access token file
with open(args.token_file, 'r') as tf:
    access_token = tf.readline().strip()

# access the Black Duck platform
bd = Client(
    base_url=args.base_url,
    verify=args.verify,
    token=access_token,
    timeout=args.timeout,
    retries=args.retries,
)


str_unknown = "n/a"

str_unknown = "n/a"

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
my_statistics['_cntOrigins'] = 0

my_statistics['_cntRefresh'] = 0
my_statistics['_cntNoOrigins'] = 0
my_statistics['_cntNoIDs'] = 0
my_statistics['_cntSkippedProjects'] = 0
my_statistics['_jobStatus'] = 0

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


cnt_project = 0
cnt_call = 0

# loop through projects list
for this_project in projects:

    cnt_project += 1

    # check if we are skipping over this project
    if args.skip_projects and cnt_project <= args.skip_projects:
        my_statistics['_cntSkippedProjects'] += 1
        RepDebug(1, 'Skipping project [%d] [%s]' % (cnt_project, this_project['name']))
        continue

    # check if we have hit any limit
    if args.max_components and my_statistics['_cntComponents'] >= args.max_components:
        RepDebug(1, 'Reached component limit [%d]' % args.max_components)
        break

    if args.max_projects and my_statistics['_cntProjects'] >= args.max_projects:
        RepDebug(1, 'Reached project limit [%d]' % args.max_projects)
        break

    # process this project
    my_statistics['_cntProjects'] += 1
    RepDebug(1, '## Project: [%d] [%s]' % (cnt_project, this_project['name']))

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
            RepDebug(1, 'Reached component limit [%d]' % args.max_components)
            break

        if args.max_versions_per_project and nVersionsPerProject >= args.max_versions_per_project:
            RepDebug(1, 'Reached versions per project limit [%d]' % args.max_versions_per_project)
            break

        nVersionsPerProject += 1
        my_statistics['_cntVersions'] += 1

        # Announce
#        logging.debug(f"Found {this_project['name']}:{this_version['versionName']}")
        RepDebug(3, '   Version: [%s]' % this_version['versionName'])


        # iterate through all components for this project version
        for this_comp_data in bd.get_resource('components', this_version, **comp_kwargs):

            if args.max_components and my_statistics['_cntComponents'] >= args.max_components:
                break

            my_statistics['_cntComponents'] += 1

            if this_comp_data.get("componentName"):
                comp_name = this_comp_data['componentName']
            else:
                comp_name = str_unknown

            if this_comp_data.get("componentVersionName"):
                comp_version_name = this_comp_data['componentVersionName']
            else:
                comp_version_name = str_unknown

            comp_label = "{} ({})".format(comp_name, comp_version_name)

            RepDebug(4, '     Component: [%s]' % comp_label)

            if this_comp_data['inputExternalIds'].__len__() > 0:
                inputExternalIds = this_comp_data['inputExternalIds'][0]
            else:
                my_statistics['_cntNoIDs'] += 1
                inputExternalIds = str_unknown
            RepDebug(2, '       ID: [%s]' % inputExternalIds)


            # refresh the copyrights for this component-origin
            if this_comp_data['origins'].__len__() > 0:

                n_origin = 0

                for this_origin in this_comp_data['origins']:

                    n_origin += 1
                    my_statistics['_cntOrigins'] += 1

                    if this_origin.get('externalId'):
                        origin_id = this_origin['externalId']
                    else:
                        origin_id = str_unknown

                    url = this_origin['origin']

                    # refresh with end point
                    url += "/copyrights-refresh"

                    status = -1
                    cnt_call += 1
                    call_id = "{}.{}".format(cnt_project, cnt_call)

                    if args.dry_run != 0:
                        RepDebug(2, '         DryRun: %s - origin - no [%d]  id [%s]  url [%s]' % (call_id, n_origin, origin_id, url))
                    else:
                        RepDebug(3,
                                 '       Origin: %s - origin - no [%d]  id [%s]  url [%s]' % (call_id, n_origin, origin_id, url))
                        try:
                            response = bd.session.put(url, data=None, **refresh_kwargs)
                            RepDebug(5,'Refresh response: origin [%s] [%s]' % (this_origin, response))
                            my_statistics['_cntRefresh'] += 1
                            status= 0

                        except Exception:
                            print('Failed to confirm copyrights refresh')
                            status = 1


                    # if recording the data - perhaps outputting to a CSV file
                    if args.dump_data:
                        my_data = {}
                        my_data['componentName'] = this_comp_data['componentName']
                        my_data['componentVersion'] = this_comp_data['componentVersionName']
                        my_data['status'] = status
                        my_data['url'] = url

                        if hasattr(args, 'debug') and 5 <= args.debug:
                            pprint(my_data)

                        # add to our list
                        all_my_comp_data.append(my_data)

            else:
                # no origins defined
                RepWarning('No origin(s) defined for [%s]' % comp_label)
                my_statistics['_cntNoOrigins'] += 1
                origin_id = ''
                status = 3
                url = 'n/a'

                # if recording the data
                if args.dump_data:
                    my_data = {}
                    my_data['componentName'] = comp_name
                    my_data['componentVersion'] = comp_version_name
                    my_data['status'] = status
                    my_data['url'] = url

                    if hasattr(args, 'debug') and 5 <= args.debug:
                        pprint(my_data)

                    # add to our list
                    all_my_comp_data.append(my_data)

# end of processing loop

CompleteTask(0)
#end
