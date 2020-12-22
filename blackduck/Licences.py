import logging
import requests
import json
from operator import itemgetter
import urllib.parse

logger = logging.getLogger(__name__)

def get_licenses(self, parameters={}):
    url = self.get_urlbase() + "/api/licenses" + self._get_parameter_string(parameters)
    response = self.execute_get(url, custom_headers={'Accept':'application/json'})
    json_data = response.json()
    return json_data

def _get_license_info(self, license_obj):
    if 'license' in license_obj:
        license_info = {}
        text_json = {}
        logger.debug("license: {}".format(license_obj))
        response = self.execute_get(license_obj['license'])
        if response.status_code == 200:
            license_info = response.json()
            text_url = self.get_link(license_info, 'text')
            response = self.execute_get(text_url)
            if response.status_code == 200:
                text_json = response.text
        yield {"license_info": license_info,
                "license_text_info": text_json}
    elif 'licenses' in license_obj and isinstance(license_obj['licenses'], list):
        for license in license_obj['licenses']:
            self._get_license_info(license)

def get_license_info_for_bom_component(self, bom_component, limit=1000):
    self._check_version_compatibility()
    all_licenses = {}
    logger.debug("gathering license info for bom component {}, version {}".format(
        bom_component['componentName'], bom_component['componentVersionName']))
    for license in bom_component.get('licenses', []):
        for license_info_obj in self._get_license_info(license):
            all_licenses.update({
                    license['licenseDisplay']: license_info_obj
                })
    return all_licenses


