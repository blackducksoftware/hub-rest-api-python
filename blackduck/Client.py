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
        _request, _get_items, _get_base_resource_url, _get_base, _get_resource_url, get_resource, list_resources, get_metadata, get_parameter_string
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
        """Instantiate a Client for use with Hub's REST-API

        Args:
            token (str): Access Token obtained from the Hub UI: System -> My Access Tokens
            base_url (str): e.g. "https://your.blackduck.url"
            session (requests.Session): custom session if specified.  For advanced users only.
                If not provided, a HubSession with recommended defaults will be generated and used.
                Any custom session must incorporate a base_url in every request as a plain
                requests.Session() will not work.  See HubSession implementation for an example.
            auth (requests.auth.AuthBase): custom authorization if specified. For advanced users only.
                If not provided, one based on the access token is generated and used.
            verify (bool): TLS certificate verification. Defaults to True.
            timeout (float): request timeout in seconds. Defaults to 15 seconds.
            retries (int): maximum number of times to retry a request. Defaults to 3.
        """
        self.base_url = base_url
        self.session = session or HubSession(base_url, timeout, retries, verify)
        self.session.auth = auth or BearerAuth(session=self.session, token=token)

    def print_methods(self):
        import inspect
        for fn in inspect.getmembers(self, predicate=inspect.ismember):
            print(fn[0])

    def get_project_by_name(self, project_name, **kwargs):
        projects = self.get_resource(name='projects')
        return find_field(projects, 'name', project_name)
