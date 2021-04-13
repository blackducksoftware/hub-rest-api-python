'''

Created on Dec 22, 2020
@author: ar-calder

'''
import logging
from json import JSONDecodeError
from .Utils import pfmt

logger = logging.getLogger(__name__)

class CreateFailedAlreadyExists(Exception):
    pass

class CreateFailedUnknown(Exception):
    pass

class InvalidVersionPhase(Exception):
    pass

class UnknownVersion(Exception):
    pass

class UnsupportedBDVersion(Exception):
    # Some operations require specific versions of BD
    pass

class EndpointNotFound(Exception):
    pass

class UnacceptableContentType(Exception):
    pass

def http_exception_handler(self, response, name):
    error_codes = {
        404: EndpointNotFound,
        406: UnacceptableContentType
    }

    try:
        content = pfmt(response.json())
    except JSONDecodeError:
        content = response.text

    error = error_codes.get(response.status_code)
    if error:
        raise error(f"(status code {response.status_code}) {name}: {content}")
    raise NotImplementedError(f"No handler for status code: {response.status_code}")
