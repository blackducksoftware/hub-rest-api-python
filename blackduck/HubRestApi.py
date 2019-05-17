'''
Created on Jul 6, 2018

@author: kumykov

Wrapper for common HUB API queries. 
Upon initialization Bearer tocken is obtained and used for all subsequent calls

Usage: 

credentials and hub URL could be placed in the .restconfig.json file
    
    {
      "baseurl": "https://hub-hostname",
      "username": "<username goes here>",
      "password": "<password goes here>",
      "insecure": true,
      "debug": false
    }

    OR, using API Token

    {
      "baseurl": "https://hub-hostname",
      "api_token": "<API token goes here>",
      "insecure": true,
      "debug": false
    }

    .restconfig.json should be present in the current directory.
    
    from blackduck.HubRestApi import HubInstance
    
    hub = HubInstance()
    projects = hub.get_projects()

It is possible to generate generate_config file by initalizing API as following:
   
    from blackduck.HubRestApi import HubInstance
    
    username="<username goes here>"
    password="<password goes here>"
    urlbase="https://hub-hostname"
    
    hub = HubInstance(urlbase, username, password, insecure=True)
    
    
'''
import logging
import requests
import json

# TODO: Create some kind of Black Duck exception grouping/hierarchy?

class CreateFailedAlreadyExists(Exception):
    pass

class CreateFailedUnknown(Exception):
    pass

class InvalidVersionPhase(Exception):
    pass

class UnknownVersion(Exception):
    pass

class UnsupportedBDVersion(Exception):
    # Some operations require specific versions of BD
    pass

def object_id(object):
    assert '_meta' in object, "REST API object must have _meta key"
    assert 'href' in object['_meta'], "REST API object must have href key in it's _meta"
    return object['_meta']['href'].split("/")[-1]

