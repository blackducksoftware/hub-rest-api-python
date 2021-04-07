'''
Created on Dec 23, 2020
@author: ar-calder

Wrapper for common HUB API queries. 
Upon initialization Bearer token is obtained and used for all subsequent calls.
Token will auto-renew on timeout.
'''

from .Utils import find_field, safe_get
from .Authentication import BearerAuth
import logging
import os
import requests.packages.urllib3
from requests.packages.urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from urllib.parse import urljoin

logger = logging.getLogger(__name__)


class HubSession(requests.Session):
    """Hold base_url, timeout, retries, and provide sensible defaults"""

    def __init__(self, base_url, timeout, retries, verify):
        super().__init__()
        self.base_url = base_url
        self._timeout = float(timeout)  # timeout is not a member of requests.Session
        self.verify = verify

        # use sane defaults to handle unreliable networks
        """HTTP response status codes:
                429 = Too Many Requests
                500 = Internal Server Error
                502 = Bad Gateway
                503 = Service Unavailable
                504 = Gateway Timeout
        """
        retry_strategy = Retry(
            total=int(retries),
            backoff_factor=2,  # exponential retry 1, 2, 4, 8, 16 sec ...
            status_forcelist=[429, 500, 502, 503, 504],
            method_whitelist=['GET']
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.mount("https://", adapter)
        self.mount("http://", adapter)
        logging.info("Using a session with a %s second timeout and up to %s retries per request", timeout, retries)

        self.proxies.update({
            'http': os.environ.get('http_proxy', ''),
            'https': os.environ.get('https_proxy', '')
        })

    def request(self, method, url, **kwargs):
        kwargs['timeout'] = self._timeout
        url = urljoin(self.base_url, url)
        return super().request(method, url, **kwargs)


class Client:
    '''
    classdocs
    '''
    from .constants import VERSION_DISTRIBUTION, VERSION_PHASES, PROJECT_VERSION_SETTINGS

    from .Exceptions import(
        http_exception_handler
    )

    from .ClientCore import (
        _request, _get_items, _get_resource_href, get_resource, list_resources, _get_base_resource_url, get_base_resource, _get_parameter_string
    )

    def __init__(
        self,
        token=None,
        base_url=None,
        session=None,
        auth=None,
        verify=True,
        timeout=15.0,  # in seconds
        retries=3):

        self.base_url=base_url
        self.session = session or HubSession(base_url, timeout, retries, verify)
        self.auth = auth or BearerAuth(
            session = self.session,
            token=token
        )

    def print_methods(self):
        import inspect
        for fn in inspect.getmembers(self, predicate=inspect.ismember):
            print(fn[0])

    # Example for projects
    def get_projects(self, parameters=[], **kwargs):
        return self._get_items(
            method='GET',
            # url unlikely to change hence is_public=false (faster).
            url= self._get_base_resource_url('projects', is_public=False),
            name="project",
            **kwargs
        )

    def get_project_by_name(self, project_name, **kwargs):
        projects = self.get_projects(**kwargs)
        return find_field(projects, 'name', project_name)
