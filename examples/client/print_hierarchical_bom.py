from blackduck import Client

import argparse
import logging
import http.client

http.client._MAXHEADERS = 1000

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] {%(module)s:%(lineno)d} %(levelname)s - %(message)s"
)

parser = argparse.ArgumentParser("SBOM")
parser.add_argument("--base-url", required=True, help="Hub server URL e.g. https://your.blackduck.url")
parser.add_argument("--token-file", dest='token_file', required=True, help="containing access token")
parser.add_argument("--project", dest='project_name', required=True, help="project name")
parser.add_argument("--version", dest='version_name', required=True, help="Version that contains the BOM components")
parser.add_argument("--no-verify", dest='verify', action='store_false', help="disable TLS certificate verification")
args = parser.parse_args()

with open(args.token_file, 'r') as tf:
    access_token = tf.readline().strip()

bd = Client(
    base_url=args.base_url,
    token=access_token,
    verify=args.verify
)

def print_children(comp, comp_depth):
    if 'children' in bd.list_resources(comp):
        for comp_child in bd.get_resource('children', comp):
            child_depth = comp_depth + 1
            for i in range(comp_depth):
                print(f"   ", end = '')
            print(f"-> {comp_child['componentName']}")
            print_children(comp_child, child_depth)


params_project = {
    'q': [f"name: {args.project_name}"]
}
projects = [p for p in bd.get_resource('projects', params=params_project) if p['name'] == args.project_name]
assert len(projects) == 1, f"There should be one, and only one project named {args.project_name}. We found {len(projects)}"
project = projects[0]
params_version = {
    'q': [f"versionName:{args.version_name}"]
}

versions = [v for v in bd.get_resource('versions', project, params=params_version) if v['versionName'] == args.version_name]
assert len(versions) == 1, f"There should be one, and only one version named {args.version_name}. We found {len(versions)}"
version = versions[0]

logging.debug(f"Found {project['name']}:{version['versionName']}")

for comp in bd.get_resource('hierarchical-components', version):
    print(comp['componentName'])
    print_children(comp, 0)
