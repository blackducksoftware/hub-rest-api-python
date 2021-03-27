import logging
import requests
import json
from operator import itemgetter
import urllib.parse

logger = logging.getLogger(__name__)

def _get_user_group_url(self):
    return self.config['baseurl'] + "/api/usergroups"

def get_user_groups(self, parameters={}):
    url = self._get_user_group_url() + self._get_parameter_string(parameters)
    headers = {'Accept': 'application/vnd.blackducksoftware.user-4+json'}
    response = self.execute_get(url, custom_headers=headers)
    return response.json()

def get_user_group_by_name(self, group_name):
    group_list = self.get_user_groups({"q": f"name:{group_name}"})
    for group in group_list['items']:
        if group['name'] == group_name:
            return group

def create_user_group(self, user_group_json):
    if self.bd_major_version == "3":
        url = self.config['baseurl'] + '/api/v1/usergroups'
    else:
        url = self._get_user_group_url()
    location = self._create(url, user_group_json)
    return location

def create_user_group_by_name(self, group_name, active=True):
    user_group_info = {
        'name': group_name,
        'createdFrom': 'INTERNAL',
        'active': active
    }
    return self.create_user_group(user_group_info)

# def get_user_group_by_id(self, user_group_id):
#     url = self._get_user_group_url() + "/{}".format(user_group_id)
#     return self.get_user_group_by_url(url)

# def get_user_group_by_url(self, user_group_url):
#     response = self.execute_get(user_group_url)
#     jsondata = response.json()
#     return jsondata

# def get_user_group_by_name(self, user_group_name):
#     url = self._get_user_group_url() + "?q={}".format(user_group_name)
#     response = self.execute_get(url)
#     user_group_obj = response.json()
#     if user_group_obj['totalCount'] > 0:
#         return user_group_obj['items'][0]

def update_user_group_by_id(self, user_group_id, update_json):
    url = self._get_user_group_url() + "/{}".format(user_group_id)
    return self.update_user_group_by_url(url, update_json)

def update_user_group_by_url(self, user_group_url, update_json):
    return self.execute_put(user_group_url, update_json)

def delete_user_group_by_id(self, user_group_id):
    url = self._get_user_group_url() + "/{}".format(user_group_id)
    return self.delete_user_group_by_url(url)

def delete_user_group_by_url(self, user_group_url):
    return self.execute_delete(user_group_url)
