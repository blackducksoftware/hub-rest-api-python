import logging
import requests
import json
from operator import itemgetter
import urllib.parse

logger = logging.getLogger(__name__)

def find_component_info_for_protex_component(self, protex_component_id, protex_component_release_id):
    '''Will return the Hub component corresponding to the protex_component_id, and if a release (version) id
    is given, the response will also include the component-version. Returns an empty list if there were
    no components found.
    '''
    url = self.config['baseurl'] + "/api/components"
    if protex_component_release_id:
        query = "?q=bdsuite:{}%23{}&limit=9999".format(protex_component_id, protex_component_release_id)
    else:
        query = "?q=bdsuite:{}&limit=9999".format(protex_component_id)
    with_query = url + query
    logger.debug("Finding the Hub componet for Protex component id {}, release id {} using query/url {}".format(
        protex_component_id, protex_component_release_id, with_query))
    response = self.execute_get(with_query)
    logger.debug("query results in status code {}, json data: {}".format(response.status_code, response.json()))
    # TODO: Error checking and retry? For now, as POC just assuming it worked
    component_list_d = response.json()
    return response.json()

def _get_components_url(self):
    return self.get_urlbase() + "/api/components"

def get_components(self, limit=100, parameters={}):
    if limit:
        parameters.update({'limit':limit})
    #
    # I was only able to GET components when using this internal media type which is how the GUI works
    #       July 19, 2019 Glenn Snyder
    #
    custom_headers = {'Accept':'application/vnd.blackducksoftware.internal-1+json'}
    url = self._get_components_url() + self._get_parameter_string(parameters)
    response = self.execute_get(url, custom_headers=custom_headers)
    return response.json()

def search_components(self, search_str_or_query, limit=100, parameters={}):
    if limit:
        parameters.update({'limit':limit})
    if search_str_or_query.startswith("q="):
        # allow caller to override original behavior with their own query
        query = search_str_or_query
    else:
        # maintain original, somewhat flawed behavior
        query = "q=name:{}".format(search_str_or_query)
    parm_str = self._get_parameter_string(parameters)
    url = self.get_apibase() + "/search/components{}&{}".format(parm_str, query)
    response = self.execute_get(url)
    return response.json()
    
def get_component_by_id(self, component_id):
    url = self.config['baseurl'] + "/api/components/{}".format(component_id)
    return self.get_component_by_url(url)

def get_component_by_url(self, component_url):
    headers = self.get_headers()
    response = self.execute_get(component_url)
    jsondata = response.json()
    return jsondata

def update_component_by_id(self, component_id, update_json):
    url = self.config["baseurl"] + "/api/components/{}".format(component_id)
    return self.update_component_by_url(url, update_json)

def update_component_by_url(self, component_url, update_json):
    return self.execute_put(component_url, update_json)
