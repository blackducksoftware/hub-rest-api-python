import logging
import requests
import json
from operator import itemgetter
import urllib.parse

from .Exceptions import InvalidVersionPhase

logger = logging.getLogger(__name__)

# VERSION_DISTRIBUTION=["EXTERNAL", "SAAS", "INTERNAL", "OPENSOURCE"]
# VERSION_PHASES = ["PLANNING", "DEVELOPMENT", "PRERELEASE", "RELEASED", "DEPRECATED", "ARCHIVED"]
# PROJECT_VERSION_SETTINGS = ['nickname', 'releaseComments', 'versionName', 'phase', 'distribution', 'releasedOn']
from .constants import VERSION_DISTRIBUTION, VERSION_PHASES, PROJECT_VERSION_SETTINGS

def _get_projects_url(self):
    return self.get_urlbase() + "/api/projects"

def get_projects(self, limit=100, parameters={}):
    headers = self.get_headers()
    if limit:
        parameters.update({'limit': limit})
    url = self._get_projects_url() + self._get_parameter_string(parameters)
    headers['Accept'] = 'application/vnd.blackducksoftware.project-detail-4+json'
    logger.debug(f"Retrieving projects using url {url}")
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
    if version_phase not in VERSION_PHASES:
        raise InvalidVersionPhase("The phase given {} is not in the list of valid phases ({})".format(
            version_phase, VERSION_PHASES))

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
        logger.error('No projects found')
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
            logger.debug("Did not find any project version matching {}".format(version_name))
        else:
            return version
    else:
        logger.debug("Did not find a project with name {}".format(project_name))

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
    headers['Accept'] = 'application/vnd.blackducksoftware.bill-of-materials-6+json'
    response = requests.get(url, headers=headers, verify = not self.config['insecure'])
    jsondata = response.json()
    return jsondata

def update_project_settings(self, project, new_settings={}):
    url = project['_meta']['href']
    headers = self.get_headers()
    headers['Accept'] = 'application/vnd.blackducksoftware.project-detail-4+json'
    headers['Content-Type'] = 'application/vnd.blackducksoftware.project-detail-4+json'
    response = self.execute_put(url, new_settings, headers)
    return response

def update_project_version_settings(self, project_name, version_name, new_settings={}):
    # Apply any new settings to the given project version
    version = self.get_project_version_by_name(project_name, version_name)

    if version:
        for k,v in new_settings.items():
            if k in PROJECT_VERSION_SETTINGS:
                logger.debug("updating setting {} in version {} with value {}".format(
                    k, version['versionName'], v))
                version[k] = v
            else:
                logger.warn("Setting {} is not in the list of project version settings ({})".format(
                    k, PROJECT_VERSION_SETTINGS))

        url = version['_meta']['href']

        response = self.execute_put(url, version)

        if response.status_code == 200:
            logger.info("Successfully updated version {} with new settings {}".format(
                version['versionName'], new_settings))
        else:
            logger.error("Failed to update version {} with new settings {}; status code: {}".format(
                version['versionName'], new_settings, response.status_code))
    else:
        logger.debug("Did not find a matching project-version in project {}, version name {}".format(
            project_name, version_name))

def get_version_by_id(self, project_id, version_id, limit=100):
    headers = self.get_headers()
    paramstring = self.get_limit_paramstring(limit)
    url = self._get_projects_url() + "/" + project_id + "/versions/" + version_id
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
        logger.debug("found project {}".format(project))
        project_versions = self.get_project_versions(
            project, 
            parameters={'q':"versionName:{}".format(version_name)}
        )

        project_version_codelocations = None
        if 'totalCount' in project_versions and project_versions['totalCount'] == 1:
            project_version = project_versions['items'][0]
            logger.debug("found the project version: {}".format(project_version))

            delete_scans = not save_scans
            logger.debug("delete_scans was {}".format(delete_scans))

            if delete_scans:
                self.delete_project_version_codelocations(project_version)
            else:
                logger.debug("Delete scans was false, or we did not find any codelocations (scans) in version {} of project {}".format(version_name, project_name))
            # TODO: Check if the project will be "empty" once we delete this version and
            # delete the project accordingly?
            logger.info("Deleting project-version at: {}".format(project_version['_meta']['href']))
            self.execute_delete(project_version['_meta']['href'])
        else:
            logger.debug("Did not find version with name {} in project {}".format(version_name, project_name))
    else:
        logger.debug("Did not find project with name {}".format(project_name))

def delete_project_by_name(self, project_name, save_scans=False, backup_scans=False):
    project = self.get_project_by_name(project_name)
    if project:
        # get project versions
        project_versions = self.get_project_versions(project)
        versions = project_versions.get('items', [])
        logger.debug("Retrieved {} versions for project {}".format(len(versions), project_name))
        
        delete_scans = not save_scans
        logger.debug("delete_scans was {}".format(delete_scans))
            
        if delete_scans:
            # delete all code locations associated with each version
            for version in versions:
                if backup_scans:
                    logger.debug("Backup code locations (aka scans) for version {}".format(version['versionName']))
                    self.download_project_scans(project_name, version['versionName'])
                logger.debug("Deleting code locations (aka scans) for version {}".format(version['versionName']))
                self.delete_project_version_codelocations(version)
                    
        # delete the project itself
        project_url = project['_meta']['href']
        logger.info("Deleting project {}".format(project_name))
        self.execute_delete(project_url)
    else:
        logger.debug("Did not find project with name {}".format(project_name))
        
