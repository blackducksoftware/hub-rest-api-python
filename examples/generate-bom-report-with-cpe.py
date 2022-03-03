import csv
import datetime
import sys

from blackduck import Client
import argparse
import logging
from pprint import pprint
import http.client
import requests
http.client._MAXHEADERS = 1000

now = datetime.datetime.now()
now = now.strftime("%d/%m/%Y %H:%M:%S")


def get_cpe_from_nvd(cve_id, comp_name, comp_version):
    nvd_url = "https://services.nvd.nist.gov/rest/json/cve/1.0/"
    r = requests.get(nvd_url + cve_id)
    response = r.json()
    # cpe_id = response['result']['CVE_Items'][0]['configurations']['nodes'][0]['cpe_match'][0]['cpe23Uri']
    # return cpe_id
    cpe_list = []
    print("Processing Component:" + ' ' + comp_name + ' ' + comp_version + ' ' + "and CVE:" + ' ' + cve_id)
    # print("Processing CVE:" + ' ' + cve_id)
    for node_info in response['result']['CVE_Items'][0]['configurations']['nodes']:
        for item in node_info['cpe_match']:
            cpe_match = item['cpe23Uri']
            comp_name_split = comp_name.split()
            if ' ' in comp_name:
                comp_name_list = comp_name_split[1:]
            else:
                comp_name_list = comp_name_split
            for value in comp_name_list:
                if (cpe_match.find(value.lower()) != -1) and (len(value) > 2):
                    print("Matched CPE =" + ' ' + cpe_match)
                    cpe_list.append(cpe_match)
                    break
                else:
                    str_value = ''.join(map(str, value))
                    n = 3
                    # value_new = [str_value[index: index + n] for index in range(0, len(str_value), n)]
                    value_new = [str_value[i:i + n] for i in range(0, len(str_value), n)]
                    if (cpe_match.find(value_new[0].lower()) != -1) and (len(value_new[0]) > 2):
                        print("Matched CPE =" + ' ' + cpe_match)
                        cpe_list.append(cpe_match)
                        # print(cve_id)
                        break
    return ','.join(set(cpe_list))


