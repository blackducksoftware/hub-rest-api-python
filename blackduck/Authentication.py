'''

Created on Dec 23, 2020
@author: ar-calder

'''
 
import requests
import logging
import json
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class BearerAuth(requests.auth.AuthBase):
    
    from .Exceptions import http_exception_handler

    def __init__(
        self,
        session=None,
        token=None,
        base_url=None,
        verify=True,
        timeout=15,
        ):

        if any(arg == False for arg in (token, base_url)):
            raise ValueError(
                'token & base_url are required'
            )

        self.verify=verify
        self.client_token = token
        self.auth_token = None
        self.csrf_token = None
        self.valid_until = datetime.utcnow()

        self.auth_url = requests.compat.urljoin(base_url, '/api/tokens/authenticate')
        self.session = session or requests.session()
        self.timeout = timeout        


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
        if not self.verify:
            requests.packages.urllib3.disable_warnings()
            # Announce this on every auth attempt, as a little incentive to properly configure certs
            logger.warn("ssl verification disabled, connection insecure. do NOT use verify=False in production!")
            
        try:
            response = self.session.request(
                method='POST',
                url=self.auth_url,
                headers = {
                    "Authorization" : f"token {self.client_token}"
                },
                verify=self.verify,
                timeout=self.timeout
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
        # - no futher details to give.  
        except requests.exceptions.ConnectTimeout as connect_timeout:
            logger.critical(f"could not establish a connection within {self.timeout}s, this may be indicative of proxy misconfiguration")
            raise connect_timeout
        except requests.exceptions.ReadTimeout as read_timeout:
            logger.critical(f"slow or unstable connection, consider increasing timeout (currently set to {self.timeout}s)")
            raise read_timeout
        else:
            logger.info(f"success: auth granted until {self.valid_until} UTC")
