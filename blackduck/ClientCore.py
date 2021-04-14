'''
Created on Dec 23, 2020
@author: ar-calder

'''
 
import logging
import requests

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
        'accept': 'application/json',
        'content-type': 'application/json'
    }
    headers.update(kwargs.pop('headers', dict()))

    if parameters:
        url += self.get_parameter_string(parameters)

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

        if 'Content-Type' in response.headers and 'internal' in response.headers['Content-Type']:
            logging.warning("Response contains internal proprietary Content-Type: " + response.headers['Content-Type'])

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
        generator(dict/json): of items
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

def get_parameter_string(self, parameters=list()):
    return '?' + '&'.join(parameters) if parameters else ''
