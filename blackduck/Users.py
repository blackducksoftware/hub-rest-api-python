import logging
import requests
import json
from operator import itemgetter
import urllib.parse

logger = logging.getLogger(__name__)

def _get_user_url(self):
    return self.config['baseurl'] + "/api/users"

def get_users(self, parameters={}):
    url = self._get_user_url() + self._get_parameter_string(parameters)
    headers = {'Accept': 'application/vnd.blackducksoftware.user-4+json'}
    response = self.execute_get(url, custom_headers=headers)
    return response.json()

def get_current_user(self):
    url = self.config['baseurl'] + "/api/current-user"
    headers = {'Accept': 'application/vnd.blackducksoftware.user-4+json'}
    response = self.execute_get(url, custom_headers=headers)
    return response.json()

def create_user(self, user_json):
    url = self._get_user_url()
    location = self._create(url, user_json)
    return location

def get_user_by_id(self, user_id):
    url = self._get_user_url() + "/{}".format(user_id)
    headers = {'Accept': 'application/vnd.blackducksoftware.user-4+json'}
    return self.get_user_by_url(url, custom_headers=headers)

def get_user_by_url(self, user_url):
    headers = {'Accept': 'application/vnd.blackducksoftware.user-4+json'}
    response = self.execute_get(user_url, custom_headers=headers)
    jsondata = response.json()
    return jsondata

def update_user_by_id(self, user_id, update_json):
    url = self._get_user_url() + "/{}".format(user_id)
    return self.update_user_by_url(url, update_json)

def update_user_by_url(self, user_url, update_json):
    return self.execute_put(user_url, update_json)

def delete_user_by_id(self, user_id):
    url = self._get_user_url() + "/{}".format(user_id)
    return self.delete_user_by_url(url)

def delete_user_by_url(self, user_url):
    return self.execute_delete(user_url)
    
def reset_user_password(self, user_id, new_password):
    url = self.config['baseurl'] + "/api/users/" + user_id + "/resetpassword"
    headers = {'Content-Type':'application/vnd.blackducksoftware.user-1+json', 'Accept': 'application/json'}
    data = {'password': new_password}
    return self.execute_put(url, data, headers)

def get_last_login(self,sinceDays=60):
    url = self.config['baseurl'] + "/api/dormant-users"
    param_string = self._get_parameter_string({'sinceDays': sinceDays})
    url = "{}{}".format(url, param_string)
    headers = {'Accept': 'application/vnd.blackducksoftware.user-4+json'}
    response = self.execute_get(url, custom_headers=headers)
    return response.json()
