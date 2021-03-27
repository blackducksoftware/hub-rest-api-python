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
import requests
logger = logging.getLogger(__name__)

class Client:
    VERSION_DISTRIBUTION=["EXTERNAL", "SAAS", "INTERNAL", "OPENSOURCE"]
    VERSION_PHASES = ["PLANNING", "DEVELOPMENT", "PRERELEASE", "RELEASED", "DEPRECATED", "ARCHIVED"]
    PROJECT_VERSION_SETTINGS = ['nickname', 'releaseComments', 'versionName', 'phase', 'distribution', 'releasedOn']

    from .Exceptions import(
        http_exception_handler
    )

    from .ClientCore import (
        _request, _get_items, _get_resource_href, get_resource, list_resources, _get_base_resource_url, get_base_resource, _get_parameter_string
    )

    def __init__(
        self,
        *args,
        token=None,
        base_url=None,
        session=None,
        auth=None,
        verify=True,
        timeout=15,
        **kwargs):

        self.verify=verify
        self.timeout=int(timeout)
        self.base_url=base_url
        self.session = session or requests.session()
        self.auth = auth or BearerAuth(
            session = self.session,
            token=token,
            base_url=base_url,
            verify=self.verify
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
