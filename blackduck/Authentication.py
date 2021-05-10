"""
Created on Dec 23, 2020
@author: ar-calder
"""
 
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
    """Authenticate with Blackduck hub using access token"""

    def __init__(self, session, token):
        """
        Args:
            session (requests.session): requests session to authenticate
            token (string): of Blackduck user from UI: System -> My Access Tokens
        """
        if any(arg is False for arg in (session, token)):
            raise ValueError(
                'session & token are required'
            )

        self.session = session
        self.access_token = token
        self.bearer_token = None
        self.csrf_token = None
        self.valid_until = datetime.now()

    def __call__(self, request):
        if not self.bearer_token or datetime.now() > self.valid_until - timedelta(minutes=5):
            # If bearer token not set or nearing expiry
            self.authenticate()

        request.headers.update({ 
            "authorization": f"bearer {self.bearer_token}",
            "X-CSRF-TOKEN": self.csrf_token
        })

        return request

    def authenticate(self):
        if not self.session.verify:
            requests.packages.urllib3.disable_warnings()
            # Announce this on every auth attempt, as a little incentive to properly configure certs
            logger.warning("ssl verification disabled, connection insecure. do NOT use verify=False in production!")

        response = self.session.post(
            url="/api/tokens/authenticate",
            auth=NoAuth(),  # temporarily strip authentication to avoid infinite recursion
            headers={"Authorization": f"token {self.access_token}"}
        )

        if response.status_code == 200:
            try:
                content = response.json()
                self.bearer_token = content['bearerToken']
                self.csrf_token = response.headers['X-CSRF-TOKEN']
                self.valid_until = datetime.now() + timedelta(milliseconds=int(content['expiresInMilliseconds']))
                logger.info(f"success: auth granted until {self.valid_until.astimezone()}")
                return
            except (json.JSONDecodeError, KeyError):
                logger.exception("HTTP response status code 200 but unable to obtain bearer token")
                # fall through

        if response.status_code == 401:
            logger.error("HTTP response status code = 401 (Unauthorized)")
            try:
                logger.error(response.json()['errorMessage'])
            except (json.JSONDecodeError, KeyError):
                logger.exception("unable to extract error message")
                logger.error("HTTP response headers: %s", response.headers)
                logger.error("HTTP response text: %s", response.text)
            raise RuntimeError("Unauthorized access token", response)

        # all unhandled responses fall through to here
        logger.error("Unhandled HTTP response")
        logger.error("HTTP response status code %i", response.status_code)
        logger.error("HTTP response headers: %s", response.headers)
        logger.error("HTTP response text: %s", response.text)
        raise RuntimeError("Unhandled HTTP response", response)


class CookieAuth(AuthBase):
    """Authenticate with Blackduck hub using username/password

       Note: username/password is not recommended and Client users are encouraged
             to use the more secure token authentication instead.
    """

    def __init__(self, session, username, password):
        """
        Args:
            session (requests.session): requests session to authenticate
            username (string): of Blackduck hub user
            password (string): of Blackduck hub user
        """
        if any(arg is False for arg in (session, username, password)):
            raise ValueError(
                'session, username and password are required'
            )

        self.session = session
        self.username = username
        self.password = password
        self.bearer_token = None
        self.csrf_token = None
        self.valid_until = datetime.now()

    def __call__(self, request):
        if not self.bearer_token or datetime.now() > self.valid_until - timedelta(minutes=5):
            # If bearer token not set or nearing expiry
            self.authenticate()

        request.headers.update({ 
            "authorization": f"bearer {self.bearer_token}",
            "X-CSRF-TOKEN": self.csrf_token
        })

        return request

    def authenticate(self):
        logger.warning("Authenticating with username/password is not recommended. Consider using the more secure "
                       "token based authentication instead.")
        if not self.session.verify:
            requests.packages.urllib3.disable_warnings()
            # Announce this on every auth attempt, as a little incentive to properly configure certs
            logger.warning("ssl verification disabled, connection insecure. do NOT use verify=False in production!")

        credentials = {'j_username': self.username, 'j_password': self.password}
        response = self.session.post(
            url="/j_spring_security_check",
            data=credentials,
            auth=NoAuth()  # temporarily strip authentication to avoid infinite recursion
        )

        if response.status_code == 204:  # No Content
            try:
                cookie = response.headers['Set-Cookie']
                self.bearer_token = cookie[cookie.index('=') + 1:cookie.index(';')]
                self.csrf_token = response.headers['X-CSRF-TOKEN']
                # As of 2021.2 the bearer token is good for 2 hours but there
                # is no explicit reference to expiry time in the response.
                #
                # There is internal talk (Feb. 2021) of revamping authentication and the
                # validity time will likely be reduced or the /j_spring_security_check
                # may be deprecated.
                #
                # HUB-25720: It is not possible to extend the validity time
                # of the bearer token obtained via /j_spring_security_check.
                self.valid_until = datetime.now() + timedelta(minutes=120)  # token is good for 2 hours
                logger.info(f"success: auth granted until {self.valid_until.astimezone()}")
                return
            except (KeyError, ValueError):
                logger.exception("HTTP response status code 204 but unable to obtain bearer token")
                # fall through

        if response.status_code == 401:
            logger.error("HTTP response status code = 401 (Unauthorized)")
            try:
                logger.error(response.json()['errorMessage'])
            except (json.JSONDecodeError, KeyError):
                logger.exception("unable to extract error message")
                logger.error("HTTP response headers: %s", response.headers)
                logger.error("HTTP response text: %s", response.text)
            raise RuntimeError("Unauthorized username/password", response)

        # all unhandled responses fall through to here
        logger.error("Unhandled HTTP response")
        logger.error("HTTP response status code %i", response.status_code)
        logger.error("HTTP response headers: %s", response.headers)
        logger.error("HTTP response text: %s", response.text)
        raise RuntimeError("Unhandled HTTP response", response)
