import logging
import requests
import json
from operator import itemgetter
import urllib.parse

logger = logging.getLogger(__name__)

def _get_policy_url(self):
    return self.config['baseurl'] + "/api/policy-rules"

def get_policies(self, parameters={}):
    url = self._get_policy_url() + self._get_parameter_string(parameters)
    headers = {'Accept': 'application/json'}
    response = self.execute_get(url, custom_headers=headers)
    return response.json()

def create_policy(self, policy_json):
    url = self._get_policy_url()
    location = self._create(url, policy_json)
    return location

def get_policy_by_id(self, policy_id):
    url = self._get_policy_url() + "/{}".format(policy_id)
    return self.get_policy_by_url(url)

def get_policy_by_url(self, policy_url):
    headers = {'Accept': 'application/vnd.blackducksoftware.policy-4+json'}
    response = self.execute_get(policy_url, custom_headers=headers)
    jsondata = response.json()
    return jsondata

def update_policy_by_id(self, policy_id, update_json):
    url = self._get_policy_url() + "/{}".format(policy_id)
    return self.update_policy_by_url(url, update_json)

def update_policy_by_url(self, policy_url, update_json):
    return self.execute_put(policy_url, update_json)

def delete_policy_by_id(self, policy_id):
    url = self._get_policy_url() + "/{}".format(policy_id)
    return self.delete_policy_by_url(url)

def delete_policy_by_url(self, policy_url):
    return self.execute_delete(policy_url)
