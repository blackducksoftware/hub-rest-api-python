'''
Created on Dec 23, 2020
@author: ar-calder

'''
 
import logging
import requests
import json

from .Utils import find_field, safe_get
logger = logging.getLogger(__name__)

def _request(
    self, 
    method,
    url,
    name='',
    parameters=[],
    **kwargs
    ):
    """[summary]

    Args:
        method ([type]): [description]
        url ([type]): [description]
        name (str, optional): name of the reqested resource. Defaults to ''.

    Raises:
        connect_timeout: often indicative of proxy misconfig
        read_timeout: often indicative of slow connection

    Returns:
        json/dict/list: requested object, json decoded.
    """

    headers = {
        'accept' : 'application/json'
    }
    headers.update(kwargs.pop('headers', dict()))

    if parameters:
        url += self._get_parameter_string(parameters)

    try:
        response = self.session.request(
            method=method, 
            url=url, 
            headers=headers, 
            verify=self.verify, 
            auth=self.auth, 
            **kwargs
        )

        if response.status_code / 100 != 2:
            self.http_exception_handler(
                response=response,
                name=name
            )

        response_json = response.json()

    # Do not handle exceptions - just just more details as to possible causes
    # Thus we do not catch a JsonDecodeError here even though it may occur
    except requests.exceptions.ConnectTimeout as connect_timeout:
        logger.critical(f"could not establish a connection within {self.timeout}s, this may be indicative of proxy misconfiguration")
        raise connect_timeout
    except requests.exceptions.ReadTimeout as read_timeout:
        logger.critical(f"slow or unstable connection, consider increasing timeout (currently set to {self.timeout}s)")
        raise read_timeout
    else:
        return response_json
    
def _get_items(self, url, method='GET', page_size=100, name='', **kwargs):
    """Utility method to get 'pages' of items

    Args:
        url (str): [description]
        method (str, optional): [description]. Defaults to 'GET'.
        page_size (int, optional): [description]. Defaults to 100.
        name (str, optional): [description]. Defaults to ''.

    Yields:
        [type]: [description]
    """
    offset = 0
    params = kwargs.pop('params', dict())
    while True:
        params.update({'offset':f"{offset}", 'limit':f"{page_size}"})
        items = self._request(
            method=method,
            url=url,
            params=params,
            name=name,
            **kwargs
        ).get('items', list())

        for item in items:
            yield item

        if len(items) < page_size:
            # This will be true if there are no more 'pages' to view
            break

        offset += page_size     


def _get_resource_href(self, resources, resource_name):
    """Utility function to get url for a given resource_name

    Args:
        resources (dict/json): [description]
        resource_name (str): [description]

    Raises:
        KeyError: on key not found

    Returns:
        str: url to named resource
    """
    res = find_field(
        data_to_filter=safe_get(resources, '_meta', 'links'),
        field_name='rel',
        field_value=resource_name
    )

    if None == res:
        raise KeyError(f"'{self.get_resource_name(resources)}' object has no such key '{resource_name}'")
    return safe_get(res, 'href')

def get_resource(self, bd_object, resource_name, iterable=True, is_public=True, **kwargs):
    """Generic function to facilitate subresource fetching  

    Args:
        bd_object (dict/json): [description]
        resource_name (str): [description]
        iterable (bool, optional): [description]. Defaults to True.
        is_public (bool, optional): [description]. Defaults to True.

    Returns:
        dict/json: named resource object
    """
    url = self._get_resource_href(resources=bd_object, resource_name=resource_name) if is_public else self.get_url(bd_object) + f"/{resource_name}"
    fn = self._get_items if iterable else self._request
    return fn(
        method='GET',
        url=url,
        name=resource_name,
        **kwargs
    )

def list_resources(self, bd_object):
    return [res.get('rel') for res in safe_get(bd_object, '_meta', 'links')]

def _get_base_resource_url(self, resource_name, is_public=True, **kwargs):
    if is_public:
        resources = self._request(
            method="GET",
            url=self.base_url + f"/api/",
            name='_get_base_resource_url',
            **kwargs
        )
        return resources.get(resource_name, "")
    else:
        return self.base_url + f"/api/{resource_name}"

def get_base_resource(self, resource_name, is_public=True, **kwargs):
    return self._request(
        method='GET',
        url=self._get_base_resource_url(resource_name, is_public=is_public, **kwargs),
        name='get_base_resource',
        **kwargs
    )

def _get_parameter_string(self, parameters=list()):
    return '?' + '&'.join(parameters) if parameters else ''
