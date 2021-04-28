from blackduck import Client

import argparse

import logging
from pprint import pprint

logging.basicConfig(
    level=logging.DEBUG,
    format="[%(asctime)s] {%(module)s:%(lineno)d} %(levelname)s - %(message)s"
)

parser = argparse.ArgumentParser("Get a specific component and list its vulnerabilities")
parser.add_argument("--base-url", required=True, help="Hub server URL e.g. https://your.blackduck.url")
parser.add_argument("--token-file", dest='token_file', required=True, help="containing access token")
parser.add_argument("--project", dest='project_name', required=True, help="Project that contains the BOM components")
parser.add_argument("--version", dest='version_name', required=True, help="Version that contains the BOM components")
parser.add_argument("--no-verify", dest='verify', action='store_false', help="disable TLS certificate verification")
args = parser.parse_args()

with open(args.token_file, 'r') as tf:
    access_token = tf.readline().strip()

bd = Client(base_url=args.base_url, token=access_token, verify=args.verify)

params = {
    'q': [f"name:{args.project_name}"]
}
projects = [p for p in bd.get_resource('projects', params=params)]
assert len(projects) == 1, f"There should be one, and only one project named {args.project_name}. We found {len(projects)}"
project = projects[0]

params = {
    'q': [f"versionName:{args.version_name}"]
}
versions = [v for v in bd.get_resource('versions', project, params=params) if v['versionName'] == args.version_name]
assert len(versions) == 1, f"There should be one, and only one version named {args.version_name}. We found {len(versions)}"
version = versions[0]

logging.debug(f"Found {project['name']}:{version['versionName']}")

all_bom_component_vulns = []

for bom_component_vuln in bd.get_resource('vulnerable-components', version):
    vuln_name = bom_component_vuln['vulnerabilityWithRemediation']['vulnerabilityName']
    vuln_source = bom_component_vuln['vulnerabilityWithRemediation']['source']
    upgrade_guidance = bd.get_json(f"{bom_component_vuln['componentVersion']}/upgrade-guidance")
    bom_component_vuln['upgrade_guidance'] = upgrade_guidance

    vuln_details = bd.get_json(f"/api/vulnerabilities/{vuln_name}")

    pprint(bd.list_resources(vuln_details))
    if 'related-vulnerability' in bd.list_resources(vuln_details):
        related_vuln = bd.get_resource("related-vulnerability", vuln_details, items=False)
    else:
        related_vuln = None
    bom_component_vuln['related_vulnerability'] = related_vuln
    all_bom_component_vulns.append(bom_component_vuln)

pprint(bom_component_vuln)
