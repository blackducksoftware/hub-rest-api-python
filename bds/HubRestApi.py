'''
Created on Jul 6, 2018

@author: kumykov

Wrapper for common HUB API queries. 
Upon initialization Bearer tocken is obtained and used for all subsequent calls

Usage: 

credentials and hub URL could be placed in the .restconfig.json file
    
    {
      "baseurl": "https://ec2-18-208-209-223.compute-1.amazonaws.com",
      "username": "sysadmin",
      "password": "genesys",
      "insecure": true,
      "debug": false
    }

    .restconfig.json should be present in the current directory.
    
    from bds_hub_api import HubInstance
    
    hub = HubInstance()
    projects = hub.get_projects()

It is possible to generate generate_config file by initalizing API as following:
   
    from bds_hub_api import HubInstance
    
    username="sysadmin"
    password="blackduck"
    urlbase="https://ec2-34-201-23-208.compute-1.amazonaws.com"
    
    hub = HubInstance(urlbase, username, password, insecure=True)
    
    
'''
import logging
import requests
import json

class CreateFailedAlreadyExists(Exception):
    pass

class CreateFailedUnknown(Exception):
    pass

class HubInstance(object):
    '''
    classdocs
    '''
    configfile = ".restconfig.json"
    config = dict()

    def __init__(self, *args, **kwargs):
        
        try:
            self.config['baseurl'] = args[0]
            self.config['username'] = args[1]
            self.config['password'] = args[2]
            self.config['insecure'] = kwargs.get('insecure', False)
            self.config['debug'] = kwargs.get('insecure', False)
            self.write_config()
        except Exception:
            self.read_config()
            
        if self.config['insecure']:
            requests.packages.urllib3.disable_warnings()
        
        if self.config['debug']:
            print(self.configfile)
        
        self.token = self.get_auth_token()
        
        
    def read_config(self):
        with open('.restconfig.json','r') as f:
            self.config = json.load(f)
            
    def write_config(self):
        with open(self.configfile,'w') as f:
            json.dump(self.config, f, indent=3)
               
    def create_policy(self, policy_json):
        url = self.config["baseurl"] + "/api/policy-rules"
        location = self._create(url, policy_json)
        return location

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
        logging.debug("Finding the Hub componet for Protex component id {}, release id {} using query/url {}".format(
            protex_component_id, protex_component_release_id, with_query))
        response = self.execute_get(with_query)
        logging.debug("query results in status code {}, json data: {}".format(response.status_code, response.json()))
        # TODO: Error checking and retry? For now, as POC just assuming it worked
        component_list_d = response.json()
        if component_list_d['totalCount'] == 1:
            return component_list_d['items'][0]
        else:
            return component_list_d['items']

    def get_auth_token(self):
        authendpoint="/j_spring_security_check"
        url = self.config['baseurl'] + authendpoint
        session=requests.session()
        credentials = dict()
        credentials['j_username'] = self.config['username']
        credentials['j_password'] = self.config['password']
        response = session.post(url, credentials, verify= not self.config['insecure'])
        cookie = response.headers['Set-Cookie']
        token = cookie[cookie.index('=')+1:cookie.index(';')]
        return token
    
    def get_urlbase(self):
        return self.config['baseurl']
    
    def get_projects(self, limit=100):
        headers = {"Authorization":"Bearer " + self.token}
        paramstring = "?limit={}".format(limit)
        url = self.config['baseurl'] + "/api/projects" + paramstring
        print (url)
        response = requests.get(url, headers=headers, verify = not self.config['insecure'])
        jsondata = response.json()
        return jsondata

    def get_project_by_id(self, project_id, limit=100):
        headers = {"Authorization":"Bearer " + self.token}
        paramstring = "?limit={}".format(limit)
        url = self.config['baseurl'] + "/api/projects/" + project_id + paramstring
        response = requests.get(url, headers=headers, verify = not self.config['insecure'])
        jsondata = response.json()
        return jsondata

    def get_project_versions(self, project, limit=100):
        paramstring = "?limit={}".format(limit)
        url = project['_meta']['href'] + "/versions" + paramstring
        headers = {"Authorization":"Bearer " + self.token}
        response = requests.get(url, headers=headers, verify = not self.config['insecure'])
        jsondata = response.json()
        return jsondata
        
    def get_version_components(self, projectversion, limit=1000):
        paramstring = "?limit={}".format(limit)
        url = projectversion['_meta']['href'] + "/components" + paramstring
        headers = {"Authorization":"Bearer " + self.token}
        response = requests.get(url, headers=headers, verify = not self.config['insecure'])
        jsondata = response.json()
        return jsondata
    
    def compare_project_versions(self, version, compareTo):
        apibase = self.config['baseurl'] + "/api"
        paramstring = "?limit=1000&sortField=component.securityRiskProfile&ascending=false&offset=0"
        cwhat = version['_meta']['href'].replace(apibase, '')
        cto = compareTo['_meta']['href'].replace(apibase, '')
        url = apibase + cwhat + "/compare" + cto + "/components" + paramstring
        headers = {"Authorization":"Bearer " + self.token}
        response = requests.get(url, headers=headers, verify = not self.config['insecure'])
        jsondata = response.json()
        return jsondata
    
    def get_version_codelocations(self, version, limit=100):
        apibase = self.config['baseurl'] + "/api"
        paramstring = "?limit=100&offset=0"
        projectversion = version['_meta']['href']
        url = projectversion + "/codelocations" + paramstring
        headers = {"Authorization":"Bearer " + self.token}
        response = requests.get(url, headers=headers, verify = not self.config['insecure'])
        jsondata = response.json()
        return jsondata
        
    def get_codelocations(self, limit=100):
        apibase = self.config['baseurl'] + "/api"
        paramstring = "?limit={}&offset=0".format(limit)
        url = apibase + "/codelocations" + paramstring
        headers = {"Authorization":"Bearer " + self.token}
        response = requests.get(url, headers=headers, verify = not self.config['insecure'])
        jsondata = response.json()
        return jsondata
    
    def get_component_by_id(self, component_id):
        url = self.config['baseurl'] + "/api/components/{}".format(component_id)
        return self.get_component_by_url(url)

    def get_component_by_url(self, component_url):
        response = self.execute_get(component_url)
        jsondata = response.json()
        return jsondata

    def get_scanlocations(self):
        url = self.config['baseurl'] + "/api/v1/scanlocations"
        headers = {"Authorization":"Bearer " + self.token}
        response = requests.get(url, headers=headers, verify = not self.config['insecure'])
        jsondata = response.json()
        return jsondata

    def update_component_by_id(self, component_id, update_json):
        url = self.config["baseurl"] + "/api/components/{}".format(component_id)
        return self.update_component_by_url(url, update_json)

    def update_component_by_url(self, component_url, update_json):
        return self.execute_put(component_url, update_json)

    def delete_codelocation(self, locationid):
        url = self.config['baseurl'] + "/api/codelocations/" + locationid
        headers = {"Authorization":"Bearer " + self.token}
        response = requests.delete(url, headers=headers, verify = not self.config['insecure'])
        return response

    def execute_delete(self, url):
        headers = {"Authorization":"Bearer " + self.token}
        response = requests.delete(url, headers=headers, verify = not self.config['insecure'])
        return response

    def execute_get(self, url):
        headers = {"Authorization":"Bearer " + self.token}
        response = requests.get(url, headers=headers, verify = not self.config['insecure'])
        return response
        
    def _validated_json_data(self, data_to_validate):
        if isinstance(data_to_validate, dict):
            json_data = json.dumps(data_to_validate)
        else:
            json_data = data_to_validate
        return json_data

    def execute_put(self, url, data):
        data = self._validated_json_data(data)
        headers = {"Authorization":"Bearer " + self.token, "Content-Type": "application/json"}
        response = requests.put(url, headers=headers, data=data, verify = not self.config['insecure'])
        return response

    def _create(self, url, json_body):
        response = self.execute_post(url, json_body)
        if response.status_code == 201 and "location" in response.headers:
            return (response.headers["location"])
        elif response.status_code == 412:
            raise CreateFailedAlreadyExists("Failed to create the object because it already exists - url {}, body {}, response {}".format(url, json_body, response))
        else:
            raise CreateFailedUnknown("Failed to create the object for an unknown reason - url {}, body {}, response {}".format(url, json_body, response))

    def execute_post(self, url, data):
        data = self._validated_json_data(data)
        headers = {"Authorization":"Bearer " + self.token, "Content-Type": "application/json"}
        response = requests.post(url, headers=headers, data=data, verify = not self.config['insecure'])
        return response








