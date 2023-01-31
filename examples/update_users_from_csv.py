'''
Created on Jan 27, 2023
@author: dnichol
Bulk update users email addresses from CSV.  CSV file requires two columns, titled 'Existing' and 'New'.  This script is case sensitive.

This script requires a .restconfig.json file present to configure the connection details.  For more details see : https://community.synopsys.com/s/article/How-to-use-the-hub-rest-api-python-for-Black-Duck

The .restconfig.json file should be in the following format:

{
   "baseurl": "https://your-hub-dns",
   "api_token": "insert-token-here",
   "insecure": true,
   "debug": false
}

Licensed to the Apache Software Foundation (ASF) under one
or more contributor license agreements. See the NOTICE file
distributed with this work for additional information
regarding copyright ownership. The ASF licenses this file
to you under the Apache License, Version 2.0 (the
"License"); you may not use this file except in compliance
with the License. You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
KIND, either express or implied. See the License for the
specific language governing permissions and limitations
under the License.
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
    logging.basicConfig(format='%(asctime)s:%(levelname)s:%(module)s: %(message)s', stream=sys.stderr, level=logging.DEBUG)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("blackduck").setLevel(logging.WARNING)

def parse_parameter():
    parser = argparse.ArgumentParser("Bulk update users from CSV file - modifies the email addresses of the users given the existing email and new email address")
    parser.add_argument("CSV", help="Location of the CSV file")
                    # "CSV File requires two columns titled 'Existing' and 'New'",
    return parser.parse_args()

def get_user_by_email(hub_client, email):
    params = {
      'q': [f"name:{email}"]
    }
    for user in hub_client.get_items("/api/users", params=params):
        if user['email'] == email:
            user_url = hub_client.list_resources(user)['href']
            print(f"Found user: {email}")
            return user
    

def read_csv(hub_client, csv_path):
    updated = 0
    failed = 0
    not_found = 0
    with open(csv_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            existing_email = (row['Existing'])
            new_email = (row['New'])
            try:
                user = get_user_by_email(hub_client, existing_email)
                if user:
                    update_user(hub_client, existing_email, new_email, user)
                    updated += 1
                else:
                    logging.info(f"User {existing_email} was not found")
                    not_found += 1
            except RequestException as err:
                logging.error(f"Failed to update user {existing_email}. Reason is " + str(err))
                failed += 1
            except Exception as err:
                raise err

        logging.info(f"------------------------------")
        logging.info(f"Execution complete.")
        logging.info(f"{updated} users updated")
        logging.info(f"{not_found} users were not found")
        logging.info(f"{failed} users failed to update")

def update_user(hub_client, existing_email, new_email, user):
    user_url = hub_client.list_resources(user)['href']

    # Update the email address.
    user['email'] = new_email

    # Not just update the email address.  If the email is also used as userName and externalUserName then update them too.
    if user['userName'] == existing_email:
        user['userName'] = new_email
    if user.get('externalUserName') and user['externalUserName'] == existing_email:
        user['externalUserName'] = new_email

    logging.info(f"Updating user {existing_email} to {user['email']} for user {user_url}")
    hub_client.session.put(user_url, json=user)


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
    
