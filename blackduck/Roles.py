import logging
import requests
import json
from operator import itemgetter
import urllib.parse

logger = logging.getLogger(__name__)

def _get_role_url(self):
    return self.config['baseurl'] + "/api/roles"

def get_roles(self, parameters={}):
    url = self._get_role_url() + self._get_parameter_string(parameters)
    response = self.execute_get(url)
    return response.json()  

def get_roles_url_from_user_or_group(self, user_or_group):
    # Given a user or user group object, return the 'roles' url
    roles_url = None
    for endpoint in user_or_group['_meta']['links']:
        if endpoint['rel'] == "roles":
            roles_url = endpoint['href']
    return roles_url

def get_roles_for_user_or_group(self, user_or_group):
    roles_url = self.get_roles_url_from_user_or_group(user_or_group)
    if roles_url:
        response = self.execute_get(roles_url)
        return response.json()
    else:
        return []

def get_role_url_by_name(self, role_name):
    # Return the global (as opposed to project-specific) role URL for this server corresponding to the role name
    all_roles = self.get_roles()
    for role in all_roles['items']:
        if role['name'] == role_name:
            return role['_meta']['href']

def assign_role_to_user_or_group(self, role_name, user_or_group):
    user_or_group_roles_url = self.get_roles_url_from_user_or_group(user_or_group)
    return self.assign_role_given_role_url(role_name, user_or_group_roles_url)

def assign_role_given_role_url(self, role_name, user_or_group_role_assignment_url):
    role_url = self.get_role_url_by_name(role_name)
    if self.bd_major_version == "3":
        # A hack to get the assignment to work on v3
        role_url = role_url.replace("api", "api/internal")
    data = {"name": role_name, "role": role_url}
    logger.debug("executing POST to {} with {}".format(
        user_or_group_role_assignment_url, data))
    return self.execute_post(user_or_group_role_assignment_url, data = data)

def delete_role_from_user_or_group(self, role_name, user_or_group):
    roles = self.get_roles_for_user_or_group(user_or_group)
    for role in roles['items']:
        if role['name'] == role_name:
            self.execute_delete(role['_meta']['href'])


def user_has_role(self, user_or_group, role_name):
    user_roles_obj = self.get_roles_for_user_or_group(user_or_group)
    return role_name in [r['name'] for r in user_roles_obj['items']]
