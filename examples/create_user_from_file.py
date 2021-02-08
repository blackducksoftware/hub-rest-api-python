'''
Created on Jan 8, 2020

@author: ylei

Create new users from file (user_list.csv)
"python create_user_from_file.py -f user_list.csv"

CSV File requires 4 columns titled 'username', 'first', 'last', and 'email'
A sample user_list.csv is like below:
username,first,last,email
flast1,first1,last1,flast1@snps.com
flast2,first2,last2,flast2@snps.com
flast3,first3,last3,flast3@snps.com

'''
import argparse
import logging
import sys
import csv

from blackduck.HubRestApi import HubInstance


parser = argparse.ArgumentParser("Create bunch of new users (For example, LDAP users) from file")
parser.add_argument("-f", "--filename", default="user_list.csv", help="File to store user list")

args = parser.parse_args()

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

hub = HubInstance()

filename = args.filename
with open(filename, 'r') as f:
    rows = csv.DictReader(f)
    for row in rows:
        print("Create user: ", row['username'])
        data = {
            "userName" : row['username'],
            "externalUserName" : row['username'],
            "firstName" : row['first'],
            "lastName" : row['last'],
            "email" : row['email'],
            "active" : True,
            "type": "EXTERNAL"
        }
        hub.create_user(data)
