import logging
import requests
import json
from operator import itemgetter
import urllib.parse

logger = logging.getLogger(__name__)

def get_health_checks(self):
    url = self.get_urlbase() + "/api/health-checks/liveness"
    return self.execute_get(url)

def get_notifications(self, parameters={}):
    url = self.get_urlbase() + "/api/notifications" + self._get_parameter_string(parameters)
    custom_headers = {'Accept': 'application/vnd.blackducksoftware.notification-4+json'}
    response = self.execute_get(url, custom_headers=custom_headers)
    json_data = response.json()
    return json_data
