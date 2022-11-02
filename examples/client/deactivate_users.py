'''
Purpose: Deactivates Black Duck users who are not actively using the system, will warn for users that have never logged in.

Usage:
deactivate_users.py [--dry-run] [--since-days DAYS] [--interactive] [--base-url https://your.blackduck.url] [--token-file token.txt]

required arguments:
  --base-url BASE_URL      Hub server URL e.g. https://your.blackduck.url
  --token-file TOKEN_FILE  containing access token

optional arguments:
    --dry-run       Show actions that would be executed on a normal run
    --since-days    Number of days since last login for a user to be inactive. Default: 90
    --interactive   Run in interactive mode to choose which users to deactivate

Examples:

authentication required for all examples below
--base-url https://your.blackduck.url --token-file token.txt

print help message
python deactivate_users.py -h

deactivate all users who haven't logged in for more than 90 days
python deactivate_users.py

log users that would be deactivated who haven't logged in for more than 90 days
python deactivate_users.py --dry-run

deactivate all users who haven't logged in for more than 30 days
python deactivate_users.py --since-days 30

interactively deactivate users who haven't logged in for more than 120 days
python deactivate_users.py --since-days 120 --interactive
'''

from blackduck import Client
import logging
import argparse

def query_yes_no(question, default="yes"):
    """Ask a yes/no question via input() and return their answer.

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
            It must be "yes" (the default), "no" or None (meaning
            an answer is required of the user).

    The "answer" return value is True for "yes" or False for "no".
    """
    valid = {"yes": True, "y": True, "ye": True, "no": False, "n": False}
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        print(question + prompt)
        choice = input().lower()
        if default is not None and choice == "":
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            print("Please respond with 'yes' or 'no' " "(or 'y' or 'n').\n")

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] {%(module)s:%(lineno)d} %(levelname)s - %(message)s"
)

# Use -h to print help message
parser = argparse.ArgumentParser("Deactivates users in the system")
parser.add_argument("--base-url", required=True, help="Hub server URL e.g. https://your.blackduck.url")
parser.add_argument("--token-file", dest='token_file', required=True, help="containing access token")
parser.add_argument("--no-verify", dest='verify', action='store_false', help="disable TLS certificate verification")
parser.add_argument("-d", "--dry-run", action='store_true', help=f"Run in dry-run mode to determine users it will update")
parser.add_argument("-s", "--since-days", default=90, type=int, help=f"Number of days since last login for a user to be inactive. Default: 90")
parser.add_argument("-i", "--interactive", action='store_true', help=f"Run in interactive mode to manually choose which users to deactivate, has no effect when run with dry-run mode")

args = parser.parse_args()

with open(args.token_file, 'r') as tf:
    access_token = tf.readline().strip()

bd = Client(
    base_url=args.base_url,
    token=access_token,
    verify=args.verify
)

system_users = ['sysadmin', 'anonymous', 'blackduck_system', 'default-authenticated-user']

dormant_params = {
   "sinceDays": args.since_days
}

headers = {
    'accept': "application/vnd.blackducksoftware.user-4+json"
}

for user in bd.get_items("api/dormant-users", params=dormant_params, headers=headers):
    if user['username'] not in system_users:
        # If the user has logged in before
        if 'lastLogin' in user:
            if args.dry_run:
                logging.info(f"Will mark user '{user['username']}' as inactive, their last login date was {user['lastLogin']}")
            else:

                user_url = user['_meta']['href'].replace("/last-login", "")

                # Get the user data to keep all data the same except for the active parameter
                user_data = bd.get_json(user_url)
                # Skip already inactive users
                if user_data['active'] == False:
                    continue

                # If interactive mode is running, prompt the user before disabling
                if args.interactive:
                    proceed = query_yes_no(f"User '{user['username']}' last login date was {user['lastLogin']}, do you want to mark them as inactive?")
                    if not proceed:
                        logging.info(f"Skipping user '{user['username']}' due to interactive input")
                        continue
                logging.info(f"Marking user '{user['username']}' as inactive")
                deactivate_params = {"userName": user_data['userName'],
                                     "externalUserName": user_data['externalUserName'] if 'externalUserName' in user_data else None,
                                     "firstName": user_data['firstName'],
                                     "lastName": user_data['lastName'],
                                     "email": user_data['email'],
                                     "type": user_data['type'],
                                     "active": False}
                # Deactivate the user
                response = bd.session.put(user_url, json=deactivate_params)
                if response.status_code == 200:
                    logging.info(f"User '{user['username']}' updated successfully")
                elif response.status_code == 404:
                    logging.info(f"User '{user['username']}' 404 Not found")
                else:
                    logging.error(f"Unexpected error updating user '{user['username']}'")
                    bd.http_error_handler(response)
        #Else the user has never logged in
        else:
            logging.warning(f"User '{user['username']}' has never logged in")
