import logging
import requests
import json
from operator import itemgetter
import urllib.parse

logger = logging.getLogger(__name__)

def _get_vulnerabilities_url(self):
    return self.config['baseurl'] + '/api/vulnerabilities'

def get_vulnerabilities(self, vulnerability, parameters={}):
    url = self._get_vulnerabilities_url() + "/{}".format(vulnerability) + self._get_parameter_string(parameters)
    headers = {'Accept': 'application/vnd.blackducksoftware.vulnerability-4+json'}
    response = self.execute_get(url, custom_headers=headers)
    return response.json()

def get_vulnerability_affected_projects(self, vulnerability):
    url = self._get_vulnerabilities_url() + "/{}/affected-projects".format(vulnerability) 
    custom_headers = {'Accept': 'application/vnd.blackducksoftware.vulnerability-4+json'}
    response = self.execute_get(url, custom_headers=custom_headers)
    return response.json()

# TODO: Refactor this, i.e. use get_link method?
def get_vulnerable_bom_components(self, version_obj, limit=9999):
    url = "{}/vulnerable-bom-components".format(version_obj['_meta']['href'])
    custom_headers = {'Accept': 'application/vnd.blackducksoftware.bill-of-materials-6+json'}
    param_string = self._get_parameter_string({'limit': limit})
    url = "{}{}".format(url, param_string)
    response = self.execute_get(url, custom_headers=custom_headers)
    return response.json()

# TODO: Remove or refactor this
def get_component_remediation(self, bom_component):
    url = "{}/remediating".format(bom_component['componentVersion'])
    logger.debug("Url for getting remediation info is : {}".format(url))
    response = self.execute_get(url)
    return response.json()
