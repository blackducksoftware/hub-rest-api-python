"""
generate-bom-report-with-CPE-v2.py

Created on March 14, 2022

@author: vpedapati

Script that generates a CSV report with matched CPE data (fron NVD) for all BOM components in a given Project Version
in Black Duck. The script leverages CVE records for BOM components and calls NVD's CVE API to fetch matched CPE
strings. If a given component-version in a BOM does not have a vulnerability record, then it look for other older
versions ( based on released data in ascending order) of the component to see if they have any vulnerabilities. Then
it loops through each version until it stumbles upon a component-version that has a CVE record and that returns a CPE
match from NVD. Currently, the script has a default search limit of 50 for other older versions of components to loop
through but it’s customizable using an argument (--other-comp-version-count) if you would like to either reduce or
expand the search base and get more CPE matches. As such, the script would take considerably longer time now to
execute. """

import csv
import datetime
import re
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
    cpe_list = []
    print("Extracting CPE data for Component:" + ' ' + comp_name + ' ' + comp_version + ' ' + "and CVE:" + ' ' + cve_id)
    # print("Processing CVE:" + ' ' + cve_id)
    for node_info in response['result']['CVE_Items'][0]['configurations']['nodes']:
        for item in node_info['cpe_match']:
            cpe_match = item['cpe23Uri']
            comp_name_split = comp_name.split()
            if ' ' in comp_name:
                comp_name_list = comp_name_split[1:]
                for value in comp_name_list:
                    # Remove special characters from value
                    new_string = re.sub(r"[^a-zA-Z0-9]", "", value)
                    if (cpe_match.find(new_string.lower()) != -1) and (len(new_string) >= 2):
                        print("Matched CPE =" + ' ' + cpe_match)
                        cpe_list.append(cpe_match)
                        break
                    else:
                        str_value = ''.join(map(str, new_string))
                        n = 3
                        # value_new = [str_value[index: index + n] for index in range(0, len(str_value), n)]
                        value_new = [str_value[i:i + n] for i in range(0, len(str_value), n)]
                        if (cpe_match.find(value_new[0].lower()) != -1) and (len(value_new[0]) > 2):
                            print("Matched CPE =" + ' ' + cpe_match)
                            cpe_list.append(cpe_match)
                            # print(cve_id)
                            break
                        else:
                            comp_name_first = comp_name_split[0]
                            if (cpe_match.find(comp_name_first.lower()) != -1) and (len(comp_name_first) >= 2):
                                print("Matched CPE =" + ' ' + cpe_match)
                                cpe_list.append(cpe_match)
                                break
            else:
                comp_name_list = comp_name_split[0]
                if (cpe_match.find(comp_name_list.lower()) != -1) and (len(comp_name_list) >= 2):
                    print("Matched CPE =" + ' ' + cpe_match)
                    cpe_list.append(cpe_match)
                    break
                else:
                    # Remove special characters from value
                    new_string = re.sub(r"[^a-zA-Z0-9]", "", comp_name_list)
                    if (cpe_match.find(new_string.lower()) != -1) and (len(new_string) >= 2):
                        print("Matched CPE =" + ' ' + cpe_match)
                        cpe_list.append(cpe_match)
                        return
                    else:
                        str_value = ''.join(map(str, comp_name_list))
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
    project_url = projects[0]['_meta']['href']
    project_uuid = project_url.split('projects/', 1)[1]
    print(project_uuid)

    params = {
        'q': [f"versionName:{args.version_name}"]
    }
    versions = [v for v in bd.get_resource('versions', project, params=params) if v['versionName'] == args.version_name]
    assert len(
        versions) == 1, f"There should be one, and only one version named {args.version_name}. We found {len(versions)}"
    version = versions[0]
    version_url = versions[0]['_meta']['href']
    version_uuid = version_url.split('versions/', 1)[1]
    print(version_uuid)

    logging.debug(f"Found {project['name']}:{version['versionName']}")

    all_bom_component_vulns = []

    comp_detail_headers = {'Accept': 'application/vnd.blackducksoftware.bill-of-materials-6+json'}
    comp_details_initial = bd.get_json(f"/api/projects/{project_uuid}/versions/{version_uuid}/components",
                                       headers=comp_detail_headers)
    totalcount_comp_details = str(comp_details_initial['totalCount'])
    comp_details_full = bd.get_json(
        f"/api/projects/{project_uuid}/versions/{version_uuid}/components?limit={totalcount_comp_details}",
        headers=comp_detail_headers)

    logging.info(f"Exporting {totalcount_comp_details} records to CSV file {args.csv_file}")
    with open(args.csv_file, 'w') as csv_f:
        field_names = [
            'Vulnerability Name',
            'Related Vuln',
            'Component',
            'Component Version',
            'Component Homepage',
            'License Name',
            'CPE Data'
        ]
        writer = csv.DictWriter(csv_f, fieldnames=field_names)
        writer.writeheader()

        for bom_comp in comp_details_full['items']:
            comp_name = bom_comp['componentName']
            comp_version = bom_comp['componentVersionName']
            comp_url = bom_comp['component']
            comp_version_url = bom_comp['componentVersion']
            comp_license = bom_comp['licenses'][0]['licenseDisplay']
            comp_headers = {'Accept': 'application/vnd.blackducksoftware.component-detail-5+json'}
            comp_home = bd.get_json(comp_url, headers=comp_headers)
            comp_homepage = comp_home.get('url', 'None available')
            print("--------->Processing Component:" + ' ' + comp_name + ' ' + comp_version)
            vuln_detail_headers = {'Accept': 'application/vnd.blackducksoftware.vulnerability-4+json'}
            vuln_details = bd.get_json(comp_version_url + "/vulnerabilities", headers=vuln_detail_headers)
            vuln_details_count = str(vuln_details['totalCount'])
            if vuln_details['totalCount'] == 0:
                print("Found" + ' ' + vuln_details_count + " vulnerabilities, looking for other versions of this "
                                                           "component with CVE records")
                other_compversion_detail_headers = {
                    'Accept': 'application/vnd.blackducksoftware.component-detail-5+json'}
                other_compversion_details = bd.get_json(comp_url + f"/versions?sort=releasedon:asc&limit={args.other_comp_version_count}",
                                                        headers=other_compversion_detail_headers)
                total_other_comp_count = other_compversion_details['totalCount']
                print("Found " + str(total_other_comp_count) + " other versions for " + comp_name)
                haszerovuln = True
                otherversioncount = 0
                for other_compversion_version in other_compversion_details['items']:
                    other_compversion_name = other_compversion_version['versionName']
                    other_compversion_vuln_url = other_compversion_version['_meta']['href']

                    other_compversion_vuln_headers = {
                        'Accept': 'application/vnd.blackducksoftware.vulnerability-4+json'}
                    other_compversion_vuln_details = bd.get_json(other_compversion_vuln_url + "/vulnerabilities",
                                                                 headers=other_compversion_vuln_headers)
                    other_compversion_vuln_count = str(other_compversion_vuln_details['totalCount'])
                    otherversioncount = otherversioncount+1
                    if other_compversion_vuln_details['totalCount'] == 0:
                        print(str(otherversioncount) + " Out of " + str(total_other_comp_count) + " other version" + ' ' + other_compversion_name + " does not have any vulnerability, SKIPPING")
                    else:
                        haszerovuln = False
                        print("Other version" + ' ' + other_compversion_name + " has" + ' ' + other_compversion_vuln_count + ' ' + "vulnerabilities")
                        for other_compversion_vulns in other_compversion_vuln_details['items']:
                            vuln_id_details = other_compversion_vulns['_meta']['href']
                            vuln_name = vuln_id_details.split('vulnerabilities/', 1)[1]
                            vuln_detail_headers = {'Accept': 'application/vnd.blackducksoftware.vulnerability-4+json'}
                            vuln_details = bd.get_json(f"/api/vulnerabilities/{vuln_name}", headers=vuln_detail_headers)
                            vuln_souce = vuln_details['source']
                            if vuln_souce == 'NVD':
                                # other_compversion_vulns['vulnerability_details'] = vuln_details
                                cve_id = vuln_details['name']
                                cpe_data = get_cpe_from_nvd(cve_id, comp_name, other_compversion_name)
                                if cpe_data != '':
                                    print("Writing record to CSV file WITH matched CPE data")
                                    row_data = {
                                        'Vulnerability Name': cve_id,
                                        'Related Vuln': 'None available',
                                        'Component': comp_name,
                                        'Component Version': comp_version,
                                        'Component Homepage': comp_homepage,
                                        'License Name': comp_license,
                                        'CPE Data': cpe_data
                                    }
                                    break
                                break
                            elif 'related-vulnerability' in bd.list_resources(vuln_details):
                                related_vuln = bd.get_resource("related-vulnerability", vuln_details, items=False)
                                cve_id = related_vuln['name']
                                cpe_data = get_cpe_from_nvd(cve_id, comp_name, other_compversion_name)
                                if cpe_data != '':
                                    print("Writing record to CSV file WITH matched CPE data")
                                    row_data = {
                                        'Vulnerability Name': cve_id,
                                        'Related Vuln': cve_id,
                                        'Component': comp_name,
                                        'Component Version': comp_version,
                                        'Component Homepage': comp_homepage,
                                        'License Name': comp_license,
                                        'CPE Data': cpe_data
                                    }
                                    break
                                break
                        break
                    # writer.writerow(row_data)
            else:
                haszerovuln = False
                print("Found " + ' ' + vuln_details_count + " vulnerabilities")
                for main_comp_version_vuln in vuln_details['items']:
                    vuln_souce = main_comp_version_vuln['source']
                    if vuln_souce == 'NVD':
                        # other_compversion_vulns['vulnerability_details'] = vuln_details
                        cve_id = main_comp_version_vuln['name']
                        cpe_data = get_cpe_from_nvd(cve_id, comp_name, comp_version)
                        if cpe_data != '':
                            print("Writing record to CSV file WITH matched CPE data")
                            row_data = {
                                'Vulnerability Name': cve_id,
                                'Related Vuln': 'None available',
                                'Component': comp_name,
                                'Component Version': comp_version,
                                'Component Homepage': comp_homepage,
                                'License Name': comp_license,
                                'CPE Data': cpe_data
                            }
                            break
                    elif 'related-vulnerability' in bd.list_resources(main_comp_version_vuln):
                        related_vuln = bd.get_resource("related-vulnerability", main_comp_version_vuln, items=False)
                        cve_id = related_vuln['name']
                        cpe_data = get_cpe_from_nvd(cve_id, comp_name, comp_version)
                        if cpe_data != '':
                            print("Writing record to CSV file WITH matched CPE data")
                            row_data = {
                                'Vulnerability Name': cve_id,
                                'Related Vuln': cve_id,
                                'Component': comp_name,
                                'Component Version': comp_version,
                                'Component Homepage': comp_homepage,
                                'License Name': comp_license,
                                'CPE Data': cpe_data
                            }
                            break
            if haszerovuln:
                print("Writing record to CSV file WITHOUT matched CPE data")
                row_data = {
                    'Vulnerability Name': 'None available',
                    'Related Vuln': 'None available',
                    'Component': comp_name,
                    'Component Version': comp_version,
                    'Component Homepage': comp_homepage,
                    'License Name': comp_license,
                    'CPE Data': ''
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
    parser.add_argument("--other-comp-version-count", dest='other_comp_version_count', required=False, const=50, nargs='?', type=int, default=50,
                        help="Count of other component versions to search for a CVE record to fetch CPE. Default is "
                             "50 other component versions")

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
