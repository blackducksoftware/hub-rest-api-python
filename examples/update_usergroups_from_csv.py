'''
Created on Jan 27, 2023
@author: dnichol
Bulk update user group names from CSV.  CSV file requires two columns, titled 'Existing' and 'New'.  This script is case sensitive.
'''

import csv
import logging
import argparse
import sys
import json
import traceback
from requests import HTTPError, RequestException

from blackduck import Client

def log_config():
    # TODO: debug option in .restconfig file to be reflected
    logging.basicConfig(format='%(asctime)s:%(levelname)s:%(module)s: %(message)s', stream=sys.stderr, level=logging.DEBUG)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("blackduck").setLevel(logging.WARNING)

def parse_parameter():
    parser = argparse.ArgumentParser("Bulk update user groups from CSV file - modifies the name of the user groups given the existing name and new name")
    parser.add_argument("CSV", help="Location of the CSV file")
                    # "CSV File requires two columns titled 'Existing' and 'New'",
    return parser.parse_args()

def get_user_group_by_name(hub_client, name):
    params = {
      'q': [f"name:{name}"]
    }
    for user_group in hub_client.get_items("/api/usergroups", params=params):
        if user_group['name'] == name:
            user_url = hub_client.list_resources(user_group)['href']
            print(f"Found user group: {name}")
            return user_group
    

def read_csv(hub_client, csv_path):
    updated = 0
    failed = 0
    not_found = 0
    with open(csv_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            existing_name = (row['Existing'])
            new_name = (row['New'])
            try:
                user = get_user_group_by_name(hub_client, existing_name)
                if user:
                    update_user_group(hub_client, existing_name, new_name, user)
                    updated += 1
                else:
                    logging.info(f"User group {existing_name} was not found")
                    not_found += 1
            except RequestException as err:
                logging.error(f"Failed to update user group {existing_name}. Reason is " + str(err))
                failed += 1
            except Exception as err:
                raise err

        logging.info(f"------------------------------")
        logging.info(f"Execution complete.")
        logging.info(f"{updated} user groups updated")
        logging.info(f"{not_found} user groups were not found")
        logging.info(f"{failed} user groups failed to update")

def update_user_group(hub_client, existing_name, new_name, user_group):
    user_group_url = hub_client.list_resources(user_group)['href']

    # Update the name.
    user_group['name'] = new_name

    logging.info(f"Updating user group {existing_name} to {user_group['name']} for user group {user_group_url}s")
    hub_client.session.put(user_group_url, json=user_group)


def main():
    log_config()
    args = parse_parameter()
    try:
        with open('.restconfig.json','r') as f:
            config = json.load(f)
        hub_client = Client(token=config['api_token'],
                            base_url=config['baseurl'],
                            verify=not config['insecure'],
                            timeout=15,
                            retries=3)
        
        read_csv(hub_client, args.CSV)
    except HTTPError as err:
        hub_client.http_error_handler(err)
    except Exception as err:
        logging.error(f"Failed to perform the task. See the stack trace")
        traceback.print_exc()

if __name__ == '__main__':
    sys.exit(main())
    
