'''
Created on Dec 19, 2018
Updated on Sept 20, 2024

@author: gsnyder
@contributor: smiths

Generate a CSV report for a given project-version and enhance with "File Paths", "How to Fix", and 
"References and Related Links"
'''

import argparse
import csv
import io
import json
import logging
import time
import zipfile
from blackduck.HubRestApi import HubInstance
from requests.exceptions import MissingSchema

logging.basicConfig(
    level=logging.DEBUG,
    format="[%(asctime)s] {%(module)s:%(lineno)d} %(levelname)s - %(message)s"
)

version_name_map = {
    'version': 'VERSION',
    'scans': 'CODE_LOCATIONS',
    'components': 'COMPONENTS',
    'vulnerabilities': 'SECURITY',
    'source': 'FILES',
    'cryptography': 'CRYPTO_ALGORITHMS',
    'license_terms': 'LICENSE_TERM_FULFILLMENT',
    'component_additional_fields': 'BOM_COMPONENT_CUSTOM_FIELDS',
    'project_version_additional_fields': 'PROJECT_VERSION_CUSTOM_FIELDS',
    'vulnerability_matches': 'VULNERABILITY_MATCH'
}

all_reports = list(version_name_map.keys())

parser = argparse.ArgumentParser("A program to create reports for a given project-version")
parser.add_argument("project_name")
parser.add_argument("version_name")
parser.add_argument("-z", "--zip_file_name", default="reports.zip")
parser.add_argument("-r", "--reports",
    default=",".join(all_reports), 
    help=f"Comma separated list (no spaces) of the reports to generate - {list(version_name_map.keys())}. Default is all reports.",
    type=lambda s: s.upper())
parser.add_argument('--format', default='CSV', choices=["CSV"], help="Report format - only CSV available for now")
parser.add_argument('-t', '--tries', default=5, type=int, help="How many times to retry downloading the report, i.e. wait for the report to be generated")
parser.add_argument('-s', '--sleep_time', default=30, type=int, help="The amount of time to sleep in-between (re-)tries to download the report")

args = parser.parse_args()

hub = HubInstance()

class FailedReportDownload(Exception):
    pass

def download_report(location, filename, retries=args.tries):
    report_id = location.split("/")[-1]

    for attempt in range(retries):
        
        # Wait for 30 seconds before attempting to download
        print(f"Waiting 30 seconds before attempting to download...")
        time.sleep(30)

        # Retries
        print(f"Attempt {attempt + 1} of {retries} to retrieve report {report_id}")        
        
        # Report Retrieval 
        print(f"Retrieving generated report from {location}")
        response = hub.download_report(report_id)
        
        if response.status_code == 200:
            with open(filename, "wb") as f:
                f.write(response.content)
            print(f"Successfully downloaded zip file to {filename} for report {report_id}")
            return response.content
        else:
            print(f"Failed to retrieve report {report_id}")
            if attempt < retries - 1:  # If it's not the last attempt
                wait_time = args.sleep_time
                print(f"Waiting {wait_time} seconds before retrying...")
                time.sleep(wait_time)
            else:
                print(f"Maximum retries reached. Unable to download report.")
    
    raise FailedReportDownload(f"Failed to retrieve report {report_id} after {retries} tries")

def get_file_paths(hub, project_id, project_version_id, component_id, component_version_id, component_origin_id):
    url = f"{hub.get_urlbase()}/api/projects/{project_id}/versions/{project_version_id}/components/{component_id}/versions/{component_version_id}/origins/{component_origin_id}/matched-files"
    headers = {
        "Accept": "application/vnd.blackducksoftware.bill-of-materials-6+json",
        "Authorization": f"Bearer {hub.token}"
    }
    
    logging.debug(f"Making API call to: {url}")
    
    try:
        response = hub.execute_get(url)
        if response.status_code == 200:
            data = response.json()
            file_paths = []
            for item in data.get('items', []):
                file_path = item.get('filePath', {})
                composite_path = file_path.get('compositePathContext', '')
                if composite_path:
                    file_paths.append(composite_path)
            return file_paths
        else:
            logging.error(f"Failed to fetch matched files. Status code: {response.status_code}")
            return []
    except Exception as e:
        logging.error(f"Error making API request: {str(e)}")
        return []