def csv_generator(bd, args):
    params = {
        'q': [f"name:{args.project_name}"]
    }
    projects = [p for p in bd.get_resource('projects', params=params) if p['name'] == args.project_name]
    assert len(
        projects) == 1, f"There should be one, and only one project named {args.project_name}. We found {len(projects)}"
    project = projects[0]

    params = {
        'q': [f"versionName:{args.version_name}"]
    }
    versions = [v for v in bd.get_resource('versions', project, params=params) if v['versionName'] == args.version_name]
    assert len(
        versions) == 1, f"There should be one, and only one version named {args.version_name}. We found {len(versions)}"
    version = versions[0]

    logging.debug(f"Found {project['name']}:{version['versionName']}")

    all_bom_component_vulns = []

    for bom_component_vuln in bd.get_resource('vulnerable-components', version):
        vuln_name = bom_component_vuln['vulnerabilityWithRemediation']['vulnerabilityName']
        vuln_source = bom_component_vuln['vulnerabilityWithRemediation']['source']
        upgrade_guidance = bd.get_json(f"{bom_component_vuln['componentVersion']}/upgrade-guidance")
        bom_component_vuln['upgrade_guidance'] = upgrade_guidance

        vuln_detail_headers = {'Accept': 'application/vnd.blackducksoftware.vulnerability-4+json'}
        vuln_details = bd.get_json(f"/api/vulnerabilities/{vuln_name}", headers=vuln_detail_headers)
        bom_component_vuln['vulnerability_details'] = vuln_details

        if 'related-vulnerability' in bd.list_resources(vuln_details):
            related_vuln = bd.get_resource("related-vulnerability", vuln_details, items=False)
        else:
            related_vuln = None
        bom_component_vuln['related_vulnerability'] = related_vuln
        all_bom_component_vulns.append(bom_component_vuln)

    '''Note: See the BD API doc and in particular .../api-doc/public.html#_bom_vulnerability_endpoints
        for a complete list of the fields available. The below code shows a subset of them just to
        illustrate how to write out the data into a CSV format.
    '''
    logging.info(f"Exporting {len(all_bom_component_vulns)} records to CSV file {args.csv_file}")
    with open(args.csv_file, 'w') as csv_f:
        field_names = [
            'Vulnerability Name',
            'Vulnerability Description',
            'Remediation Status',
            'Component',
            'Component Version',
            'Exploit Available',
            'Workaround Available',
            'Solution Available',
            'Upgrade Guidance - short term',
            'Upgrade Guidance - long term',
            'Related Vuln',
            'CPE Data'
        ]
        writer = csv.DictWriter(csv_f, fieldnames=field_names)
        writer.writeheader()
        for comp_vuln in all_bom_component_vulns:
            comp_name = comp_vuln['componentName']
            comp_version = comp_vuln['componentVersionName']
            if comp_vuln['related_vulnerability'] is not None:
                cve_id = comp_vuln['related_vulnerability'].get('name')
                # cpe_data = list(set(get_cpe_from_nvd(cve_id, comp_name)))
                cpe_data = get_cpe_from_nvd(cve_id, comp_name, comp_version)
                row_data = {
                    'Vulnerability Name': comp_vuln['vulnerabilityWithRemediation']['vulnerabilityName'],
                    'Vulnerability Description': comp_vuln['vulnerabilityWithRemediation']['description'],
                    'Remediation Status': comp_vuln['vulnerabilityWithRemediation']['remediationStatus'],
                    'Component': comp_vuln['componentName'],
                    'Component Version': comp_vuln['componentVersionName'],
                    'Exploit Available': comp_vuln['vulnerability_details'].get('exploitPublishDate', 'None available'),
                    'Workaround Available': comp_vuln['vulnerability_details'].get('workaround', 'None available'),
                    'Solution Available': comp_vuln['vulnerability_details'].get('solution', 'None available'),
                    'Upgrade Guidance - short term': comp_vuln['upgrade_guidance'].get('shortTerm', 'None available'),
                    'Upgrade Guidance - long term': comp_vuln['upgrade_guidance'].get('longTerm', 'None available'),
                    'Related Vuln': comp_vuln['related_vulnerability'].get('name', 'None available'),
                    'CPE Data': cpe_data
                }
            else:
                source = comp_vuln['vulnerabilityWithRemediation']['source']
                if source == 'NVD':
                    cve_id = comp_vuln['vulnerabilityWithRemediation']['vulnerabilityName']
                    cpe_data = get_cpe_from_nvd(cve_id, comp_name, comp_version)
                else:
                    cpe_data = ''
                row_data = {
                    'Vulnerability Name': comp_vuln['vulnerabilityWithRemediation']['vulnerabilityName'],
                    'Vulnerability Description': comp_vuln['vulnerabilityWithRemediation']['description'],
                    'Remediation Status': comp_vuln['vulnerabilityWithRemediation']['remediationStatus'],
                    'Component': comp_vuln['componentName'],
                    'Component Version': comp_vuln['componentVersionName'],
                    'Exploit Available': comp_vuln['vulnerability_details'].get('exploitPublishDate', 'None available'),
                    'Workaround Available': comp_vuln['vulnerability_details'].get('workaround', 'None available'),
                    'Solution Available': comp_vuln['vulnerability_details'].get('solution', 'None available'),
                    'Upgrade Guidance - short term': comp_vuln['upgrade_guidance'].get('shortTerm', 'None available'),
                    'Upgrade Guidance - long term': comp_vuln['upgrade_guidance'].get('longTerm', 'None available'),
                    'Related Vuln': 'None Available',
                    'CPE Data': cpe_data
                }
            writer.writerow(row_data)


def main(argv=None):
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] {%(module)s:%(lineno)d} %(levelname)s - %(message)s"
    )
    if argv is None:
        argv = sys.argv
    else:
        argv.extend(sys.argv)
    print("Today's Date:", now)
    print('############################################')
    print("Black Duck BoM to CPE Extraction Utility")
    print('############################################')
    parser = argparse.ArgumentParser("Extract CPE Data from NVD for Vulnerable BOM Components in a given Black Duck "
                                     "Project and Version")
    parser.add_argument("--base-url", required=True, help="Hub server URL e.g. https://your.blackduck.url")
    parser.add_argument("--token-file", dest='token_file', required=True, help="containing access token")
    parser.add_argument("--csv-file", dest='csv_file', required=True, help="Supply a CSV file name to get output "
                                                                           "formatted in CSV")
    parser.add_argument("--project", dest='project_name', required=True,
                        help="Project that contains the BOM components")
    parser.add_argument("--version", dest='version_name', required=True,
                        help="Version that contains the BOM components")
    parser.add_argument("--no-verify", dest='verify', action='store_false', help="disable TLS certificate verification")
    args = parser.parse_args()
    print(args)

    # Initiate Black Duck Client Class
    print("Initiating Black Duck Client Class")
    with open(args.token_file, 'r') as tf:
        access_token = tf.readline().strip()

    bd = Client(base_url=args.base_url, token=access_token, verify=args.verify)

    if args.csv_file:
        print("Generating CSV Report for: " + args.project_name + ' ' + args.version_name)
        csv_generator(bd, args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main(sys.argv[1:])