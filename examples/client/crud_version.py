from blackduck import Client
from blackduck.constants import PROJECT_VERSION_SETTINGS, VERSION_DISTRIBUTION, VERSION_PHASES

import argparse
import logging
import requests

logging.basicConfig(
    level=logging.DEBUG,
    format="[%(asctime)s] {%(module)s:%(lineno)d} %(levelname)s - %(message)s"
)

parser = argparse.ArgumentParser("Create, read, update, and delete a project")
parser.add_argument("--base-url", required=True, help="Hub server URL e.g. https://your.blackduck.url")
parser.add_argument("--token-file", dest='token_file', required=True, help="containing access token")
parser.add_argument("--no-verify", dest='verify', action='store_false', help="disable TLS certificate verification")
parser.add_argument("project", help="Project name")
parser.add_argument("version", help="Version name")
args = parser.parse_args()

with open(args.token_file, 'r') as tf:
    access_token = tf.readline().strip()

bd = Client(
    base_url=args.base_url,
    token=access_token,
    verify=args.verify
)

project_name = args.project

# POST project
project_data = {
    'name': project_name,
    'description': "some description",
    'projectLevelAdjustments': True,
}

try:
    r = bd.session.post("/api/projects", json=project_data)
    r.raise_for_status()
    print(f"created project {r.links['project']['url']}")
except requests.HTTPError as err:
    # more fine grained error handling here; otherwise:
    bd.http_error_handler(err)

# GET project
params = {
    'q': [f"name:{project_name}"]
}

project_obj = None
project_url = None
for project in bd.get_items("/api/projects", params=params):
    if project['name'] == project_name:
        project_obj = project
        project_url = bd.list_resources(project)['href']
        print(f"project url: {project_url}")

# POST version
version_data = {
    'versionName': args.version,
    'distribution': 'EXTERNAL',
    'phase': 'PLANNING'
}

versions_url = project_url + "/versions"
try:
    r = bd.session.post(versions_url, json=version_data)
    r.raise_for_status()
    version_url = r.headers['Location']
    print(f"created version {version_url}")
except requests.HTTPError as err:
    # more fine grained error handling here; otherwise:
    bd.http_error_handler(err)

# GET or CREATE version

version = bd.get_or_create_resource(field='versionName', value=args.version, name="versions", parent=project_obj)
print(f"Version {version['versionName']} was either found or created after initial POST")

# DELETE version
try:
    r = bd.session.delete(version_url)
    r.raise_for_status()
    print(f"deleted version {args.version}")
except requests.HTTPError as err:
    if err.response.status_code == 404:
        print("not found")
    else:
        bd.http_error_handler(err)

# GET or CREATE version
params = {
    'phase': 'PLANNING',
    'distribution': 'SAAS'
}
version = bd.get_or_create_resource(field='versionName', value=args.version, name="versions", parent=project_obj, params=params)
print(f"Version {version['versionName']} was either found or created after deleting the version")

# DELETE project
try:
    r = bd.session.delete(project_url)
    r.raise_for_status()
    print("deleted project")
except requests.HTTPError as err:
    if err.response.status_code == 404:
        print("not found")
    else:
        bd.http_error_handler(err)

