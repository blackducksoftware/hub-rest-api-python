'''
Created on Jul 6, 2018

@author: kumykov

Wrapper for common HUB API queries. 
Upon initialization Bearer tocken is obtained and used for all subsequent calls

Usage: 

    from bds_hub_api import HubInstance
    
    username="sysadmin"
    password="blackduck"
    urlbase="https://ec2-34-201-23-208.compute-1.amazonaws.com"
    
    hub = HubInstance(urlbase, username, password, insecure=True)
    
    projects = hub.get_projects()
    
    
'''
import requests

class HubInstance(object):
    '''
    classdocs
    '''


    def __init__(self, baseurl, username, password, insecure=False):
        '''
        Constructor
        '''
        self.username = username
        self.password = password
        self.baseurl = baseurl
        self.insecure = insecure
        requests.packages.urllib3.disable_warnings()
        self.token = self.get_auth_token()
        
    def get_auth_token(self):
        authendpoint="/j_spring_security_check"
        url = self.baseurl + authendpoint
        session=requests.session()
        response = session.post(url, {"j_username" : "sysadmin" , "j_password" : "blackduck"}, verify= not self.insecure)
        cookie = response.headers['Set-Cookie']
        token = cookie[cookie.index('=')+1:cookie.index(';')]
        return token
    
    def get_projects(self):
        url = self.baseurl + "/api/projects"
        headers = {"Authorization":"Bearer " + self.token}
        response = requests.get(url, headers=headers, verify = not self.insecure)
        jsondata = response.json()
        return jsondata

    def get_project_versions(self, project):
        url = project['_meta']['href'] + "/versions"
        headers = {"Authorization":"Bearer " + self.token}
        response = requests.get(url, headers=headers, verify = not self.insecure)
        jsondata = response.json()
        return jsondata
        
    def get_version_components(self, projectversion):
        url = projectversion['_meta']['href'] + "/components"
        headers = {"Authorization":"Bearer " + self.token}
        response = requests.get(url, headers=headers, verify = not self.insecure)
        jsondata = response.json()
        return jsondata
    
    def compare_project_versions(self, version, compareTo):
        apibase = self.baseurl + "/api"
        paramstring = "?limit=1000&sortField=component.securityRiskProfile&ascending=false&offset=0"
        cwhat = version['_meta']['href'].replace(apibase, '')
        cto = compareTo['_meta']['href'].replace(apibase, '')
        url = apibase + cwhat + "/compare" + cto + "/components" + paramstring
        headers = {"Authorization":"Bearer " + self.token}
        response = requests.get(url, headers=headers, verify = not self.insecure)
        jsondata = response.json()
        return jsondata
    
    def get_codelocations(self, version):
        apibase = self.baseurl + "/api"
        internalapibase = self.baseurl + "/api/internal"
        paramstring = "?limit=100&offset=0"
        projectversion = version['_meta']['href'].replace(apibase, '')
        url = internalapibase + projectversion + "/codelocations" + paramstring
        headers = {"Authorization":"Bearer " + self.token}
        response = requests.get(url, headers=headers, verify = not self.insecure)
        jsondata = response.json()
        return jsondata
        
    
    def get_scanlocations(self):
        url = self.baseurl + "/api/v1/scanlocations"
        headers = {"Authorization":"Bearer " + self.token}
        response = requests.get(url, headers=headers, verify = not self.insecure)
        jsondata = response.json()
        return jsondata

    def delete_codelocation(self, locationid):
        url = self.baseurl + "/api/v1/composite/codelocations/" + locationid
        headers = {"Authorization":"Bearer " + self.token}
        response = requests.delete(url, headers=headers, verify = not self.insecure)
        return response

    def execute_delete(self, url):
        headers = {"Authorization":"Bearer " + self.token}
        response = requests.delete(url, headers=headers, verify = not self.insecure)
        return response

        
