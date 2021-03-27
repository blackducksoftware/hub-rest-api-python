import logging
import requests
import json
from operator import itemgetter
import urllib.parse

logger = logging.getLogger(__name__)

def add_version_as_component(self, main_project_release, sub_project_release):
    headers = self.get_headers()
    main_data = main_project_release['_meta']['href'].split('/')
    sub_data = sub_project_release['_meta']['href'].split('/')
    main_project_release_links = main_project_release['_meta']['links']
    main_project_release_component_links = [x for x in main_project_release_links if x['rel'] == 'components']
    main_project_release_component_link = main_project_release_component_links[0]['href']
    logger.debug(main_project_release_component_link)
    sub_project_release_as_custom_component_url = self.get_apibase() + "/components/" + sub_data[5] + "/versions/" + sub_data[7]
    logger.debug(sub_project_release_as_custom_component_url)
    payload = {}
    payload['component'] = sub_project_release_as_custom_component_url
    logger.debug(json.dumps(payload))
    response = requests.post(main_project_release_component_link, headers=headers, verify = not self.config['insecure'], json=payload)
    logger.debug(response)
    return response



def remove_version_as_component(self, main_project_release, sub_project_release):
    headers = self.get_headers()
    main_data = main_project_release['_meta']['href'].split('/')
    sub_data = sub_project_release['_meta']['href'].split('/')
    main_project_release_links = main_project_release['_meta']['links']
    main_project_release_component_links = [x for x in main_project_release_links if x['rel'] == 'components']
    main_project_release_component_link = main_project_release_component_links[0]['href']
    logger.debug(main_project_release_component_link)
    subcomponent_url = main_project_release_component_link + "/" + sub_data[5] + "/versions/" + sub_data[7]
    logger.debug(subcomponent_url)
    response = requests.delete(subcomponent_url, headers=headers, verify = not self.config['insecure'])
    return response
