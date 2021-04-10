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
    except requests.exceptions.ConnectTimeout:
        logger.critical("could not establish a connection; this may be indicative of proxy misconfiguration")
        raise
    except requests.exceptions.ReadTimeout:
        logger.critical("slow or unstable connection, consider increasing timeout")
        raise
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

def _get_base(self, **kwargs):
    """Utility function to provide base(/api/) object.
       Base is root of all other calls, hence the common function.

    Returns:
        dict: api base resource
    """
    return self._request(
            method="GET",
            url="/api/",
            name='_get_base_resource_url',
            **kwargs
    )

def _get_base_resource_url(self, name, public=True, **kwargs):
    """Utility function to get url for a given base(/api/) resouce

    Args:
        name (str)

    Raises:
        KeyError: on key not found

    Returns:
        str: url to named resource
    """
    res = self._get_base(**kwargs).get(name) if public else f"/api/{name}"
    
    if not res:
        raise KeyError(f"'/api/ has no such key '{name}', available keys = {self.list_resources()}")
    return res

def _get_resource_url(self, source, name, public=True):
    """Utility function to get url for a given name

    Args:
        source (dict/json): resource object i.e. project
        name (str): name of api sub-resource i.e. versions
        public (bool): whether the resource is part of the public api
    Raises:
        KeyError: on key not found

    Returns:
        str: url to named resource
    """
    res = f"{self.get_url(source)}/{name}" if not public else find_field(
        data_to_filter=safe_get(source, '_meta', 'links'),
        field_name='rel',
        field_value=name
    )

    if None == res:
        raise KeyError(f"'{self.get_resource_name(source)}' object has no such key '{name}', available keys = {self.list_resources(source)}")
    return safe_get(res, 'href')

def get_resource(self, source=None, name=None, items=True, public=True, **kwargs):
    """Generic function to facilitate subresource fetching  

    Args:
        bd_object (dict/json): [description]
        resource_name (str): [description]
        iterable (bool, optional): [description]. Defaults to True.
        is_public (bool, optional): [description]. Defaults to True.

    Returns:
        dict/json: named resource object
    """
    if None == name:
        raise ValueError("'name' cannot be null")
    if None == source:
        url = self._get_base_resource_url(name, public)
    else:
        url = self._get_resource_url(source, name, public)

    fn = self._get_items if items else self._request
    return fn(
        method='GET',
        url=url,
        name=name,
        **kwargs
    )

def get_metadata(self, source=None, name=None, items=True, public=True, **kwargs):
    """ Generic function to facilitate subresource metadata fetching  

    Args:
        bd_object (dict/json): [description]
        resource_name (str): [description]
        iterable (bool, optional): [description]. Defaults to True.
        is_public (bool, optional): [description]. Defaults to True.

    Returns:
        dict/json: named resource metadata
    """
    if None == name:
        raise ValueError("'name' cannot be null")
    if None == source:
        url = self._get_base_resource_url(name, public)
    else:
        url = self._get_resource_url(source, name, public)

    return self._request(
        method='GET',
        url=url,
        params={'limit':0},
        name=name,
        **kwargs
    )

def list_resources(self, source=None, **kwargs):
    """Utility function to list available subresources

    Optional Args:
        source (dict/json): ..of subresources. Defaults to None / API Base.

    Raises:
        KeyError: on key not found

    Returns:
        list: available *public* resources
    """
    if None==source:
        base = self._get_base(**kwargs)
        return [key for key, value in base.items()]
    return [res.get('rel') for res in safe_get(source, '_meta', 'links')]

def get_parameter_string(self, parameters=list()):
    return '?' + '&'.join(parameters) if parameters else ''