class HubInstance(object):
    '''
    classdocs
    '''
    VERSION_PHASES = ["PLANNING", "DEVELOPMENT", "PRERELEASE", "RELEASED", "DEPRECATED", "ARCHIVED"]
    PROJECT_VERSION_SETTINGS = ['nickname', 'releaseComments', 'version', 'phase', 'distribution', 'releasedOn']

    # TODO: What to do about the config file for thread-safety, concurrency
    configfile = ".restconfig.json"

    def __init__(self, *args, **kwargs):
        # Config needs to be an instance variable for thread-safety, concurrent use of HubInstance()
        self.config = {}

        try:
            self.config['baseurl'] = args[0]
            api_token = kwargs.get('api_token', False)
            if api_token:
                self.config['api_token'] = api_token
            else:
                self.config['username'] = args[1]
                self.config['password'] = args[2]
            self.config['insecure'] = kwargs.get('insecure', False)
            self.config['debug'] = kwargs.get('debug', False)

            if kwargs.get('write_config_flag', True):
                self.write_config()
        except Exception:
            self.read_config()
            
        if self.config['insecure']:
            requests.packages.urllib3.disable_warnings()
        
        if self.config['debug']:
            print(self.configfile)
        
        self.token, self.csrf_token, self.cookie = self.get_auth_token()
        try:
            self.version_info = self._get_hub_rest_api_version_info()
        except UnknownVersion:
            self.version_info = {'version': '3'} # assume it's v3 since all versions after 3 supported version info

        self.bd_major_version = self._get_major_version()
        
    def read_config(self):
        with open('.restconfig.json','r') as f:
            self.config = json.load(f)
            
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
            bearer_token = json.loads(response.content.decode('utf-8'))['bearerToken']
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
        parameter_string = "&".join(["{}={}".format(k,v) for k,v in parameters.items()])
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
        if '_meta' in bd_rest_obj and 'links' in bd_rest_obj['_meta']:
            for link_obj in bd_rest_obj['_meta']['links']:
                if 'rel' in link_obj and link_obj['rel'] == link_name:
                    return link_obj.get('href', None)
        else:
            logging.debug("This does not appear to be a BD REST object. It should have ['_meta']['links']")

    def get_limit_paramstring(self, limit):
        return "?limit={}".format(limit)

    def get_apibase(self):
        return self.config['baseurl'] + "/api"
    
    ###
    #
    # Role stuff
    #
    ###
    def _get_role_url(self):
        return self.config['baseurl'] + "/api/roles"

    def get_roles(self, parameters={}):
        url = self._get_role_url() + self._get_parameter_string(parameters)
        response = self.execute_get(url)
        return response.json()

    def get_roles_url_from_user_or_group(self, user_or_group):
        # Given a user or user group object, return the 'roles' url
        roles_url = None
        for endpoint in user_or_group['_meta']['links']:
            if endpoint['rel'] == "roles":
                roles_url = endpoint['href']
        return roles_url

    def get_roles_for_user_or_group(self, user_or_group):
        roles_url = self.get_roles_url_from_user_or_group(user_or_group)
        if roles_url:
            response = self.execute_get(roles_url)
            return response.json()
        else:
            return []

    def get_role_url_by_name(self, role_name):
        # Return the global (as opposed to project-specific) role URL for this server corresponding to the role name
        all_roles = self.get_roles()
        for role in all_roles['items']:
            if role['name'] == role_name:
                return role['_meta']['href']

    def assign_role_to_user_or_group(self, role_name, user_or_group):
        user_or_group_roles_url = self.get_roles_url_from_user_or_group(user_or_group)
        return self.assign_role_given_role_url(role_name, user_or_group_roles_url)

    def assign_role_given_role_url(self, role_name, user_or_group_role_assignment_url):
        role_url = self.get_role_url_by_name(role_name)
        if self.bd_major_version == "3":
            # A hack to get the assignment to work on v3
            role_url = role_url.replace("api", "api/internal")
        data = {"name": role_name, "role": role_url}
        logging.debug("executing POST to {} with {}".format(
            user_or_group_role_assignment_url, data))
        return self.execute_post(user_or_group_role_assignment_url, data = data)

    def delete_role_from_user_or_group(self, role_name, user_or_group):
        roles = self.get_roles_for_user_or_group(user_or_group)
        for role in roles['items']:
            if role['name'] == role_name:
                self.execute_delete(role['_meta']['href'])

    # def get_current_user_roles(self):
    #     url = self.config['baseurl'] + "/api/current-user"
    #     response = self.execute_get(url)
    #     response = self.get_roles_for_user_or_group(response.json())
    #     roles_json = response.json()
    #     return roles_json

    # def current_user_has_role(self, role_name):
    #     user_roles_obj = self.get_current_user_roles()
    #     return role_name in [r['name'] for r in user_roles_obj['items']]

    def user_has_role(self, user_or_group, role_name):
        user_roles_obj = self.get_roles_for_user_or_group(user_or_group)
        return role_name in [r['name'] for r in user_roles_obj['items']]

    ###
    #
    # User stuff
    #
    ###
    def _get_user_url(self):
        return self.config['baseurl'] + "/api/users"

    def get_users(self, parameters={}):
        url = self._get_user_url() + self._get_parameter_string(parameters)
        headers = {'Accept': 'application/vnd.blackducksoftware.user-4+json'}
        response = self.execute_get(url, custom_headers=headers)
        return response.json()

    def get_current_user(self):
        url = self.config['baseurl'] + "/api/current-user"
        headers = {'Accept': 'application/vnd.blackducksoftware.user-4+json'}
        response = self.execute_get(url, custom_headers=headers)
        return response.json()

    def create_user(self, user_json):
        url = self._get_user_url()
        location = self._create(url, user_json)
        return location

    def get_user_by_id(self, user_id):
        url = self._get_user_url() + "/{}".format(user_id)
        headers = {'Accept': 'application/vnd.blackducksoftware.user-4+json'}
        return self.get_user_by_url(url, custom_headers=headers)

    def get_user_by_url(self, user_url):
        headers = {'Accept': 'application/vnd.blackducksoftware.user-4+json'}
        response = self.execute_get(user_url, custom_headers=headers)
        jsondata = response.json()
        return jsondata

    def update_user_by_id(self, user_id, update_json):
        url = self._get_user_url() + "/{}".format(user_id)
        return self.update_user_by_url(url, update_json)

    def update_user_by_url(self, user_url, update_json):
        return self.execute_put(user_url, update_json)

    def delete_user_by_id(self, user_id):
        url = self._get_user_url() + "/{}".format(user_id)
        return self.delete_user_by_url(url)

    def delete_user_by_url(self, user_url):
        return self.execute_delete(user_url)
		
    def reset_user_password(self, user_id, new_password):
        url = self.config['baseurl'] + "/api/users/" + user_id + "/resetpassword"
        headers = {'Content-Type':'application/vnd.blackducksoftware.user-1+json', 'Accept': 'application/json'}
        data = {'password': new_password}
        return self.execute_put(url, data, headers)

    ###
    #
    # User group stuff
    #
    ###
    def _get_user_group_url(self):
        return self.config['baseurl'] + "/api/usergroups"

    def get_user_groups(self, parameters={}):
        url = self._get_user_group_url() + self._get_parameter_string(parameters)
        headers = {'Accept': 'application/vnd.blackducksoftware.user-4+json'}
        response = self.execute_get(url, custom_headers=headers)
        return response.json()

    def get_user_group_by_name(self, group_name):
        groups = self.get_user_groups()
        for group in groups['items']:
            if group['name'] == group_name:
                return group

    def create_user_group(self, user_group_json):
        if self.bd_major_version == "3":
            url = self.config['baseurl'] + '/api/v1/usergroups'
        else:
            url = self._get_user_group_url()
        location = self._create(url, user_group_json)
        return location

    def create_user_group_by_name(self, group_name, active=True):
        user_group_info = {
            'name': group_name,
            'createdFrom': 'INTERNAL',
            'active': active
        }
        return self.create_user_group(user_group_info)

    # def get_user_group_by_id(self, user_group_id):
    #     url = self._get_user_group_url() + "/{}".format(user_group_id)
    #     return self.get_user_group_by_url(url)

    # def get_user_group_by_url(self, user_group_url):
    #     response = self.execute_get(user_group_url)
    #     jsondata = response.json()
    #     return jsondata

    # def get_user_group_by_name(self, user_group_name):
    #     url = self._get_user_group_url() + "?q={}".format(user_group_name)
    #     response = self.execute_get(url)
    #     user_group_obj = response.json()
    #     if user_group_obj['totalCount'] > 0:
    #         return user_group_obj['items'][0]

    def update_user_group_by_id(self, user_group_id, update_json):
        url = self._get_user_group_url() + "/{}".format(user_group_id)
        return self.update_user_group_by_url(url, update_json)

    def update_user_group_by_url(self, user_group_url, update_json):
        return self.execute_put(user_group_url, update_json)

    def delete_user_group_by_id(self, user_group_id):
        url = self._get_user_group_url() + "/{}".format(user_group_id)
        return self.delete_user_group_by_url(url)

    def delete_user_group_by_url(self, user_group_url):
        return self.execute_delete(user_group_url)

    ###
    #
    # Policy stuff
    #
    ###
    def _get_policy_url(self):
        return self.config['baseurl'] + "/api/policy-rules"

    def get_policies(self, parameters={}):
        url = self._get_policy_url() + self._get_parameter_string(parameters)
        headers = {'Accept': 'application/vnd.blackducksoftware.policy-4+json'}
        response = self.execute_get(url, custom_headers=headers)
        return response.json()

    def create_policy(self, policy_json):
        url = self._get_policy_url()
        location = self._create(url, policy_json)
        return location

    def get_policy_by_id(self, policy_id):
        url = self._get_policy_url() + "/{}".format(policy_id)
        return self.get_policy_by_url(url)

    def get_policy_by_url(self, policy_url):
        headers = {'Accept': 'application/vnd.blackducksoftware.policy-4+json'}
        response = self.execute_get(policy_url, custom_headers=headers)
        jsondata = response.json()
        return jsondata

    def update_policy_by_id(self, policy_id, update_json):
        url = self._get_policy_url() + "/{}".format(policy_id)
        return self.update_policy_by_url(url, update_json)

    def update_policy_by_url(self, policy_url, update_json):
        return self.execute_put(policy_url, update_json)

    def delete_policy_by_id(self, policy_id):
        url = self._get_policy_url() + "/{}".format(policy_id)
        return self.delete_policy_by_url(url)

    def delete_policy_by_url(self, policy_url):
        return self.execute_delete(policy_url)

    ##
    #
    # Vulnerabilities
    #
    ##
    def _get_vulnerabilities_url(self):
        return self.config['baseurl'] + '/api/vulnerabilities'

    def get_vulnerabilities(self, vulnerability, parameters={}):
        url = self._get_vulnerabilities_url() + "/{}".format(vulnerability) + self._get_parameter_string(parameters)
        headers = {'Accept': 'application/vnd.blackducksoftware.vulnerability-4+json'}
        response = self.execute_get(url, custom_headers=headers)
        return response.json()

    def get_vulnerability_affected_projects(self, vulnerability):
        url = self.config['baseurl'] + "/api/v1/composite/vulnerability"+ "/{}".format(vulnerability) 
        response = self.execute_get(url)
        return response.json()

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
        if component_list_d['totalCount'] >= 1:
            return component_list_d['items'][0]
        else:
            return component_list_d['items']

    def get_vulnerable_bom_components(self, version_obj, limit=9999):
        url = "{}/vulnerable-bom-components".format(version_obj['_meta']['href'])
        custom_headers = {'Content-Type': 'application/vnd.blackducksoftware.bill-of-materials-4+json'}
        param_string = self._get_parameter_string({'limit': limit})
        url = "{}{}".format(url, param_string)
        response = self.execute_get(url, custom_headers=custom_headers)
        if response.status_code == 200:
            vulnerable_bom_components = response.json()
            return vulnerable_bom_components
        else:
            logging.warning("Failed to retrieve vulnerable bom components for project {}, status code {}".format(
                version_obj, response.status_code))

    def get_component_remediation(self, bom_component):
        url = "{}/remediating".format(bom_component['componentVersion'])
        logging.debug("Url for getting remediation info is : {}".format(url))
        response = self.execute_get(url)
        return response.json()

    ##
    #
    # CSV and Notices reporting
    #
    ##

    valid_categories = ['VERSION','CODE_LOCATIONS','COMPONENTS','SECURITY','FILES']
    valid_report_formats = ["CSV"]
    def create_version_reports(self, version, report_list, format="CSV"):
        assert all(list(map(lambda k: k in HubInstance.valid_categories, report_list))), "One or more selected report categories in {} are not valid ({})".format(
            report_list, HubInstance.valid_categories)
        assert format in HubInstance.valid_report_formats, "Format must be one of {}".format(HubInstance.valid_report_formats)

        post_data = {
            'categories': report_list,
            'versionId': version['_meta']['href'].split("/")[-1],
            'reportType': 'VERSION',
            'reportFormat': format
        }
        version_reports_url = self.get_link(version, 'versionReport')
        return self.execute_post(version_reports_url, post_data)

    valid_notices_formats = ["TEXT", "HTML"]
    def create_version_notices_report(self, version, format="TEXT"):
        assert format in HubInstance.valid_notices_formats, "Format must be one of {}".format(HubInstance.valid_notices_formats)

        post_data = {
            'categories': HubInstance.valid_categories,
            'versionId': version['_meta']['href'].split("/")[-1],
            'reportType': 'VERSION_LICENSE',
            'reportFormat': format
        }
        notices_report_url = self.get_link(version, 'licenseReports')
        return self.execute_post(notices_report_url, post_data)

    def download_report(self, report_id):
        url = self.get_urlbase() + "/api/reports/{}".format(report_id)
        return self.execute_get(url, {'Content-Type': 'application/zip', 'Accept':'application/zip'})

    ##
    #
    # License stuff
    #
    ##
    def _get_license_info(self, license_obj):
        if 'license' in license_obj:
            license_info = {}
            text_json = {}
            logging.debug("license: {}".format(license_obj))
            response = self.execute_get(license_obj['license'])
            if response.status_code == 200:
                license_info = response.json()
                text_url = self.get_link(license_info, 'text')
                response = self.execute_get(text_url)
                if response.status_code == 200:
                    text_json = response.text
            yield {"license_info": license_info,
                    "license_text_info": text_json}
        elif 'licenses' in license_obj and isinstance(license_obj['licenses'], list):
            for license in license_obj['licenses']:
                self._get_license_info(license)

    def get_license_info_for_bom_component(self, bom_component, limit=1000):
        self._check_version_compatibility()
        all_licenses = {}
        logging.debug("gathering license info for bom component {}, version {}".format(
            bom_component['componentName'], bom_component['componentVersionName']))
        for license in bom_component.get('licenses', []):
            for license_info_obj in self._get_license_info(license):
                all_licenses.update({
                        license['licenseDisplay']: license_info_obj
                    })
        return all_licenses

    ##
    #
    # Files and Snippet matching
    #
    ##
    def _check_version_compatibility(self):
        if int(self.bd_major_version) < 2018:
            raise UnsupportedBDVersion("The BD major version {} is less than the minimum required major version {}".format(self.bd_major_version, 2018))        

    def get_file_bom_entries(self, hub_release_id, limit=100):
        self._check_version_compatibility()
        paramstring = self.get_limit_paramstring(limit)
        # Using internal API - see https://jira.dc1.lan/browse/HUB-18270: Make snippet API calls for ignoring, confirming snippet matches public
        url =  "{}/v1/releases/{}/file-bom-entries{}".format(self.get_apibase(), hub_release_id)
        url += paramstring
        logging.debug("GET {}".format(url))
        response = self.execute_get(url)
        jsondata = response.json()
        return jsondata

    def get_file_matches_for_bom_component(self, bom_component, limit=1000):
        self._check_version_compatibility()
        url = self.get_link(bom_component, "matched-files")
        paramstring = self.get_limit_paramstring(limit)
        logging.debug("GET {}".format(url))
        response = self.execute_get(url)
        jsondata = response.json()
        return jsondata

    def get_snippet_bom_entries(self, project_id, version_id, reviewed=False, included=False, limit=100, offset=0):
        self._check_version_compatibility()
        paramstring = "?limit=" + str(limit) + "&offset=" + \
            str(offset) + "&filter=bomReviewStatus:" + str(reviewed).lower() + "&filter=bomInclusion:" + str(included).lower()
        # Using internal API - see https://jira.dc1.lan/browse/HUB-18270: Make snippet API calls for ignoring, confirming snippet matches public
        path =  "{}/internal/projects/{}/versions/{}/snippet-bom-entries".format(self.get_apibase(), project_id, version_id)
        url = path + paramstring
        response = self.execute_get(url)
        jsondata = response.json()
        return jsondata

    def ignore_snippet_bom_entry(self, hub_version_id, snippet_bom_entry):
        self._check_version_compatibility()
        # Using internal API - see https://jira.dc1.lan/browse/HUB-18270: Make snippet API calls for ignoring, confirming snippet matches public
        url = "{}/v1/releases/{}/snippet-bom-entries".format(self.get_apibase(), hub_version_id)
        body = self.get_ignore_snippet_json(snippet_bom_entry)
        response = self.execute_put(url, body)
        jsondata = response.json()
        return jsondata

    def get_ignore_snippet_json(self, snippet_bom_entry):
        self._check_version_compatibility()
        for cur_fileSnippetBomComponents in snippet_bom_entry['fileSnippetBomComponents']:
            cur_fileSnippetBomComponents['ignored'] = True
        return [snippet_bom_entry]
    
    def confirm_snippet_bom_entry(self, hub_version_id, snippet_bom_entry):
        self._check_version_compatibility()
        # Using internal API - see https://jira.dc1.lan/browse/HUB-18270: Make snippet API calls for ignoring, confirming snippet matches public
        url = "{}/v1/releases/{}/snippet-bom-entries".format(self.get_apibase(), hub_version_id)
        body = self.get_confirm_snippet_json(snippet_bom_entry)
        response = self.execute_put(url, body)
        jsondata = response.json()
        return jsondata

    def get_confirm_snippet_json(self, snippet_bom_entry):
        self._check_version_compatibility()
        for cur_fileSnippetBomComponents in snippet_bom_entry['fileSnippetBomComponents']:
            cur_fileSnippetBomComponents['reviewStatus'] = 'REVIEWED'
            cur_fileSnippetBomComponents['ignored'] = False
        return [snippet_bom_entry]
    
    def edit_snippet_bom_entry(self, hub_version_id, snippet_bom_entry, new_kb_component):
        self._check_version_compatibility()
        # Using internal API - see https://jira.dc1.lan/browse/HUB-18270: Make snippet API calls for ignoring, confirming snippet matches public
        url = "{}/v1/releases/{}/snippet-bom-entries".format(self.get_apibase(), hub_version_id)
        body = self.get_edit_snippet_json(snippet_bom_entry, new_kb_component)
        response = self.execute_put(url, body)
        jsondata = response.json()
        return jsondata

    def get_edit_snippet_json(self, snippet_bom_entry, new_kb_component):
        self._check_version_compatibility()
        assert 'fileSnippetBomComponents' in snippet_bom_entry
        assert len(snippet_bom_entry['fileSnippetBomComponents']) == 1, "We can only edit the component info for one snippet match at a time"

        # TODO: Handle case where either the component from snippet_bom_entry OR new_kb_component does not have a version?
        snippet_component_info = snippet_bom_entry['fileSnippetBomComponents'][0]
        snippet_component_info['project']['id'] = new_kb_component['component'].split("/")[-1]
        snippet_component_info['release']['id'] = new_kb_component['componentVersion'].split("/")[-1]
        return [snippet_bom_entry]
    
    def get_alternate_matches_for_snippet(self, project_id, version_id, snippet_object):
        self._check_version_compatibility()
        version_bom_entry_id = snippet_object['fileSnippetBomComponents'][0]['versionBomEntryId']

        # Using internal API - see https://jira.dc1.lan/browse/HUB-18270: Make snippet API calls for ignoring, confirming snippet matches public
        url =  "{}/internal/projects/{}/versions/{}/alternate-snippet-matches/{}".format(
            self.get_apibase(), project_id, version_id, version_bom_entry_id)
        response = self.execute_get(url)
        jsondata = response.json()
        alternate_matches = list()
        for snippet_bom_components_d in jsondata['snippetMatches']:
            for snippet_bom_component in snippet_bom_components_d['snippetBomComponents']:
                alternate_matches.append(snippet_bom_component)
        return alternate_matches

    def find_matching_alternative_snippet_match(self, project_id, version_id, snippet_object, kb_component):
        # Given a KB component, find the matching alternative snippet match for a given snippet BOM entry
        # Returns None if no match was found
        kb_component_id = kb_component['component'].split("/")[-1]
        # TODO: handle cases where there is no version supplied?
        kb_component_version_id = kb_component['componentVersion'].split("/")[-1]
        for alternative_match in self.get_alternate_matches_for_snippet(project_id, version_id, snippet_object):
            alternative_match_component_id = alternative_match['project']['id']
            alternative_match_component_version_id = alternative_match['release']['id']
            if kb_component_id == alternative_match_component_id and kb_component_version_id == alternative_match_component_version_id:
                return alternative_match

    def _generate_new_match_selection(self, original_snippet_match, new_component_match):
        # Merge the values from new_component_match into the origingal_snippet_match
        # Note: Must do the merge to preserver other key/value pairs in the original_snippet_match (e.g. ignored, reviewStatus, versionBomComponentId)
        # TODO: Can there ever be more than one item in fileSnippetBomComponents?
        for k in original_snippet_match['fileSnippetBomComponents'][0].keys():
            if k in new_component_match:
                original_snippet_match['fileSnippetBomComponents'][0][k] = new_component_match[k]
        return [original_snippet_match]

    def update_snippet_match(self, version_id, current_snippet_match, new_snippet_match_component):
        # Update the (snippet) component selection for a given snippet match
        # Assumption: new_snippet_match_component is from one of the alternate matches listed for the file snippet match
        self._check_version_compatibility()
        headers = self.get_headers()
        headers['ContentType'] = "application/json"
        # Using internal API - see https://jira.dc1.lan/browse/HUB-18270: Make snippet API calls for ignoring, confirming snippet matches public
        url = "{}/v1/releases/{}/snippet-bom-entries".format(self.get_apibase(), version_id)
        body = self._generate_new_match_selection(current_snippet_match, new_snippet_match_component)
        response = self.execute_put(url, body)
        jsondata = response.json()
        return jsondata

    ##
    #
    # Projects and versions Stuff
    #
    ##

    def _get_projects_url(self):
        return self.get_urlbase() + "/api/projects"

    def get_projects(self, limit=100, parameters={}):
        headers = self.get_headers()
        if limit:
            parameters.update({'limit': limit})
        url = self._get_projects_url() + self._get_parameter_string(parameters)
        headers['Accept'] = 'application/vnd.blackducksoftware.project-detail-4+json'
        response = requests.get(url, headers=headers, verify = not self.config['insecure'])
        jsondata = response.json()
        return jsondata

    def create_project(self, project_name, version_name="Default Version", parameters={}):
        url = self._get_projects_url()

        post_data = {
          "name": project_name,
          "description": parameters.get("description", ""),
          "projectTier": parameters.get("project_tier", ""),
          "projectOwner": parameters.get("project_owner", ""),
          "projectLevelAdjustments": parameters.get("project_level_adjustments", True),
          "cloneCategories": [
            "COMPONENT_DATA",
            "VULN_DATA"
          ],
          "versionRequest": {
            "phase": parameters.get("version_phase", "PLANNING"),
            "distribution": parameters.get("version_distribution", "EXTERNAL"),
            "projectLevelAdjustments": parameters.get("project_level_adjustments", True),
            "versionName": version_name
          }
        }
        response = self.execute_post(url, data=post_data)
        return response

    def create_project_version(self, project_obj, new_version_name, parameters={}):
        url = self.get_link(project_obj, "versions")

        version_phase = parameters.get("phase", "PLANNING")
        if version_phase not in HubInstance.VERSION_PHASES:
            raise InvalidVersionPhase("The phase given {} is not in the list of valid phases ({})".format(
                version_phase, HubInstance.VERSION_PHASES))

        post_data = {
            "versionUrl": url,
            "cloneCategories": [
                "VULN_DATA",
                "COMPONENT_DATA"
            ],
            "versionName": new_version_name,
            "phase": parameters.get("phase", "PLANNING"),
            "distribution": parameters.get("distribution", "EXTERNAL")
        }
        response = self.execute_post(url, data=post_data)
        return response

    def get_project_by_name(self, project_name):
        project_list = self.get_projects(parameters={"q":"name:{}".format(project_name)})
        for project in project_list['items']:
            if project['name'] == project_name:
                return project

    def get_version_by_name(self, project, version_name):
        version_list = self.get_project_versions(project, parameters={'q':"versionName:{}".format(version_name)})
        # A query by name can return more than one version if other versions
        # have names that include the search term as part of their name
        for version in version_list['items']:
            if version['versionName'] == version_name:
                return version

    def get_project_version_by_name(self, project_name, version_name):
        project = self.get_project_by_name(project_name)
        if project:
            version = self.get_version_by_name(project, version_name)
            if version == None:
                logging.debug("Did not find any project version matching {}".format(version_name))
            else:
                return version
        else:
            logging.debug("Did not find a project with name {}".format(project_name))

    def get_or_create_project_version(self, project_name, version_name, parameters = {}):
        project = self.get_project_by_name(project_name)
        if project:
            version = self.get_version_by_name(project, version_name)
            if not version:
                self.create_project_version(project, version_name, parameters)
                version = self.get_version_by_name(project, version_name)
        else:
            self.create_project(project_name, version_name, parameters)
            project = self.get_project_by_name(project_name)
            version = self.get_version_by_name(project, version_name)
        return version

    def get_project_by_id(self, project_id, limit=100):
        headers = self.get_headers()
        paramstring = self.get_limit_paramstring(limit)
        url = self._get_projects_url() + project_id + paramstring
        headers['Accept'] = 'application/vnd.blackducksoftware.project-detail-4+json'
        response = requests.get(url, headers=headers, verify = not self.config['insecure'])
        jsondata = response.json()
        return jsondata

    def get_project_versions(self, project, limit=100, parameters={}):
        # paramstring = self.get_limit_paramstring(limit)
        parameters.update({'limit': limit})
        url = project['_meta']['href'] + "/versions" + self._get_parameter_string(parameters)
        headers = self.get_headers()
        headers['Accept'] = 'application/vnd.blackducksoftware.project-detail-4+json'
        response = requests.get(url, headers=headers, verify = not self.config['insecure'])
        jsondata = response.json()
        return jsondata

    def get_version_components(self, projectversion, limit=1000):
        paramstring = self.get_limit_paramstring(limit)
        url = projectversion['_meta']['href'] + "/components" + paramstring
        headers = self.get_headers()
        headers['Accept'] = 'application/vnd.blackducksoftware.bill-of-materials-4+json'
        response = requests.get(url, headers=headers, verify = not self.config['insecure'])
        jsondata = response.json()
        return jsondata

    def update_project_version_settings(self, project_name, version_name, new_settings={}):
        # Apply any new settings to the given project version
        version = self.get_project_version_by_name(project_name, version_name)

        if version:
            for k,v in new_settings.items():
                if k in HubInstance.PROJECT_VERSION_SETTINGS:
                    logging.debug("updating setting {} in version {} with value {}".format(
                        k, version['versionName'], v))
                    version[k] = v
                else:
                    logging.warn("Setting {} is not in the list of project version settings ({})".format(
                        k, HubInstance.PROJECT_VERSION_SETTINGS))

            url = version['_meta']['href']

            response = self.execute_put(url, version)

            if response.status_code == 200:
                logging.info("Successfully updated version {} with new settings {}".format(
                    version['versionName'], new_settings))
            else:
                logging.error("Failed to update version {} with new settings {}; status code: {}".format(
                    version['versionName'], new_settings, response.status_code))
        else:
            logging.debug("Did not find a matching project-version in project {}, version name {}".format(
                project_name, version_name))

    def get_version_by_id(self, project_id, version_id, limit=100):
        headers = self.get_headers()
        paramstring = self.get_limit_paramstring(limit)
        url = self._get_projects_url() + project_id + "/versions/" + version_id
        headers['Accept'] = 'application/vnd.blackducksoftware.project-detail-4+json'
        response = requests.get(url, headers=headers, verify = not self.config['insecure'])
        jsondata = response.json()
        return jsondata
        
    def compare_project_versions(self, version, compareTo):
        apibase = self.config['baseurl'] + "/api"
        paramstring = "?limit=1000&sortField=component.securityRiskProfile&ascending=false&offset=0"
        cwhat = version['_meta']['href'].replace(apibase, '')
        cto = compareTo['_meta']['href'].replace(apibase, '')
        url = apibase + cwhat + "/compare" + cto + "/components" + paramstring
        headers = self.get_headers()
        response = requests.get(url, headers=headers, verify = not self.config['insecure'])
        jsondata = response.json()
        return jsondata
    
    def get_version_codelocations(self, version, limit=100, offset=0):
        url = self.get_link(version, "codelocations") + self._get_parameter_string({
            'limit': limit,
            'offset': offset})
        custom_headers = {'Content-Type': 'application/vnd.blackducksoftware.scan-4+json'}
        response = self.execute_get(url, custom_headers=custom_headers)
        jsondata = response.json()
        return jsondata

    def delete_project_version_by_name(self, project_name, version_name, save_scans=False):
        project = self.get_project_by_name(project_name)
        if project:
            logging.debug("found project {}".format(project))
            project_versions = self.get_project_versions(
                project, 
                parameters={'q':"versionName:{}".format(version_name)}
            )

            project_version_codelocations = None
            if 'totalCount' in project_versions and project_versions['totalCount'] == 1:
                project_version = project_versions['items'][0]
                logging.debug("found the project version: {}".format(project_version))

                delete_scans = not save_scans
                logging.debug("delete_scans was {}".format(delete_scans))

                if delete_scans:
                    self.delete_project_version_codelocations(project_version)
                else:
                    logging.debug("Delete scans was false, or we did not find any codelocations (scans) in version {} of project {}".format(version_name, project_name))
                # TODO: Check if the project will be "empty" once we delete this version and
                # delete the project accordingly?
                logging.info("Deleting project-version at: {}".format(project_version['_meta']['href']))
                self.execute_delete(project_version['_meta']['href'])
            else:
                logging.debug("Did not find version with name {} in project {}".format(version_name, project_name))
        else:
            logging.debug("Did not find project with name {}".format(project_name))
    
    def delete_project_by_name(self, project_name, save_scans=False):
        project = self.get_project_by_name(project_name)
        if project:
            # get project versions
            project_versions = self.get_project_versions(project)
            versions = project_versions.get('items', [])
            logging.debug("Retrieved {} versions for project {}".format(len(versions), project_name))
            
            delete_scans = not save_scans
            logging.debug("delete_scans was {}".format(delete_scans))
                
            if delete_scans:
                # delete all code locations associated with each version
                for version in versions:
                    logging.debug("Deleting code locations (aka scans) for version {}".format(version['versionName']))
                    self.delete_project_version_codelocations(version)
                        
            # delete the project itself
            project_url = project['_meta']['href']
            logging.info("Deleting project {}".format(project_name))
            self.execute_delete(project_url)
        else:
            logging.debug("Did not find project with name {}".format(project_name))
            
    def delete_project_version_codelocations(self, version):
        version_name = version['versionName']
        try:
            logging.debug("Retrieving code locations (aka scans) for version {}".format(version_name))
            version_code_locations = self.get_version_codelocations(version)
        except:
            logging.error("Failed to get codelocations (aka scans) for version {}".format(version_name), exc_info=True)
            version_code_locations = []
        else:
            version_code_locations = version_code_locations.get('items', []) if version_code_locations else []
        logging.debug("Found {} code locations (aka scans) for version {}".format(len(version_code_locations), version_name))
        code_location_urls = [c['_meta']['href'] for c in version_code_locations]
        for code_location_url in code_location_urls:
            logging.info("Deleting code location at: {}".format(code_location_url))
            self.execute_delete(code_location_url)

    def delete_empty_projects(self):
        #get all projects with no mapped code locations and delete them all
        projects = self.get_projects().get('items',[])
        for p in projects:
            p_empty = True
            versions = self.get_project_versions(p)
            for v in versions:
                codelocations = self.get_version_codelocations(versions['items'][0])
                if codelocations['totalCount'] != 0:
                    p_empty = False
                    break
            if p_empty:
                self.execute_delete(p['_meta']['href'])
    
    def _find_user_group_url(self, assignable_user_groups, user_group_name):
        for user_group in assignable_user_groups['items']:
            if user_group['name'] == user_group_name:
                return user_group['usergroup']

    def _project_role_urls(self, project_role_names):
        all_project_roles = self.get_project_roles()
        project_role_urls = list()
        for project_role_name in project_role_names:
            for project_role in all_project_roles:
                if project_role_name == project_role['name']:
                    project_role_urls.append(project_role['_meta']['href'])
        return project_role_urls

    def assign_user_group_to_project(self, project_name, user_group_name, project_roles):
        # Assign the user group to the project using the list of project-role names
        project = self.get_project_by_name(project_name)
        # user_group = self.get_user_group_by_name(user_group_name)

        if project:
            project_url = project['_meta']['href']
            assignable_user_groups_link = self.get_link(project, 'assignable-usergroups')
            if assignable_user_groups_link:
                assignable_user_groups_response = self.execute_get(assignable_user_groups_link)
                assignable_user_groups = assignable_user_groups_response.json()

                # TODO: What to do if the user group is already assigned to the project, and therefore
                # does not appear in the list of 'assignable' user groups? Should we search the (assigned) user
                # groups and re-apply the project-roles to the assignment?

                user_group_url = self._find_user_group_url(assignable_user_groups, user_group_name)
                if user_group_url:
                    headers = self.get_headers()

                    # need project role urls to build the POST payload
                    project_roles_urls = self._project_role_urls(project_roles)

                    # The POST endpoint changes based on whether we found any project-roles to assign
                    # Also, due to what appears to be a defect, the Content-Type changes
                    if project_roles_urls:
                        url = user_group_url + "/roles"
                        # one dict per project role assignment
                        post_data = [{'role': r, 'scope': project_url} for r in project_roles_urls]
                        # I found I had to use this Content-Type (application/json resulted in 412)
                        # ref: https://jira.dc1.lan/browse/HUB-18417
                        headers['Content-Type'] = 'application/vnd.blackducksoftware.internal-1+json'
                    else:
                        url = project_url + "/usergroups"
                        # Assigning a group with no project-roles
                        post_data = {"group": user_group_url}
                        headers['Content-Type'] = 'application/json'

                    response = requests.post(
                        url, 
                        headers=headers, 
                        data=json.dumps(post_data), 
                        verify = not self.config['insecure'])
                    return response
                else:
                    assignable_groups = [u['name'] for u in assignable_user_groups['items']]
                    logging.warning("The user group {} was not found in the assignable user groups ({}) for this project {}. Is the group already assigned to this project?".format(
                        user_group_name, assignable_groups, project_name))
            else:
                logging.warning("This project {} has no assignable user groups".format(project_name))
        else:
            logging.warning("Did not find a project by the name {}".format(project_name))

    def assign_user_to_project(self, user_name, project_name, project_roles_l):
        pass

    def assign_project_application_id(self, project_name, application_id, overwrite=False):
        logging.debug("Assigning application_id {} to project_name {}, overwrite={}".format(
            application_id, project_name, overwrite))

        existing_application_id, application_id_url = self.get_project_application_id(project_name)

        if existing_application_id:
            if overwrite:
                logging.debug("Found an existing application id {} for project {} and overwrite was True. Updating it to {}".format(
                    existing_application_id, project_name, application_id))
                return self.update_project_application_id(project_name, application_id)
            else:
                logging.debug("Found an existing application id {} for project {} and overwrite was False so not updating it".format(
                    existing_application_id, project_name))
        else:
            logging.debug("No application id exists for project {}, assigning {} to it".format(
                project_name, application_id))
            project = self.get_project_by_name(project_name)
            if project:
                project_mappings_url = self.get_link(project, "project-mappings")
                if project_mappings_url:
                    post_data = {"applicationId": application_id}
                    response = self.execute_post(project_mappings_url, data=post_data)
                    return response
                else:
                    logging.warning("Did not find project-mappings URL for project {}".format(project))
            else:
                logging.warning("Did not find project by name {}".format(project_name))

    def update_project_application_id(self, project_name, new_application_id):
        application_id, application_id_url = self.get_project_application_id(project_name)

        if application_id and application_id_url:
            put_data = {
                "applicationId": new_application_id,
                "_meta": {
                    "allow": [
                      "DELETE",
                      "GET",
                      "PUT"
                    ],
                    "href": application_id_url,
                    "links": []
                }
            }
            response = self.execute_put(application_id_url, data=put_data)
            return response
        else:
            logging.debug("Did not find application id for project name {}".format(project_name))

    def delete_application_id(self, project_name):
        application_id, application_id_url = self.get_project_application_id(project_name)

        if application_id_url:
            self.execute_delete(application_id_url)

    def get_project_application_id(self, project_name):
        project_mapping_info = self.get_project_info(project_name, 'project-mappings')
        if project_mapping_info and 'items' in project_mapping_info:
            for project_mapping in project_mapping_info['items']:
                if 'applicationId' in project_mapping:
                    application_id = project_mapping['applicationId']
                    application_id_url = project_mapping['_meta']['href']

                    return (application_id, application_id_url)
            logging.debug("Did not find any project-mappings with 'applicationId' in them")
            return (None, None)
        else:
            logging.debug("did not find any project-mappings for project {}".format(project_name))
            return (None, None)

    def get_project_info(self, project_name, link_name):
        project = self.get_project_by_name(project_name)
        link = self.get_link(project, link_name)
        if link:
            response = self.execute_get(link)
            return response.json()
        else:
            return {} # nada

    def get_project_roles(self):
        all_project_roles = self.get_roles(parameters={"filter":"scope:project"})
        return all_project_roles['items']

    ###
    #
    # Add project version as a component to another project
    # 
    # WARNING: Uses internal API
    ###
    
    def add_version_as_component(self, main_project_release, sub_project_release):
        headers = self.get_headers()
        main_data = main_project_release['_meta']['href'].split('/')
        sub_data = sub_project_release['_meta']['href'].split('/')
        url = self.get_apibase() + "/v1/releases/" + main_data[7] + "/component-bom-entries"
        print (url)
        payload = {}
        payload['producerProject'] = {}
        payload['producerProject']['id'] = sub_data[5]
        payload['producerRelease'] = {} 
        payload['producerRelease']['id'] = sub_data[7]
        print (json.dumps(payload))
        response = requests.post(url, headers=headers, verify = not self.config['insecure'], json=payload)
        jsondata = response.json()
        return jsondata

    def remove_version_as_component(self, main_project_release, sub_project_release):
        headers = self.get_headers()
        main_data = main_project_release['_meta']['href'].split('/')
        sub_data = sub_project_release['_meta']['href'].split('/')
        url = self.get_apibase() + "/v1/releases/" + main_data[7] + "/component-bom-entries"
        print (url)
        payload = []
        entity = {}
        entity['entityKey'] = {}
        entity['entityKey']['entityId'] = sub_data[7]
        entity['entityKey']['entityType'] = 'RL'
        payload.append(entity)
        print (json.dumps(payload))
        response = requests.delete(url, headers=headers, verify = not self.config['insecure'], json=payload)
        return response

    ###
    #
    # Code locations or Scans Stuff
    #
    ###
    
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
            matches = [x for x in links if x['rel'] == 'enclosure']
            for m in matches:
                url = m['href']
                filename = url.split('/')[6]
                if output_folder:
                    pathname = os.path.join(output_folder, filename)
                else:
                    pathname = filename
                responce = requests.get(url, headers=self.get_headers(), stream=True, verify=False)
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
        if response.status_code == 200:
            jsondata = response.json()
            if unmapped:
                jsondata['items'] = [s for s in jsondata['items'] if 'mappedProjectVersion' not in s]
                jsondata['totalCount'] = len(jsondata['items'])
            return jsondata
        elif response.status_code == 403:
            logging.warning("Failed to retrieve code locations (aka scans) probably due to lack of permissions, status code {}".format(
                response.status_code))
        else:
            logging.error("Failed to retrieve code locations (aka scans), status code {}".format(
                response.status_code))

    def get_codelocation_scan_summaries(self, code_location_id, limit=100):
        paramstring = "?limit={}&offset=0".format(limit)
        headers = self.get_headers()
        url = self.get_apibase() + \
            "/codelocations/{}/scan-summaries".format(code_location_id)
        response = requests.get(url, headers=headers, verify = not self.config['insecure'])
        jsondata = response.json()
        return jsondata
    
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

    def delete_codelocation(self, locationid):
        url = self.config['baseurl'] + "/api/codelocations/" + locationid
        headers = self.get_headers()
        response = requests.delete(url, headers=headers, verify = not self.config['insecure'])
        return response
        
    def get_scan_locations(self, code_location_id):
        headers = self.get_headers()
        url = self.get_apibase() + \
            "/v1/scanlocations/{}".format(code_location_id)
        response = requests.get(url, headers=headers, verify = not self.config['insecure'])
        jsondata = response.json()
        return jsondata

    def execute_delete(self, url):
        headers = self.get_headers()
        response = requests.delete(url, headers=headers, verify = not self.config['insecure'])
        return response

    def get_ldap_state(self):
        url = self.config['baseurl'] + "/api/v1/ldap/state"
        headers = self.get_headers()
        response = requests.get(url, headers=headers, verify = not self.config['insecure'])
        jsondata = response.json()
        return jsondata

    def enable_ldap(self):
        url = self.config['baseurl'] + "/api/v1/ldap/state"
        headers = self.get_headers()
        payload = {}
        payload['ldapEnabled'] = True
        response = requests.post(url, headers=headers, verify = not self.config['insecure'], json=payload)
        jsondata = response.json()
        return jsondata
        
    def disable_ldap(self):
        url = self.config['baseurl'] + "/api/v1/ldap/state"
        headers = self.get_headers()
        payload = {}
        payload['ldapEnabled'] = False
        response = requests.post(url, headers=headers, verify = not self.config['insecure'], json=payload)
        jsondata = response.json()
        return jsondata
        
    def get_ldap_configs(self):
        url = self.config['baseurl'] + "/api/v1/ldap/configs"
        headers = self.get_headers()
        headers['Content-Type']  = "application/json"
        response = requests.get(url, headers=headers, verify = not self.config['insecure'])
        jsondata = response.json()
        return jsondata

    def delete_unmapped_codelocations(self, limit=1000):
        jsondata = self.get_codelocations(limit, True)
        codelocations = jsondata['items']
        for c in codelocations:
            response = self.execute_delete(c['_meta']['href'])

    ##
    #
    # Health Stuff
    #
    ##
    def get_health_checks(self):
        url = self.get_urlbase() + "/api/health-checks/liveness"
        return self.execute_get(url)
    
    ##
    #
    # Job Statistics
    #
    ##
    def get_job_statistics(self):
        url = self.get_urlbase() + "/api/job-statistics"
        response = self.execute_get(url)
        return response.json()
        
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
                    logging.warning('did not receive any json data back')
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


