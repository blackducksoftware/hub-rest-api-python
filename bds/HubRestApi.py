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
import requests
import json

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
            print(self.config)
        
        self.token = self.get_auth_token()
        
        
    def read_config(self):
        with open('.restconfig.json','r') as f:
            self.config = json.load(f)
            
    def write_config(self):
        with open(self.configfile,'w') as f:
            json.dump(self.config, f, indent=3)
               
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
        internalapibase = self.config['baseurl'] + "/api/internal"
        paramstring = "?limit=100&offset=0"
        projectversion = version['_meta']['href'].replace(apibase, '')
        url = internalapibase + projectversion + "/codelocations" + paramstring
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
    
    def get_scanlocations(self):
        url = self.config['baseurl'] + "/api/v1/scanlocations"
        headers = {"Authorization":"Bearer " + self.token}
        response = requests.get(url, headers=headers, verify = not self.config['insecure'])
        jsondata = response.json()
        return jsondata

    def delete_codelocation(self, locationid):
        url = self.config['baseurl'] + "/api/v1/composite/codelocations/" + locationid
        headers = {"Authorization":"Bearer " + self.token}
        response = requests.delete(url, headers=headers, verify = not self.config['insecure'])
        return response

    def execute_delete(self, url):
        headers = {"Authorization":"Bearer " + self.token}
        response = requests.delete(url, headers=headers, verify = not self.config['insecure'])
        return response

        