def get_vulnerability_details(hub, vulnerability_id):
    url = f"{hub.get_urlbase()}/api/vulnerabilities/{vulnerability_id}"
    
    try:
        response = hub.execute_get(url)
        if response.status_code == 200:
            data = response.json()
            solution = data.get('solution', '')
            references = []
            meta_data = data.get('_meta', {})
            links = meta_data.get('links', [])
            for link in links:
                references.append({
                    'rel': link.get('rel', ''),
                    'href': link.get('href', '')
                })
            return solution, references
        else:
            logging.error(f"Failed to fetch vulnerability details. Status code: {response.status_code}")
            return '', []
    except Exception as e:
        logging.error(f"Error making API request for vulnerability details: {str(e)}")
        return '', []

def enhance_security_report(hub, zip_content, project_id, project_version_id):
    logging.info(f"Enhancing security report for Project ID: {project_id}, Project Version ID: {project_version_id}")
    
    with zipfile.ZipFile(io.BytesIO(zip_content), 'r') as zin:
        csv_files = [f for f in zin.namelist() if f.endswith('.csv')]
        for csv_file in csv_files:
            csv_content = zin.read(csv_file).decode('utf-8')
            reader = csv.DictReader(io.StringIO(csv_content))
            
            # Count total rows
            total_rows = sum(1 for row in reader)
            reader = csv.DictReader(io.StringIO(csv_content))  # Reset reader
            
            fieldnames = reader.fieldnames + ["File Paths", "How to Fix", "References and Related Links"]
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()

            processed_components = 0
            skipped_components = 0

            for index, row in enumerate(reader, 1):
                print(f"\rProcessing row {index} of {total_rows} ({index/total_rows*100:.2f}%)", end='', flush=True)
                
                component_id = row.get('Component id', '')
                component_version_id = row.get('Version id', '')
                component_origin_id = row.get('Origin id', '')
                vulnerability_id = row.get('Vulnerability id', '')

                if not all([component_id, component_version_id, component_origin_id]):
                    logging.warning(f"Missing component information. Component ID: {component_id}, Component Version ID: {component_version_id}, Origin ID: {component_origin_id}")
                    skipped_components += 1
                    file_paths = []
                else:
                    file_paths = get_file_paths(hub, project_id, project_version_id, component_id, component_version_id, component_origin_id)
                    processed_components += 1

                if vulnerability_id:
                    solution, references = get_vulnerability_details(hub, vulnerability_id)
                else:
                    solution, references = '', []

                row["File Paths"] = '; '.join(file_paths) if file_paths else "No file paths available"
                row["How to Fix"] = solution
                row["References and Related Links"] = json.dumps(references)
                
                writer.writerow(row)

            print("\nProcessing complete.")

            # Generate a unique filename for the enhanced report
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            enhanced_filename = f"enhanced_security_report_{timestamp}.csv"

            # Update zip file with modified CSV
            with zipfile.ZipFile(args.zip_file_name, 'a') as zout:
                zout.writestr(enhanced_filename, output.getvalue())

    logging.info(f"Enhanced security report saved to {args.zip_file_name}")
    logging.info(f"Processed components: {processed_components}")
    logging.info(f"Skipped components: {skipped_components}")

def main():
    hub = HubInstance()

    project = hub.get_project_by_name(args.project_name)

    if project:
        project_id = project['_meta']['href'].split('/')[-1]
        logging.info(f"Project ID: {project_id}")

        version = hub.get_version_by_name(project, args.version_name)
        if version:
            project_version_id = version['_meta']['href'].split('/')[-1]
            logging.info(f"Project Version ID: {project_version_id}")

            reports_l = [version_name_map.get(r.strip().lower(), r.strip()) for r in args.reports.split(",")]

            valid_reports = set(version_name_map.values())
            invalid_reports = [r for r in reports_l if r not in valid_reports]
            if invalid_reports:
                print(f"Error: Invalid report type(s): {', '.join(invalid_reports)}")
                print(f"Valid report types are: {', '.join(valid_reports)}")
                exit(1)

            response = hub.create_version_reports(version, reports_l, args.format)

            if response.status_code == 201:
                print(f"Successfully created reports ({args.reports}) for project {args.project_name} and version {args.version_name}")
                location = response.headers['Location']
                zip_content = download_report(location, args.zip_file_name)
                
                if 'SECURITY' in reports_l:
                    enhance_security_report(hub, zip_content, project_id, project_version_id)
            else:
                print(f"Failed to create reports for project {args.project_name} version {args.version_name}, status code returned {response.status_code}")
        else:
            print(f"Did not find version {args.version_name} for project {args.project_name}")
    else:
        print(f"Did not find project with name {args.project_name}")

if __name__ == "__main__":
    main()