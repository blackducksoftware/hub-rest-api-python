'''
Purpose: Deactivates Deep Licenses that were detected by Deep License search

usage: deactivate_deep_licenses.py [-h] -u BASE_URL -t TOKEN_FILE -p PROJECT_NAME -pv VERSION_NAME [-mt MATCH_TYPE] [-nv] [--active]

options:
  -h, --help            show this help message and exit
  -u BASE_URL, --base-url BASE_URL
                        Hub server URL e.g. https://your.blackduck.url
  -t TOKEN_FILE, --token-file TOKEN_FILE
                        File containing access token
  -p PROJECT_NAME, --project-name PROJECT_NAME
                        Project Name
  -pv VERSION_NAME, --version-name VERSION_NAME
                        Project Version Name
  -mt MATCH_TYPE, --match-type MATCH_TYPE
                        Limit the action to components with specific Match Type 
  -nv, --no-verify      Disable TLS certificate verification
  --active              Status to set deep license to


'''

from blackduck import Client
import logging
import argparse
import sys

from pprint import pprint

logging.basicConfig(
    level=logging.DEBUG,
    format="[%(asctime)s] {%(module)s:%(lineno)d} %(levelname)s - %(message)s"
)

def set_active(bd, licenses, status=False):
    for license in licenses:
        license['active'] = status
    headers = {'Content-Type': 'application/vnd.blackducksoftware.internal-1+json'}
    url = license['_meta']['href']
    dld_url = url[:url.index('deep-license-data')+len('deep-license-data')]
    response = bd.session.put(dld_url, headers=headers, json=licenses)    
    return response

def parse_command_args():

    parser = argparse.ArgumentParser("deactivate_deep_licenses.py")
    parser.add_argument("-u", "--base-url",     required=True, help="Hub server URL e.g. https://your.blackduck.url")
    parser.add_argument("-t", "--token-file",   required=True, help="File containing access token")
    parser.add_argument("-p", "--project-name",   required=True, help="Project Name")
    parser.add_argument("-pv", "--version-name",   required=True, help="Project Version Name")
    parser.add_argument("-mt", "--match-type",   required=False, help="Limit the action to components with specific Match Type ")
    parser.add_argument("-nv", "--no-verify",   action='store_false', help="Disable TLS certificate verification")
    parser.add_argument("--active", action='store_true', help='Status to set deep license to')
    return parser.parse_args()

def main():
    args = parse_command_args()
    with open(args.token_file, 'r') as tf:
        access_token = tf.readline().strip()
    global bd
    bd = Client(base_url=args.base_url, token=access_token, verify=args.no_verify, timeout=60.0, retries=4)

    params = {
        'q': [f"name:{args.project_name}"]
    }
    projects = [p for p in bd.get_resource('projects', params=params) if p['name'] == args.project_name]
    assert len(projects) == 1, f"There should be one, and only one project named {args.project_name}. We found {len(projects)}"
    project = projects[0]

    params = {
        'q': [f"versionName:{args.version_name}"]
    }
    versions = [v for v in bd.get_resource('versions', project, params=params) if v['versionName'] == args.version_name]
    assert len(versions) == 1, f"There should be one, and only one version named {args.version_name}. We found {len(versions)}"
    version = versions[0]

    headers = {'Accept': 'application/vnd.blackducksoftware.internal-1+json'}
    components = bd.get_resource('components',version, headers=headers)
    for component in components:
        pprint(component['matchTypes'])
        if not args.match_type:
            pass
        elif args.match_type not in component['matchTypes']: 
            continue
        try:
            deep_licenses = bd.get_resource('deep-license-data-list',component, headers=headers)
            set = []
            for deep_license in deep_licenses:
                set.append(deep_license)
            pprint (set_active(bd, set, status = args.active))
        except KeyError as err:
            pprint (err)

    logging.debug(f"Found {project['name']}:{version['versionName']}")


if __name__ == "__main__":
    sys.exit(main())