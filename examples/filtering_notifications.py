'''
Created on Feb 3, 2023

@author: mkoishi

This script sets the not-interested notifications state for the appointed user to "SEEN" to free up the user from the notification flood.
The notification "type," which is either POLICY_OVERRIDE, or RULE_VIOLATION, or VULNERABILITY, or something else, determines the filter.
If the notification type is VULNERABILITY, it also checks optionally to see if the vulnerability is new.

Usage:
The following items must be filled out in the.restconfig-notifications.json file.
Note: 
1. "type" can take POLICY_OVERRIDE or RULE_VIOLATION or VULNERABILITY or else. Please refer to the Black Duck REST API documentation.
2. "vuln_source" is for future use.

{
   "baseurl": "YOUR_BLACKDUCK_URL",
   "api_token": "YOUR_API_TOKEN",
   "insecure": <true or false>,
   "timeout": 15.0,
   "retries": 3,
   "filters": {
       "type":"VULNERABILITY",
       "only_new_vulns": <true or false>
   },
   "vuln_source": "NVD",
   "user_name": "YOUR_USER_NAME"
}

Remarks:
If the number of the notifications is large, we may need to run this script a few rounds to fetch all notifications from Black Duck.
Since Client class of hub-rest-api-python uses a generator, we should not consider the pagination, and all notifications should be
returned by one attempt. It might be affected by the Black Duck side's buffer or else. It will require more research. Until then, please
run this script until the number of the fetched notifications becomes zero.

Copyright (C) 2023 Synopsys, Inc.
http://www.synopsys.com/

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

import logging
import sys
import json
import traceback
import re
from requests import RequestException
from blackduck import Client
from ast import literal_eval

def log_config():
    logging.basicConfig(format='%(asctime)s:%(levelname)s:%(module)s: %(message)s', stream=sys.stderr, level=logging.INFO)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("blackduck").setLevel(logging.WARNING)

def read_notifications(hub_client, notification_filters, user, vuln_source=None):
    params = {
        "filter": "notificationState:NEW"
    }
    for notification in hub_client.get_resource("notifications", user, params=params):
        logging.debug(f"Fetched notification item is {notification}")
        # Check if notification is NOT interested one and yield to get notification state to SEEN
        if not check_notificatons(notification, notification_filters, vuln_source):
            yield notification
    return

def get_user(hub_client, user_name):
    for user in hub_client.get_resource("users"):
        if user['userName'] == user_name:
            return user
    return None

def check_notificatons(notification, filters, vuln_source):
    # TODO: to check source of vulnerabilities, i.e. NVD or BDSA
    if notification['type'] == filters['type']:
        if filters['type'] == "VULNERABILITY" and filters['only_new_vulns']:
            if notification['content']['newVulnerabilityCount'] != 0:
                return notification
        else:
            return notification
            
    return None

def update_user_notification(hub_client, user_id, notification):
    notification_id = re.split("/", notification['_meta']['href'])[-1]
    put_data = {
        "notificationState": "SEEN"
    }
    return hub_client.session.put(f"/api/users/{user_id}/notifications/{notification_id}", json=put_data)

def main():
    log_config()
    try:
        with open('.restconfig-notifications.json','r') as f:
            config = json.load(f)
        set_to_seen = 0
        hub_client = Client(token=config['api_token'],
                            base_url=config['baseurl'],
                            verify=not config['insecure'],
                            timeout=config['timeout'],
                            retries=config['retries'])
        user_name = config['user_name']
        notification_filters = config['filters']
        vuln_source = config['vuln_source'] # Future use
        
        user = get_user(hub_client, user_name)
        if user:
            for notification in read_notifications(
                    hub_client,
                    notification_filters,
                    user,
                    vuln_source=vuln_source):
                user_id = re.split("/", user['_meta']['href'])[-1]
                res = update_user_notification(hub_client, user_id, notification)
                set_to_seen += 1
                content = literal_eval(res.content.decode("UTF-8"))
                logging.info(f"Notification state is set to SEEN for {content['type']}")
        else:
            logging.error(f"User not found for {user_name}")
    except RequestException as err:
        logging.error(f"Failed to read or update notification and the reason is {str(err)}")
    except Exception as err:
        logging.error(f"Failed to perform the task with exception {str(err)}. See also the stack trace")
        traceback.print_exc()
    finally:
        logging.info(f"=== Updating Notifications Finished ===")
        logging.info(f"{set_to_seen} Notifications are set to SEEN.")

if __name__ == '__main__':
    sys.exit(main())
