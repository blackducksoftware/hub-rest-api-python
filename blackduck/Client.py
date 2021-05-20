"""
Created on Dec 23, 2020
@author: ar-calder

Wrapper for common HUB API queries. 
Upon initialization Bearer token is obtained and used for all subsequent calls.
Token will auto-renew on timeout.
"""

from .Utils import safe_get
from .Authentication import BearerAuth
import json
import logging
import os
from pprint import pformat
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
        logger.info("Using a session with a %s second timeout and up to %s retries per request", timeout, retries)

        self.proxies.update({
            'http': os.environ.get('http_proxy', ''),
            'https': os.environ.get('https_proxy', '')
        })

    def request(self, method, url, **kwargs):
        kwargs['timeout'] = self._timeout

        if method.lower() == 'get':
            headers = kwargs.pop('headers', dict())
            lc_keys = {key.lower(): value for (key, value) in headers.items()}
            if 'accept' not in lc_keys and 'content-type' not in lc_keys:
                # set default media type only if neither 'accept' nor 'content-type'
                # exist as some endpoints may only accept one or the other but not both
                lc_keys['accept'] = "application/json"
                lc_keys['content-type'] = "application/json"
            kwargs['headers'] = lc_keys

        url = urljoin(self.base_url, url)
        return super().request(method, url, **kwargs)


class Client:
    """A binding to Blackduck's REST API that provides a robust connection backed by a session object.
    A base URL, timeout, retries, proxies, and TLS verification are set upon initialization and these
    attributes are persisted across all requests.

    At the REST API level, it provides a consistent way to discover and traverse public resources,
    uses a generator to fetch all items using pagination, and automatically renews the bearer token.

    Ultimately it provides a solid foundation especially suited for long-running scripts.
    """
    def __init__(self,
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
        self.session.auth = auth or BearerAuth(self.session, token)
        self.root_resources_dict = None

    def list_resources(self, parent=None):
        """List named resources that can be fetched.

        Args:
            parent (dict/json): resource object from prior get_resource invocations.
                                Defaults to None (for root /api/ base).

        Returns:
            dict(str -> str): of public resource names to urls
                              To obtain the url to the parent itself, use key 'href'.
        """
        if parent is not None and not isinstance(parent, dict):
            raise TypeError("parent parameter must be a dict if not None")

        if not parent:
            # the root resources are in a different format (name -> href)
            # compared to (rel, href) pairs in _meta.links
            if self.root_resources_dict is None:
                # cache root resources for efficiency
                resp = self.session.get("/api/")
                resources_dict = resp.json()
                resources_dict['href'] = resp.url  # save url to root itself
                del resources_dict['_meta']
                self.root_resources_dict = resources_dict
            return self.root_resources_dict
        else:
            key = '_hub_rest_api_python_resources_dict'
            if key not in parent:
                obj = safe_get(parent, '_meta', 'links')
                try:
                    rel_href_pairs = iter(obj)
                except TypeError:
                    logger.error("unable to list resources on parent object (missing ['_meta']['links']):")
                    logger.error(pformat(parent))
                    raise
                resources_dict = {}
                for res in rel_href_pairs:
                    resources_dict[res['rel']] = res['href']
                # save url to parent itself if available, otherwise save 'href': None
                resources_dict['href'] = safe_get(parent, '_meta', 'href')
                parent[key] = resources_dict  # cache for future use
            return parent[key]

    def get_resource(self, name, parent=None, items=True, **kwargs):
        """Fetch a named resource.

        Args:
            name (str): resource name i.e. specific key from list_resources()
            parent (dict/json): resource object from prior get_resource() call.
                                Use None for root /api/ base.
            items (bool): enable resource generator for paginated results. Defaults to True.
            kwargs: passed to session.request

        Returns:
            list (items=True) or dict formed from returned json
        """
        if not isinstance(name, str) or not name:
            raise TypeError("name parameter must be a non-empty str")
        if parent is not None and not isinstance(parent, dict):
            raise TypeError("parent parameter must be a dict if not None")

        resources_dict = self.list_resources(parent)
        if name not in resources_dict:
            msg = f"resource name '{name}' not found in available resources"
            logger.error(msg)
            logger.error(pformat(resources_dict))
            raise KeyError(msg)
        url = resources_dict[name]

        if items:
            return self.get_items(url, **kwargs)
        else:
            return self.get_json(url, **kwargs)

    def get_metadata(self, name, parent=None, **kwargs):
        """Fetch named resource metadata and other useful data such as totalCount.

        Args:
            name (str): resource name i.e. specific key from list_resources()
            parent (dict/json): resource object from prior get_resource() call.
                                Use None for root /api/ base.
            kwargs: passed to session.request

        Returns:
            dict/json: named resource metadata
        """
        # limit: 0 works for 'projects' but not for 'codeLocations' or project 'versions'
        kwargs['params'] = {'limit': 1}
        return self.get_resource(name, parent, items=False, **kwargs)

    def get_json(self, url, **kwargs):
        """Streamline GET request to url endpoint and return json result
           while preserving underlying error handling.

        Args:
            url (str): of endpoint
            kwargs: passed to session.request

        Returns:
            json/dict: requested object

        Raises:
            requests.exceptions.HTTPError: from response.raise_for_status()
            json.JSONDecodeError: if response.text is not json
        """
        r = self.session.get(url, **kwargs)

        if r.status_code != 200:
            # print out a more descriptive error message before raising an exception
            self.http_error_handler(r)

        r.raise_for_status()

        if 'Content-Type' in r.headers:
            content_type = r.headers['Content-Type']
            if 'internal' in content_type:
                logger.warning("Response contains internal proprietary Content-Type: " + content_type)

        try:
            return r.json()
        except json.JSONDecodeError:
            self.http_error_handler(r)
            raise

    def get_items(self, url, page_size=250, **kwargs):
        """Fetch 'pages' of items

        Args:
            url (str): of endpoint
            page_size (int): Number of items to get per page. Defaults to 250.
            kwargs: passed to session.request

        Yields:
            generator(dict/json): of items
        """
        offset = 0
        params = kwargs.pop('params', dict())

        while True:
            params.update({'offset': f"{offset}", 'limit': f"{page_size}"})
            kwargs['params'] = params
            items = self.get_json(url, **kwargs).get('items', list())

            for item in items:
                yield item

            if len(items) < page_size:
                # This will be true if there are no more 'pages' to view
                break

            offset += page_size

    @staticmethod
    def http_error_handler(r):
        """Handle an unexpected HTTPError or Response by logging useful information.

        Args:
            r (requests.HTTPError OR requests.Response): to handle
        """
        if isinstance(r, requests.HTTPError):
            r = r.response
        logger.error(f"{r.request.method} {r.url}")
        status_description = requests.status_codes._codes[r.status_code][0]
        logger.error(f"HTTP response status code {r.status_code}: {status_description}")
        try:
            content = json.dumps(r.json(), indent=4)
            logger.error(f"HTTP response json (formatted): {content}")
        except json.JSONDecodeError:
            logger.error(f"HTTP response text: {r.text}")
