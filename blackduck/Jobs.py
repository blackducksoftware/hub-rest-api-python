import logging
import requests
import json
from operator import itemgetter
import urllib.parse

logger = logging.getLogger(__name__)

def get_jobs(self, parameters={}):
    url = self.get_apibase() + "/jobs"
    url = url + self._get_parameter_string(parameters)
    custom_headers = {'Accept': 'application/vnd.blackducksoftware.status-4+json'}
    response = self.execute_get(url, custom_headers=custom_headers)
    return response.json()

def get_job_statistics(self):
    url = self.get_urlbase() + "/api/job-statistics"
    response = self.execute_get(url)
    return response.json()
    