import logging
import requests
import json
from operator import itemgetter
import urllib.parse

logger = logging.getLogger(__name__)

def upload_scan(self, filename):
    url = self.get_apibase() + "/scan/data/?mode=replace"
    headers = self.get_headers()
    if filename.endswith('.json') or filename.endswith('.jsonld'):
        headers['Content-Type'] = 'application/ld+json'
        with open(filename,"r") as f:
            response = requests.post(url, headers=headers, data=f, verify=not self.config['insecure'])
    elif filename.endswith('.bdio'):
        headers['Content-Type'] = 'application/vnd.blackducksoftware.bdio+zip'
        with open(filename,"rb") as f:
            response = requests.post(url, headers=headers, data=f, verify=not self.config['insecure'])
    else:
        raise Exception("Unkown file type")
    return response

def download_project_scans(self, project_name,version_name, output_folder=None):
    version = self.get_project_version_by_name(project_name,version_name)
    codelocations = self.get_version_codelocations(version)
    import os
    if output_folder:
        if not os.path.exists(output_folder):
            os.makedirs(output_folder, 0o755, True)
    
    result = []
    
    for item in codelocations['items']:
        links = item['_meta']['links']
        matches = [x for x in links if x['rel'] == 'enclosure' or x['rel'] == 'scan-data']
        for m in matches:
            url = m['href']
            filename = url.split('/')[6]
            if output_folder:
                pathname = os.path.join(output_folder, filename)
            else:
                if not os.path.exists(project_name):
                    os.mkdir(project_name)
                pathname = os.path.join(project_name, filename)
            responce = requests.get(url, headers=self.get_headers(), stream=True, verify=not self.config['insecure'])
            with open(pathname, "wb") as f:
                for data in responce.iter_content():
                    f.write(data)
            result.append({filename, pathname})
    return result
                        
def get_codelocations(self, limit=100, unmapped=False, parameters={}):
    parameters['limit'] = limit
    paramstring = self._get_parameter_string(parameters)
    headers = self.get_headers()
    url = self.get_apibase() + "/codelocations" + paramstring
    headers['Accept'] = 'application/vnd.blackducksoftware.scan-4+json'
    response = requests.get(url, headers=headers, verify = not self.config['insecure'])
    jsondata = response.json()
    if unmapped:
        jsondata['items'] = [s for s in jsondata['items'] if 'mappedProjectVersion' not in s]
        jsondata['totalCount'] = len(jsondata['items'])
    return jsondata

def get_codelocation_scan_summaries(self, code_location_id = None, code_location_obj = None, limit=100):
    '''Retrieve the scans (aka scan summaries) for the given location. You can give either
    code_location_id or code_location_obj. If both are supplied, precedence is to use code_location_obj
    '''
    assert code_location_id or code_location_obj, "You must supply at least one - code_location_id or code_location_obj"

    paramstring = "?limit={}&offset=0".format(limit)
    headers = self.get_headers()
    headers['Accept'] = 'application/vnd.blackducksoftware.scan-4+json'
    if code_location_obj:
        url = self.get_link(code_location_obj, "scans")
    else:
        url = self.get_apibase() + \
            "/codelocations/{}/scan-summaries".format(code_location_id)
    response = requests.get(url, headers=headers, verify = not self.config['insecure'])
    jsondata = response.json()
    return jsondata

def delete_unmapped_codelocations(self, limit=1000):
    code_locations = self.get_codelocations(limit=limit, unmapped=True).get('items', [])

    for c in code_locations:
        scan_summaries = self.get_codelocation_scan_summaries(code_location_obj = c).get('items', [])

        if scan_summaries[0]['status'] == 'COMPLETE':
            response = self.execute_delete(c['_meta']['href'])

def delete_codelocation(self, locationid):
    url = self.config['baseurl'] + "/api/codelocations/" + locationid
    headers = self.get_headers()
    response = requests.delete(url, headers=headers, verify = not self.config['insecure'])
    return response
    
def get_scan_locations(self, code_location_id):
    headers = self.get_headers()
    headers['Accept'] = 'application/vnd.blackducksoftware.scan-4+json'
    url = self.get_apibase() + "/codelocations/{}".format(code_location_id)
    response = requests.get(url, headers=headers, verify = not self.config['insecure'])
    jsondata = response.json()
    return jsondata