def delete_project_version_codelocations(self, version):
    version_name = version['versionName']
    try:
        logger.debug("Retrieving code locations (aka scans) for version {}".format(version_name))
        version_code_locations = self.get_version_codelocations(version)
    except:
        logger.error("Failed to get codelocations (aka scans) for version {}".format(version_name), exc_info=True)
        version_code_locations = []
    else:
        version_code_locations = version_code_locations.get('items', []) if version_code_locations else []
    logger.debug("Found {} code locations (aka scans) for version {}".format(len(version_code_locations), version_name))
    code_location_urls = [c['_meta']['href'] for c in version_code_locations]
    for code_location_url in code_location_urls:
        logger.info("Deleting code location at: {}".format(code_location_url))
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
                logger.debug("Found a non-empty version in project {}, skipping...".format(
                    p['name']))
                break
        if p_empty:
            logger.info("Project {} is empty, deleting".format(p['name']))
            self.execute_delete(p['_meta']['href'])
            deleted_projects.append(p['name'])
    return deleted_projects

def delete_empty_versions(self, project):
    # delete versions within a given project if there are no mapped code locations (scans)
    versions = self.get_project_versions(project).get('items', [])
    logger.debug("Deleting empty versions for project {}".format(project['name']))
    deleted_versions = list()
    for v in versions:
        codelocations = self.get_version_codelocations(v).get('items', [])
        if not codelocations:
            logger.info("Deleting empty version {} from project {}".format(
                v['versionName'], project['name']))
            self.execute_delete(v['_meta']['href'])
            deleted_versions.append((project['name'], v['versionName']))
        else:
            logger.debug("Version {} within project {} has scans (i.e. not empty), skipping".format(
                v['versionName'], project['name']))
    return deleted_versions

def delete_all_empty_versions(self):
    # delete versions if there are no mapped code locations (scans) across all projects
    projects = self.get_projects().get('items', [])
    deleted_versions = list()
    logger.info("Deleting empty versions for all {} projects on this server".format(
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
            assignable_user_groups_response = self.execute_get(f"{assignable_user_groups_link}?q=name:{user_group_name}")
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
                logger.warning("The user group {} was not found in the assignable user groups ({}) for this project {}. Is the group already assigned to this project?".format(
                    user_group_name, assignable_groups, project_name))
        else:
            logger.warning("This project {} has no assignable user groups".format(project_name))
    else:
        logger.warning("Did not find a project by the name {}".format(project_name))

def delete_user_group_from_project(self, project_name, user_group_name):
    project = self.get_project_by_name(project_name)
    
    if project:
        project_url = project['_meta']['href']
        
        user_group = self.get_user_group_by_name(user_group_name)
        if user_group:
            user_group_url = user_group['_meta']['href']
            user_group_id = user_group_url.rsplit('/', 1)[-1]
        
            project_user_group_url = f"{project_url}/usergroups/{user_group_id}"
            self.execute_delete(project_user_group_url)    

def assign_user_to_project(self, user_name, project_name, project_roles, limit=1000):
    # Assign users to projects
    project = self.get_project_by_name(project_name)

    if project:
        project_url = project['_meta']['href']
        assignable_users_link = self.get_link(project, 'assignable-users')
        paramstring = self.get_limit_paramstring(limit)
        url = assignable_users_link + paramstring
        logger.debug("GET {}".format(url))
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
                logger.warning(
                    "The user {} was not found in the assignable user ({}) for this project {}. Is the user already assigned to this project?".format(
                        user_name, assignable_username, project_name))
        else:
            logger.warning("This project {} has no assignable users".format(project_name))
    else:
        logger.warning("Did not find a project by the name {}".format(project_name))

def assign_project_application_id(self, project_name, application_id, overwrite=False):
    logger.debug("Assigning application_id {} to project_name {}, overwrite={}".format(
        application_id, project_name, overwrite))

    existing_application_id, application_id_url = self.get_project_application_id(project_name)

    if existing_application_id:
        if overwrite:
            logger.debug("Found an existing application id {} for project {} and overwrite was True. Updating it to {}".format(
                existing_application_id, project_name, application_id))
            return self.update_project_application_id(project_name, application_id)
        else:
            logger.debug("Found an existing application id {} for project {} and overwrite was False so not updating it".format(
                existing_application_id, project_name))
    else:
        logger.debug("No application id exists for project {}, assigning {} to it".format(
            project_name, application_id))
        project = self.get_project_by_name(project_name)
        if project:
            project_mappings_url = self.get_link(project, "project-mappings")
            if project_mappings_url:
                post_data = {"applicationId": application_id}
                response = self.execute_post(project_mappings_url, data=post_data)
                return response
            else:
                logger.warning("Did not find project-mappings URL for project {}".format(project))
        else:
            logger.warning("Did not find project by name {}".format(project_name))

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
        logger.debug("Did not find application id for project name {}".format(project_name))

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
        logger.debug("Did not find any project-mappings with 'applicationId' in them")
        return (None, None)
    else:
        logger.debug("did not find any project-mappings for project {}".format(project_name))
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
