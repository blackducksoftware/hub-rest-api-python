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
from operator import itemgetter
import urllib.parse

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
        parameter_string = "&".join(["{}={}".format(k,v) for k,v in sorted(parameters.items(), key=itemgetter(0))])
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
        headers = {'Accept': 'application/json'}
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
        url = self._get_vulnerabilities_url() + "/{}/affected-projects".format(vulnerability) 
        custom_headers = {'Accept': 'application/vnd.blackducksoftware.vulnerability-4+json'}
        response = self.execute_get(url, custom_headers=custom_headers)
        return response.json()

    # TODO: Refactor this, i.e. use get_link method?
    def get_vulnerable_bom_components(self, version_obj, limit=9999):
        url = "{}/vulnerable-bom-components".format(version_obj['_meta']['href'])
        custom_headers = {'Accept': 'application/vnd.blackducksoftware.bill-of-materials-6+json'}
        param_string = self._get_parameter_string({'limit': limit})
        url = "{}{}".format(url, param_string)
        response = self.execute_get(url, custom_headers=custom_headers)
        return response.json()

    # TODO: Remove or refactor this
    def get_component_remediation(self, bom_component):
        url = "{}/remediating".format(bom_component['componentVersion'])
        logging.debug("Url for getting remediation info is : {}".format(url))
        response = self.execute_get(url)
        return response.json()

    ##
    #
    # Lookup Black Duck (Hub) KB info given Protex KB info
    #
    ##
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

    valid_notices_formats = ["TEXT", "JSON"]
    def create_version_notices_report(self, version, format="TEXT"):
        assert format in HubInstance.valid_notices_formats, "Format must be one of {}".format(HubInstance.valid_notices_formats)

        post_data = {
            'categories': ["COPYRIGHT_TEXT"],
            'versionId': version['_meta']['href'].split("/")[-1],
            'reportType': 'VERSION_LICENSE',
            'reportFormat': format
        }
        notices_report_url = self.get_link(version, 'licenseReports')
        return self.execute_post(notices_report_url, post_data)

    def download_report(self, report_id):
        # TODO: Fix me, looks like the reports should be downloaded from different paths than the one here, and depending on the type and format desired the path can change
        url = self.get_urlbase() + "/api/reports/{}".format(report_id)
        return self.execute_get(url, {'Content-Type': 'application/zip', 'Accept':'application/zip'})

    def download_notification_report(self, report_location_url):
        '''Download the notices report using the report URL. Inspect the report object to determine
        the format and use the appropriate media header'''
        custom_headers = {'Accept': 'application/vnd.blackducksoftware.report-4+json'}
        response = self.execute_get(report_location_url, custom_headers=custom_headers)
        report_obj = response.json()

        if report_obj['reportFormat'] == 'TEXT':
            download_url = self.get_link(report_obj, "download") + ".json"
            logging.debug("downloading report from {}".format(download_url))
            response = self.execute_get(download_url, {'Accept': 'application/zip'})
        else:
            # JSON
            contents_url = self.get_link(report_obj, "content")
            logging.debug("retrieving report contents from {}".format(contents_url))
            response = self.execute_get(contents_url, {'Accept': 'application/json'})
        return response, report_obj['reportFormat']

    ##
    #
    # (Global) Vulnerability reports
    #
    ##
    valid_vuln_status_report_formats = ["CSV", "JSON"]
    def create_vuln_status_report(self, format="CSV"):
        assert format in HubInstance.valid_vuln_status_report_formats, "Format must be one of {}".format(HubInstance.valid_vuln_status_report_formats)

        post_data = {
            "reportFormat": format,
            "locale": "en_US"
        }
        url = self.get_apibase() + "/vulnerability-status-reports"
        custom_headers = {
            'Content-Type': 'application/vnd.blackducksoftware.report-4+json',
            'Accept': 'application/vnd.blackducksoftware.report-4+json'
        }
        return self.execute_post(url, custom_headers=custom_headers, data=post_data)

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

    def get_file_matches_for_bom_component(self, bom_component, limit=1000):
        self._check_version_compatibility()
        url = self.get_link(bom_component, "matched-files")
        paramstring = self.get_limit_paramstring(limit)
        logging.debug("GET {}".format(url))
        response = self.execute_get(url)
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

    def create_project_version(self, project_obj, new_version_name, clone_version=None, parameters={}):
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
            "phase": version_phase,
            "distribution": parameters.get("distribution", "EXTERNAL")
        }
        if clone_version:
            post_data["cloneFromReleaseUrl"] = clone_version['_meta']['href']
        response = self.execute_post(url, data=post_data)
        return response

    def get_project_by_name(self, project_name):
        project_list = self.get_projects(parameters={"q":"name:{}".format(project_name)})
        for project in project_list['items']:
            if project['name'] == project_name:
                return project

    def get_projects_by_version_name(self, version_name, exclude_projects=None):
        """Returns all project dicts which have given version_name, including the version object under 'version' key
        
        Arguments:
            version_name {str} -- version name to be searched
            exclude_projects {list} -- list of project names to be excluded from scanning for given version name
        """
        headers = self.get_headers()
        projects = self.get_projects(limit=9999).get('items',[])
        if len(projects) == 0:
            logging.error('No projects found')
        else:
            jsondata = {'items':[]}
            for project in projects:
                if project['name'] not in exclude_projects:
                    version = self.get_version_by_name(project, version_name)
                    if version:
                        project['version'] = version
                        jsondata['items'].append(project)
            jsondata['totalCount'] = len(jsondata['items'])
            return jsondata

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
                self.create_project_version(project, version_name, parameters=parameters)
                version = self.get_version_by_name(project, version_name)
        else:
            self.create_project(project_name, version_name, parameters=parameters)
            project = self.get_project_by_name(project_name)
            version = self.get_version_by_name(project, version_name)
        return version

    def get_project_by_id(self, project_id, limit=100):
        headers = self.get_headers()
        paramstring = self.get_limit_paramstring(limit)
        url = self._get_projects_url() + "/" + project_id + paramstring
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
    
    def delete_project_by_name(self, project_name, save_scans=False, backup_scans=False):
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
                    if backup_scans:
                        logging.debug("Backup code locations (aka scans) for version {}".format(version['versionName']))
                        self.download_project_scans(project_name, version['versionName'])
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
        deleted_projects = list()
        for p in projects:
            p_empty = True
            versions = self.get_project_versions(p).get('items', [])
            for v in versions:
                codelocations = self.get_version_codelocations(v)
                if codelocations['totalCount'] != 0:
                    p_empty = False
                    logging.debug("Found a non-empty version in project {}, skipping...".format(
                        p['name']))
                    break
            if p_empty:
                logging.info("Project {} is empty, deleting".format(p['name']))
                self.execute_delete(p['_meta']['href'])
                deleted_projects.append(p['name'])
        return deleted_projects

    def delete_empty_versions(self, project):
        # delete versions within a given project if there are no mapped code locations (scans)
        versions = self.get_project_versions(project).get('items', [])
        logging.debug("Deleting empty versions for project {}".format(project['name']))
        deleted_versions = list()
        for v in versions:
            codelocations = self.get_version_codelocations(v).get('items', [])
            if not codelocations:
                logging.info("Deleting empty version {} from project {}".format(
                    v['versionName'], project['name']))
                self.execute_delete(v['_meta']['href'])
                deleted_versions.append((project['name'], v['versionName']))
            else:
                logging.debug("Version {} within project {} has scans (i.e. not empty), skipping".format(
                    v['versionName'], project['name']))
        return deleted_versions

    def delete_all_empty_versions(self):
        # delete versions if there are no mapped code locations (scans) across all projects
        projects = self.get_projects().get('items', [])
        deleted_versions = list()
        logging.info("Deleting empty versions for all {} projects on this server".format(
            len(projects)))
        for p in projects:
            deleted_versions.extend(self.delete_empty_versions(p))
        return deleted_versions

    def _find_user_group_url(self, assignable_user_groups, user_group_name):
        for user_group in assignable_user_groups['items']:
            if user_group['name'] == user_group_name:
                return user_group['usergroup']

    def _find_user_url(self, assignable_user, user_name):
        for user in assignable_user['items']:
            if user['name'] == user_name:
                return user['user']

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

    def assign_user_to_project(self, user_name, project_name, project_roles, limit=1000):
        # Assign users to projects
        project = self.get_project_by_name(project_name)

        if project:
            project_url = project['_meta']['href']
            assignable_users_link = self.get_link(project, 'assignable-users')
            paramstring = self.get_limit_paramstring(limit)
            url = assignable_users_link + paramstring
            logging.debug("GET {}".format(url))
            if assignable_users_link:
                assignable_users_response = self.execute_get(url)
                assignable_users = assignable_users_response.json()

                # TODO: What to do if the user is already assigned to the project, and therefore
                # does not appear in the list of 'assignable' user? Should we search the (assigned) user
                # and re-apply the project-roles to the assignment?

                user_url = self._find_user_url(assignable_users, user_name)
                if user_url:
                    headers = self.get_headers()

                    # need project role urls to build the POST payload
                    project_roles_urls = self._project_role_urls(project_roles)

                    # The POST endpoint changes based on whether we found any project-roles to assign
                    # Also, due to what appears to be a defect, the Content-Type changes
                    if project_roles_urls:
                        url = user_url + "/roles"
                        # one dict per project role assignment
                        post_data = [{'role': r, 'scope': project_url} for r in project_roles_urls]
                        # I found I had to use this Content-Type (application/json resulted in 412)
                        # ref: https://jira.dc1.lan/browse/HUB-18417
                        headers['Content-Type'] = 'application/vnd.blackducksoftware.internal-1+json'
                    else:
                        url = project_url + "/users"
                        # Assigning a user with no project-roles
                        post_data = {"user": user_url}
                        headers['Content-Type'] = 'application/json'

                    response = requests.post(
                        url,
                        headers=headers,
                        data=json.dumps(post_data),
                        verify=not self.config['insecure'])
                    return response
                else:
                    assignable_username = [u['name'] for u in assignable_users['items']]
                    logging.warning(
                        "The user {} was not found in the assignable user ({}) for this project {}. Is the user already assigned to this project?".format(
                            user_name, assignable_username, project_name))
            else:
                logging.warning("This project {} has no assignable users".format(project_name))
        else:
            logging.warning("Did not find a project by the name {}".format(project_name))

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

    def get_version_scan_info(self, version_obj):
        url = self.get_link(version_obj, "codelocations")
        custom_headers = {'Accept': 'application/vnd.blackducksoftware.project-detail-5+json'}
        response = self.execute_get(url, custom_headers=custom_headers)
        code_locations = response.json().get('items', [])
        if code_locations:
            scan_info = {
                'most_recent_scan': max([cl['updatedAt'] for cl in code_locations]),
                'oldest_scan': min([cl['createdAt'] for cl in code_locations]),
                'number_scans': len(code_locations)
            }
        else:
            scan_info = {
                'most_recent_scan': None,
                'oldest_scan': None,
                'number_scans': None
            }
        return scan_info

    ###
    #
    # Add project version as a component to another project
    # 
    # WARNING: Uses internal API
    ###
    
    # TODO: Refactor this code to use the (newly released, v2019.4.0) public endpoint for adding sub-projects (POST /api/projects/{projectId}/versions/{projectVersionId}/components)
    #       ref: https://jira.dc1.lan/browse/HUB-16972
    
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
    
    def upload_scan(self, filename):
        url = self.get_apibase() + "/scan/data/?mode=replace"
        files = {'file':open(filename,'rb')}
        headers = self.get_headers()
        headers['Content-Type'] = 'application/vnd.blackducksoftware.bdio+zip'
        with open(filename,"rb") as f:
            response = requests.post(url, headers=headers, data=f, verify=False)
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
            matches = [x for x in links if x['rel'] == 'enclosure']
            for m in matches:
                url = m['href']
                filename = url.split('/')[6]
                if output_folder:
                    pathname = os.path.join(output_folder, filename)
                else:
                    if not os.path.exists(project_name):
                        os.mkdir(project_name)
                    pathname = os.path.join(project_name, filename)
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

    ##
    #
    # Component stuff
    #
    ##
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

    def search_components(self, search_str, limit=100, parameters={}):
        if limit:
            parameters.update({'limit':limit})
        url = self.get_apibase() + "/search/components?q=name:{}".format(urllib.parse.quote(search_str))
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


    ##
    #
    # Custom fields
    #
    ##
    def _get_cf_url(self):
        return self.get_apibase() + "/custom-fields/objects"

    def supported_cf_object_types(self):
        '''Get the types and cache them since they are static (on a per-release basis)'''
        if not hasattr(self, "_cf_object_types"):
            logging.debug("retrieving object types")
            self._cf_object_types = [cfo['name'] for cfo in self.get_cf_objects().get('items', [])]
        return self._cf_object_types

    def get_cf_objects(self):
        '''Get CF objects and cache them since these are static (on a per-release basis)'''
        url = self._get_cf_url()
        if not hasattr(self, "_cf_objects"):
            logging.debug("retrieving objects")
            response = self.execute_get(url)
            self._cf_objects = response.json()
        return self._cf_objects

    def _get_cf_object_url(self, object_name):
        for cf_object in self.get_cf_objects().get('items', []):
            if cf_object['name'].lower() == object_name.lower():
                return cf_object['_meta']['href']

    def get_cf_object(self, object_name):
        assert object_name in self.supported_cf_object_types(), "Object name {} not one of the supported types ({})".format(object_name, self.supported_cf_object_types())

        object_url = self._get_cf_object_url(object_name)
        response = self.execute_get(object_url)
        return response.json()

    def _get_cf_obj_rel_path(self, object_name):
        return object_name.lower().replace(" ", "-")

    def create_cf(self, object_name, field_type, description, label, position, active=True, initial_options=[]):
        '''
            Create a custom field for the given object type (e.g. "Project", "Project Version") using the field_type and other parameters.

            Initial options are needed for field types like multi-select where the multiple values to choose from must also be provided.

            initial_options = [{"label":"val1", "position":0}, {"label":"val2", "position":1}]
        '''
        assert isinstance(position, int) and position >= 0, "position must be an integer that is greater than or equal to 0"
        assert field_type in ["BOOLEAN", "DATE", "DROPDOWN", "MULTISELECT", "RADIO", "TEXT", "TEXTAREA"]

        types_using_initial_options = ["DROPDOWN", "MULTISELECT", "RADIO"]

        post_url = self._get_cf_object_url(object_name) + "/fields"
        cf_object = self._get_cf_obj_rel_path(object_name)
        cf_request = {
            "active": active,
            "description": description,
            "label": label,
            "position": position,
            "type": field_type,
        }
        if field_type in types_using_initial_options and initial_options:
            cf_request.update({"initialOptions": initial_options})
        response = self.execute_post(post_url, data=cf_request)
        return response

    def delete_cf(self, object_name, field_id):
        '''Delete a custom field from a given object type, e.g. Project, Project Version, Component, etc

        WARNING: Deleting a custom field is irreversiable. Any data in the custom fields could be lost so use with caution.
        '''
        assert object_name in self.supported_cf_object_types(), "You must supply a supported object name that is in {}".format(self.supported_cf_object_types())

        delete_url = self._get_cf_object_url(object_name) + "/fields/{}".format(field_id)
        return self.execute_delete(delete_url)

    def get_custom_fields(self, object_name):
        '''Get the custom field (definition) for a given object type, e.g. Project, Project Version, Component, etc
        '''
        assert object_name in self.supported_cf_object_types(), "You must supply a supported object name that is in {}".format(self.supported_cf_object_types())

        url = self._get_cf_object_url(object_name) + "/fields"

        response = self.execute_get(url)        
        return response.json()

    def get_cf_values(self, obj):
        '''Get all of the custom fields from an object such as a Project, Project Version, Component, etc

        The obj is expected to be the JSON document for a project, project-version, component, etc
        '''
        url = self.get_link(obj, "custom-fields")
        response = self.execute_get(url)
        return response.json()

    def get_cf_value(self, obj, field_id):
        '''Get a custom field value from an object such as a Project, Project Version, Component, etc

        The obj is expected to be the JSON document for a project, project-version, component, etc
        '''
        url = self.get_link(obj, "custom-fields") + "/{}".format(field_id)
        response = self.execute_get(url)
        return response.json()

    def put_cf_value(self, cf_url, new_cf_obj):
        '''new_cf_obj is expected to be a modified custom field value object with the values updated accordingly, e.g.
        call get_cf_value, modify the object, and then call put_cf_value
        '''
        return self.execute_put(cf_url, new_cf_obj)

    ##
    #
    # General stuff
    #
    ##

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
    # Jobs
    #
    ##
    def get_jobs(self, parameters={}):
        url = self.get_apibase() + "/jobs"
        url = url + self._get_parameter_string(parameters)
        custom_headers = {'Accept': 'application/vnd.blackducksoftware.status-4+json'}
        response = self.execute_get(url, custom_headers=custom_headers)
        return response.json()

    ##
    #
    # Job Statistics
    #
    ##
    def get_job_statistics(self):
        url = self.get_urlbase() + "/api/job-statistics"
        response = self.execute_get(url)
        return response.json()
        
    ##
    #
    # Notifications
    #
    ##
    def get_notifications(self, parameters={}):
        url = self.get_urlbase() + "/api/notifications" + self._get_parameter_string(parameters)
        custom_headers = {'Accept': 'application/vnd.blackducksoftware.notification-4+json'}
        response = self.execute_get(url, custom_headers=custom_headers)
        json_data = response.json()
        return json_data

    ##
    #
    # Licenses
    #
    ##
    def get_licenses(self, parameters={}):
        url = self.get_urlbase() + "/api/licenses" + self._get_parameter_string(parameters)
        response = self.execute_get(url, custom_headers={'Accept':'application/json'})
        json_data = response.json()
        return json_data

    ##
    #
    # General methods including get, put, post, etc
    #
    ##
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


