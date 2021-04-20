import logging
import requests
import json
from operator import itemgetter
import urllib.parse

from .Exceptions import UnknownVersion, CreateFailedAlreadyExists, CreateFailedUnknown

logger = logging.getLogger(__name__)

def read_config(self):
    try:
        with open('.restconfig.json','r') as f:
            self.config = json.load(f)
    except:
        logging.error(f"Unable to load configuration from '.restconfig.json'. Make sure you create one with proper connection and authentication values for your Black Duck server")
        raise
        
def write_config(self):
    with open(self.configfile,'w') as f:
        json.dump(self.config, f, indent=3)
        
def get_auth_token(self):
    api_token = self.config.get('api_token', False)
    if api_token:
        authendpoint = "/api/tokens/authenticate"
        url = self.config['baseurl'] + authendpoint
        session = requests.session()
        response = session.post(
            url, 
            data={}, 
            headers={'Authorization': 'token {}'.format(api_token)}, 
            verify=not self.config['insecure']
        )
        csrf_token = response.headers['X-CSRF-TOKEN']
        try:
            bearer_token = json.loads(response.content.decode('utf-8'))['bearerToken']
        except json.decoder.JSONDecodeError as e:
            logger.exception("Authentication failure, could not obtain bearer token")
            raise Exception("Failed to obtain bearer token, check for valid authentication token")
        return (bearer_token, csrf_token, None)
    else:
        authendpoint="/j_spring_security_check"
        url = self.config['baseurl'] + authendpoint
        session=requests.session()
        credentials = dict()
        credentials['j_username'] = self.config['username']
        credentials['j_password'] = self.config['password']
        response = session.post(url, credentials, verify= not self.config['insecure'])
        cookie = response.headers['Set-Cookie']
        token = cookie[cookie.index('=')+1:cookie.index(';')]
    return (token, None, cookie)

def _get_hub_rest_api_version_info(self):
    '''Get the version info from the server, if available
    '''
    session = requests.session()
    url = self.config['baseurl'] + "/api/current-version"
    response = session.get(url, verify = not self.config['insecure'])

    if response.status_code == 200:
        version_info = response.json()
        if 'version' in version_info:
            return version_info
        else:
            raise UnknownVersion("Did not find the 'version' key in the response to a successful GET on /api/current-version")
    else:
        raise UnknownVersion("Failed to retrieve the version info from {}, status code {}".format(url, response.status_code))

def _get_major_version(self):
    return self.version_info['version'].split(".")[0]

def get_urlbase(self):
    return self.config['baseurl']

def get_headers(self):
    if self.config.get('api_token', False):
        return {
            'X-CSRF-TOKEN': self.csrf_token, 
            'Authorization': 'Bearer {}'.format(self.token), 
            'Accept': 'application/json',
            'Content-Type': 'application/json'}
    else:
        if self.bd_major_version == "3":
            return {"Cookie": self.cookie}
        else:
            return {"Authorization":"Bearer " + self.token}

def get_api_version(self):
    url = self.get_urlbase() + '/api/current-version'
    response = self.execute_get(url)
    version = response.json().get('version', 'unknown')
    return version

def _get_parameter_string(self, parameters={}):
    parameter_string = "&".join(["{}={}".format(k,urllib.parse.quote(str(v))) for k,v in sorted(parameters.items(), key=itemgetter(0))])
    return "?" + parameter_string

def get_tags_url(self, component_or_project):
    # Utility method to return the tags URL from either a component or project object
    url = None
    for link_d in component_or_project['_meta']['links']:
        if link_d['rel'] == 'tags':
            return link_d['href']
    return url

def get_link(self, bd_rest_obj, link_name):
    # returns the URL for the link_name OR None
    if bd_rest_obj and '_meta' in bd_rest_obj and 'links' in bd_rest_obj['_meta']:
        for link_obj in bd_rest_obj['_meta']['links']:
            if 'rel' in link_obj and link_obj['rel'] == link_name:
                return link_obj.get('href', None)
    else:
        logger.warning("This does not appear to be a BD REST object. It should have ['_meta']['links']")

def get_limit_paramstring(self, limit):
    return "?limit={}".format(limit)

def get_apibase(self):
    return self.config['baseurl'] + "/api"

def execute_delete(self, url):
    headers = self.get_headers()
    response = requests.delete(url, headers=headers, verify = not self.config['insecure'])
    return response

def _validated_json_data(self, data_to_validate):
    if isinstance(data_to_validate, dict) or isinstance(data_to_validate, list):
        json_data = json.dumps(data_to_validate)
    else:
        json_data = data_to_validate
    json.loads(json_data) # will fail with JSONDecodeError if invalid
    return json_data

def execute_get(self, url, custom_headers={}):
    headers = self.get_headers()
    headers.update(custom_headers)
    response = requests.get(url, headers=headers, verify = not self.config['insecure'])
    return response
    
def execute_put(self, url, data, custom_headers={}):
    json_data = self._validated_json_data(data)
    headers = self.get_headers()
    headers["Content-Type"] = "application/json"
    headers.update(custom_headers)
    response = requests.put(url, headers=headers, data=json_data, verify = not self.config['insecure'])
    return response

def _create(self, url, json_body):
    response = self.execute_post(url, json_body)
    # v4+ returns the newly created location in the response headers
    # and there is nothing in the response json
    # whereas v3 returns the newly created object in the response json
    if response.status_code == 201:
        if "location" in response.headers:
            return response.headers["location"]
        else:
            try:
                response_json = response.json()
            except json.decoder.JSONDecodeError:
                logger.warning('did not receive any json data back')
            else:
                if '_meta' in response_json and 'href' in response_json['_meta']:
                    return response_json['_meta']['href']
                else:
                    return response_json
    elif response.status_code == 412:
        raise CreateFailedAlreadyExists("Failed to create the object because it already exists - url {}, body {}, response {}".format(url, json_body, response))
    else:
        raise CreateFailedUnknown("Failed to create the object for an unknown reason - url {}, body {}, response {}".format(url, json_body, response))

def execute_post(self, url, data, custom_headers={}):
    json_data = self._validated_json_data(data)
    headers = self.get_headers()
    headers["Content-Type"] = "application/json"
    headers.update(custom_headers)
    response = requests.post(url, headers=headers, data=json_data, verify = not self.config['insecure'])
    return response

def get_matched_components(self, version_obj, limit=9999):
    url = "{}/matched-files".format(version_obj['_meta']['href'])
    param_string = self._get_parameter_string({'limit': limit})
    url = "{}{}".format(url, param_string)
    response = self.execute_get(url)
    return response.json()
