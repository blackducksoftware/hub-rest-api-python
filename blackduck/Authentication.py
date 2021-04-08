'''

Created on Dec 23, 2020
@author: ar-calder

'''
 
import requests
from requests.auth import AuthBase
import logging
import json
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class NoAuth(AuthBase):
    def __call__(self, r):
        return r


class BearerAuth(AuthBase):
    
    from .Exceptions import http_exception_handler

    def __init__(self, session=None, token=None):
        if any(arg is False for arg in (session, token)):
            raise ValueError(
                'session & token are required'
            )

        self.client_token = token
        self.auth_token = None
        self.csrf_token = None
        self.valid_until = datetime.utcnow()

        self.session = session

    def __call__(self, request):
        if not self.auth_token or self.valid_until < datetime.utcnow():
            # If authentication token not set or no longer valid
            self.authenticate()

        request.headers.update({ 
            "authorization" : f"bearer {self.auth_token}",
            "X-CSRF-TOKEN" : self.csrf_token
        })

        return request

    def authenticate(self):
        if not self.session.verify:
            requests.packages.urllib3.disable_warnings()
            # Announce this on every auth attempt, as a little incentive to properly configure certs
            logger.warn("ssl verification disabled, connection insecure. do NOT use verify=False in production!")
            
        try:
            response = self.session.request(
                method='POST',
                url="/api/tokens/authenticate",
                auth=NoAuth(),  # temporarily strip authentication to avoid infinite recursion
                headers={"Authorization": f"token {self.client_token}"}
            )

            if response.status_code / 100 != 2:
                self.http_exception_handler(
                    response=response,
                    name="authenticate"
                )

            content = response.json()
            self.csrf_token = response.headers.get('X-CSRF-TOKEN')
            self.auth_token = content.get('bearerToken')
            self.valid_until = datetime.utcnow() + timedelta(milliseconds=int(content.get('expiresInMilliseconds', 0)))

        # Do not handle exceptions - just just more details as to possible causes
        # Thus we do not catch a JsonDecodeError here even though it may occur
        # - no further details to give.
        except requests.exceptions.ConnectTimeout:
            logger.critical("could not establish a connection; this may be indicative of proxy misconfiguration")
            raise
        except requests.exceptions.ReadTimeout:
            logger.critical("slow or unstable connection, consider increasing timeout")
            raise
        else:
            logger.info(f"success: auth granted until {self.valid_until} UTC")
