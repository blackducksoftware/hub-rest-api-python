'''
Created on Jul 6, 2018

@author: kumykov
@contributors: gsnyder2007, AR-Calder

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

logger = logging.getLogger(__name__)

from .Utils import object_id

class HubInstance(object):
    '''
    classdocs
    '''

    from .constants import VERSION_DISTRIBUTION, VERSION_PHASES, PROJECT_VERSION_SETTINGS

    # TODO: What to do about the config file for thread-safety, concurrency
    configfile = ".restconfig.json"
      
    from .Core import (
        _create,_get_hub_rest_api_version_info,_get_major_version,_get_parameter_string,_validated_json_data,
        execute_delete,execute_get,execute_post,execute_put,get_api_version,get_apibase,get_auth_token,get_headers,
        get_limit_paramstring,get_link,get_matched_components,get_tags_url,get_urlbase,read_config,write_config
    )
    from .Roles import (
        _get_role_url, assign_role_given_role_url, assign_role_to_user_or_group, 
        delete_role_from_user_or_group, get_role_url_by_name, get_roles, get_roles_for_user_or_group,
        get_roles_url_from_user_or_group, user_has_role
    )
    from .Users import (
        _get_user_url, create_user, delete_user_by_id, delete_user_by_url, get_current_user,
        get_last_login, get_user_by_id, get_user_by_url, get_users, reset_user_password, update_user_by_id, 
        update_user_by_url
    )
    from .UserGroup import (
        _get_user_group_url, create_user_group, create_user_group_by_name, 
        delete_user_group_by_id, delete_user_group_by_url, get_user_group_by_name, get_user_groups, 
        update_user_group_by_id, update_user_group_by_url
    )
    from .Policy import (
        _get_policy_url, create_policy, delete_policy_by_id, delete_policy_by_url, 
        get_policies, get_policy_by_id, get_policy_by_url, update_policy_by_id, update_policy_by_url
    )
    from .Vulnerabilities import (
        _get_vulnerabilities_url, get_component_remediation, get_vulnerabilities, 
        get_vulnerability_affected_projects, get_vulnerable_bom_components
    )
    from .Reporting import (
        create_version_notices_report, create_version_reports, create_vuln_status_report, 
        download_notification_report, download_report
    )
    from .Projects import (
        _find_user_group_url, _find_user_url, _get_projects_url, _project_role_urls, 
        assign_project_application_id, assign_user_group_to_project, assign_user_to_project, 
        compare_project_versions, create_project, create_project_version, delete_all_empty_versions, 
        delete_application_id, delete_empty_projects, delete_empty_versions, delete_project_by_name, 
        delete_project_version_by_name, delete_project_version_codelocations, delete_user_group_from_project, 
        get_or_create_project_version, get_project_application_id, get_project_by_id, get_project_by_name, 
        get_project_info, get_project_roles, get_project_version_by_name, get_project_versions, get_projects, 
        get_projects_by_version_name, get_version_by_id, get_version_by_name, get_version_codelocations, 
        get_version_components, get_version_scan_info, update_project_application_id, update_project_settings, 
        update_project_version_settings
    ) # TODO Transfer relevant versions related functions to .Versions
    from .Versions import ( add_version_as_component, remove_version_as_component )
    from .Scans import (
        delete_codelocation, delete_unmapped_codelocations, download_project_scans, 
        get_codelocation_scan_summaries, get_codelocations, get_scan_locations, upload_scan
    )
    from .Components import (
        _get_components_url, find_component_info_for_protex_component, get_component_by_id, 
        get_component_by_url, get_components, search_components, update_component_by_id, update_component_by_url
    )
    from .CustomFields import (
        _get_cf_obj_rel_path, _get_cf_object_url, _get_cf_url, create_cf, delete_cf, 
        get_cf_object, get_cf_objects, get_cf_value, get_cf_values, get_custom_fields, put_cf_value,
        supported_cf_object_types
    )
    from .Licences import ( _get_license_info, get_license_info_for_bom_component, get_licenses )
    from .System import ( get_health_checks, get_notifications )
    from .Ldap import ( disable_ldap, enable_ldap, get_ldap_configs, get_ldap_state )

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
            logger.debug(f"Reading connection and authentication info from {self.configfile}")
        
        self.token, self.csrf_token, self.cookie = self.get_auth_token()
        try:
            self.version_info = self._get_hub_rest_api_version_info()
        except UnknownVersion:
            self.version_info = {'version': '3'} # assume it's v3 since all versions after 3 supported version info

        self.bd_major_version = self._get_major_version()

    def print_methods(self):
        import inspect
        for fn in inspect.getmembers(self, predicate=inspect.isfunction):
            print(fn[0])
