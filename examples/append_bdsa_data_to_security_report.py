"""
append_bdsa_data_to_security_report.py

Created on March 17, 2021

@author: DNicholls

Script that takes a security report CSV file and goes line by line and where it finds a BDSA vulnerability will call 
the Black Duck API to get more information from the BDSA record and adds additional columns for eacg row with this data.

Currently retrieves the solution and workaround text and adds these as 2 columns but can be modified to add more if required.

To run this script, you will need to pass the folder containing the security report, it will find any CSV file matching 
security*.csv and read the file line by line.  Where a BDSA vulnerability is found it will call the Black Duck API
to get more information on the BDSA record and add columns with the BDSA's solution and workarounds if applicable.

For this script to run, the hub-rest-api-python (blackduck) library and csv library will need to be installed.

"""

import argparse
from blackduck.HubRestApi import HubInstance
import os
import glob
import sys
import logging
import csv

parser = argparse.ArgumentParser("A program to add BDSA details to security reports.")
parser.add_argument("folder")
args = parser.parse_args()
hub = HubInstance()

logging.basicConfig(format='%(asctime)s:%(levelname)s:%(module)s: %(message)s', stream=sys.stderr, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("blackduck.HubRestApi").setLevel(logging.WARNING)

def checkdirs(folder):
    if os.path.isdir(folder) == False:
        raise NotADirectoryError("Folder {} is not a folder".format(folder))

def handle_security_reports(folder):
    logging.info(f"Looking for security reports in {folder}/security*.csv")
    for csvfile in glob.iglob(f"{folder}/security*.csv"):
        if '_with_bdsa' not in os.path.basename(csvfile):
            logging.debug(f"Handling security report file {csvfile}")
            handle_security_report(csvfile)
        
def handle_security_report(csvfile):
    # Create a new file for this report
    file_no_ext = os.path.splitext(csvfile)[0]
    file_to_create = file_no_ext + "_with_bdsa.csv"

    if os.path.isfile(file_to_create):
        raise FileExistsError(f"File {file_to_create} already exists so cannot write output file")

    # Read the security report line by line
    with open(file_to_create, "w", encoding="utf8") as output_csv_file:
        with open(csvfile, 'r', encoding="utf8") as read_obj:
            writer = csv.writer(output_csv_file, delimiter=',', lineterminator='\n')
            reader = csv.reader(read_obj)
            
            all = []
            row = next(reader)
            row.append('BDSA Id')
            row.append('BDSA Url')
            row.append('Solution')
            row.append('Workaround')
            all.append(row)

            for row in reader:
                vuln_id_cell = row[9]  # Currently the column index of 'Vulnerability id' column is 9.  Change if required.
                #logging.debug(f" CELL [{vuln_id_cell}]")
                bdsa_id = parse_bdsa_id(vuln_id_cell)
                #logging.debug(f"BDSA ID [{bdsa_id}]")
                if bdsa_id != None:
                    bdsa_data = load_bdsa_data(bdsa_id)
                    #logging.info(f"{bdsa_data}")
                    if bdsa_data and "solution" in bdsa_data and "workaround" in bdsa_data and "name" in bdsa_data:
                        #logging.debug(f"BDSA Data Solution [{bdsa_data['solution']}]")
                        #logging.debug(f"BDSA Data Workaround [{bdsa_data['workaround']}]")
                        #row.append(row[0])
                        row.append(bdsa_data['name'])
                        row.append(bdsa_data['_meta']['href'])
                        row.append(bdsa_data['solution'])
                        row.append(bdsa_data['workaround'])
                        all.append(row)
                    else:
                        logging.debug(f"BDSA Data not found for {bdsa_id}")
                        row.append(bdsa_id)
                        row.append('')
                        row.append('Failed to load BDSA data')
                        row.append('Failed to load BDSA data')
                        all.append(row)
                else:  
                    # Add the line as is.
                    logging.debug(f"No BDSA Record")
                    row.append('N/A')
                    row.append('N/A')
                    row.append('')
                    row.append('')
                    all.append(row)

            logging.info(f"Writing output csv file [{file_to_create}]")
            writer.writerows(all)
                
    # Write the report file.
    return None

def parse_bdsa_id(record):
    # Cell value could be a BDSA id, CVE id or both e.g. BDSA-2020-1128 (CVE-2020-1945)
    # This method will return the BDSA id if there is one regardless of the data
    if is_bdsa_record(record):
        if '(BDSA-' in record:
            # CVE-2020-1945 (BDSA-2020-1128)
            return record[record.index('(')+len('('):record.index(')')]
        elif '(CVE-' in record:
            # BDSA-2020-1128 (CVE-2020-1945)
            return record[0:record.index('(') - 1]
        elif '(' not in record:
            # BDSA-2020-1128
            return record
                 
    else:
        return None        


def is_bdsa_record(record):
    return 'BDSA' in record

def load_bdsa_data(bdsa_id):
    logging.debug(f"Retrieving BDSA data for [{bdsa_id}]")
    vuln = hub.get_vulnerabilities(bdsa_id)
    return vuln

def main():
    checkdirs(args.folder)
    handle_security_reports(args.folder)


main()
