import logging
import requests
import json
from operator import itemgetter
import urllib.parse

logger = logging.getLogger(__name__)

def get_ldap_state(self):
    url = self.config['baseurl'] + "/api/v1/ldap/state"
    headers = self.get_headers()
    response = requests.get(url, headers=headers, verify = not self.config['insecure'])
    jsondata = response.json()
    return jsondata

def enable_ldap(self):
    url = self.config['baseurl'] + "/api/v1/ldap/state"
    headers = self.get_headers()
    payload = {}
    payload['ldapEnabled'] = True
    response = requests.post(url, headers=headers, verify = not self.config['insecure'], json=payload)
    jsondata = response.json()
    return jsondata
    
def disable_ldap(self):
    url = self.config['baseurl'] + "/api/v1/ldap/state"
    headers = self.get_headers()
    payload = {}
    payload['ldapEnabled'] = False
    response = requests.post(url, headers=headers, verify = not self.config['insecure'], json=payload)
    jsondata = response.json()
    return jsondata
    
def get_ldap_configs(self):
    url = self.config['baseurl'] + "/api/v1/ldap/configs"
    headers = self.get_headers()
    headers['Content-Type']  = "application/json"
    response = requests.get(url, headers=headers, verify = not self.config['insecure'])
    jsondata = response.json()
    return jsondata