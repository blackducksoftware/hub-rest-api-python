#!/usr/bin/env python

import copy
import json
import os
import pytest
import re
from urllib.parse import urlparse

from blackduck.HubRestApi import HubInstance
from unittest.mock import patch, MagicMock, mock_open


fake_hub_host = "https://my-hub-host"


def return_auth_token(api_token):
    if api_token:
        return ("the-token", "the-csrf-token")
    else:
        return ("the-token", None)

invalid_bearer_token="anInvalidTokenValue"
invalid_csrf_token="anInvalidCSRFTokenValue"
made_up_api_token="theMadeUpAPIToken"

def setup_function(function):
    # Remove .restconfig file before running any test
    try:
        os.remove(HubInstance.configfile)
    except OSError:
        pass

def teardown_function(function):
    # Remove .restconfig file after running any test
    try:
        os.remove(HubInstance.configfile)
    except OSError:
        pass
        
@pytest.fixture()
def mock_hub_instance(requests_mock):
    requests_mock.post(
        "{}/j_spring_security_check".format(fake_hub_host), 
        headers={"Set-Cookie": 'AUTHORIZATION_BEARER={}; Path=/; secure; Secure; HttpOnly'.format(invalid_bearer_token)}
    )
    requests_mock.get(
        "{}/api/current-version".format(fake_hub_host),
        json = {
            "version": "2018.11.0",
            "_meta": {
                "allow": [
                    "GET"
                ],
                "href": "{}/api/current-version".format(fake_hub_host)
            }
        }
    )
    yield HubInstance(fake_hub_host, "a_username", "a_password")

@pytest.fixture()
def mock_hub_instance_using_api_token(requests_mock):
    requests_mock.post(
        "https://my-hub-host/api/tokens/authenticate", 
        content = json.dumps({'bearerToken': invalid_bearer_token}).encode('utf-8'),
        headers={
                'X-CSRF-TOKEN': invalid_csrf_token, 
                'Content-Type': 'application/json'
            }
    )
    requests_mock.get(
        "{}/api/current-version".format(fake_hub_host),
        json = {
            "version": "2018.11.0",
            "_meta": {
                "allow": [
                    "GET"
                ],
                "href": "{}/api/current-version".format(fake_hub_host)
            }
        }
    )

    yield HubInstance(fake_hub_host, api_token=made_up_api_token)

@pytest.fixture()
def policy_info_json(shared_datadir):
    yield json.load((shared_datadir / "policies.json").open())

@pytest.fixture()
def a_test_policy(policy_info_json):
    test_policy = policy_info_json['items'][0]
    yield test_policy

@pytest.fixture()
def a_test_policy_for_create_or_update(a_test_policy):
        # a_policy_for_creating_or_updating = dict(
        #     (attr, test_policy[attr]) for attr in 
        #     ['name', 'description', 'enabled', 'overridable', 'expression', 'severity'] if attr in test_policy)
        # yield a_policy_for_creating_or_updating
        yield a_test_policy

@pytest.fixture()
def test_vulnerability_info(requests_mock, shared_datadir):
    yield json.loads((shared_datadir / "sample-vulnerability.json").read_text())

def test_get_major_version(requests_mock):
    requests_mock.post(
        "{}/j_spring_security_check".format(fake_hub_host), 
        headers={"Set-Cookie": 'AUTHORIZATION_BEARER={}; Path=/; secure; Secure; HttpOnly'.format(invalid_bearer_token)}
    )
    for version in ["2018.11.0", "5.0.2", "4.8.3", "3.7.2"]:
        expected = version.split(".")[0]
        requests_mock.get(
            "{}/api/current-version".format(fake_hub_host),
            json = {
                "version": "{}".format(version),
                "_meta": {
                    "allow": [
                        "GET"
                    ],
                    "href": "{}/api/current-version".format(fake_hub_host)
                }
            }
        )
        hub = HubInstance(fake_hub_host, "a_username", "a_password")
        assert hub.bd_major_version == expected

def test_get_headers(mock_hub_instance):
    # somewhat contrived, but it does execute all the paths
    # TODO: better way to test this one?
    #
    the_api_token = "fake-api-token"
    the_csrf_token = "fake-csrf-token"
    the_token = "fake-bearer-token"
    mock_hub_instance.config['api_token'] = the_api_token
    mock_hub_instance.csrf_token = the_csrf_token
    mock_hub_instance.token = the_token

    assert mock_hub_instance.get_headers() == {
                'X-CSRF-TOKEN': the_csrf_token, 
                'Authorization': "Bearer {}".format(the_token),
                'Content-Type': 'application/json',
                'Accept': 'application/json'}

    del mock_hub_instance.config['api_token']
    for bd_major_version in ["2018", "5", "4", "3"]:
        if bd_major_version == "3":
            expected =  {"Cookie": mock_hub_instance.cookie}
        else:
            expected =  {"Authorization":"Bearer " + mock_hub_instance.token}

        mock_hub_instance.bd_major_version = bd_major_version
        assert mock_hub_instance.get_headers() == expected

def test_get_policy_url(mock_hub_instance):
    assert mock_hub_instance._get_policy_url() == fake_hub_host + "/api/policy-rules"

def test_get_parameter_string(mock_hub_instance):
    assert mock_hub_instance._get_parameter_string({"limit":"100"}) == "?limit=100"
    assert mock_hub_instance._get_parameter_string({"limit":"100", "q":"name:my-name"}) == "?limit=100&q=name%3Amy-name"
    assert mock_hub_instance._get_parameter_string({"limit":"100", "sort":"updatedAt"}) == "?limit=100&sort=updatedAt"

def test_hub_instance_username_password_for_auth(mock_hub_instance):
    assert mock_hub_instance.get_headers() == {"Authorization":"Bearer {}".format(invalid_bearer_token)}

    assert 'api_token' not in mock_hub_instance.config
    assert 'baseurl' in mock_hub_instance.config
    assert 'username' in mock_hub_instance.config
    assert 'password' in mock_hub_instance.config

def test_hub_instance_api_token_for_auth(mock_hub_instance_using_api_token):
    assert mock_hub_instance_using_api_token.get_headers() == {
                'X-CSRF-TOKEN': invalid_csrf_token, 
                'Authorization': 'Bearer {}'.format(invalid_bearer_token), 
                'Content-Type': 'application/json',
                'Accept': 'application/json'}

    assert 'api_token' in mock_hub_instance_using_api_token.config
    assert 'baseurl' in mock_hub_instance_using_api_token.config
    assert 'username' not in mock_hub_instance_using_api_token.config
    assert 'password' not in mock_hub_instance_using_api_token.config

def test_hub_instance_with_write_config(requests_mock):
    requests_mock.post(
        "https://my-hub-host/j_spring_security_check", 
        headers={"Set-Cookie": 'AUTHORIZATION_BEARER={}; Path=/; secure; Secure; HttpOnly'.format(invalid_bearer_token)}
    )
    requests_mock.get(
        "{}/api/current-version".format(fake_hub_host),
        json = {
            "version": "2018.11.0",
            "_meta": {
                "allow": [
                    "GET"
                ],
                "href": "{}/api/current-version".format(fake_hub_host)
            }
        }
    )
    
    with patch("builtins.open", new_callable=mock_open()) as m:
        with patch('json.dump') as m_json:
            hub = HubInstance(fake_hub_host, "a_username", "a_password")

            m.assert_called_with('.restconfig.json', 'w')
            assert m_json.called

def test_hub_instance_with_write_config_false(requests_mock):
    requests_mock.post(
        "https://my-hub-host/j_spring_security_check", 
        headers={"Set-Cookie": 'AUTHORIZATION_BEARER={}; Path=/; secure; Secure; HttpOnly'.format(invalid_bearer_token)}
    )
    requests_mock.get(
        "{}/api/current-version".format(fake_hub_host),
        json = {
            "version": "2018.11.0",
            "_meta": {
                "allow": [
                    "GET"
                ],
                "href": "{}/api/current-version".format(fake_hub_host)
            }
        }
    )

    with patch.object(HubInstance, "write_config") as mock_write_config:
        hub = HubInstance(fake_hub_host, "a_username", "a_password", write_config_flag=False)

        assert not mock_write_config.called

def test_get_policy_by_id(requests_mock, mock_hub_instance, a_test_policy):
    requests_mock.get(fake_hub_host + "/api/policy-rules/00000000-0000-0000-0000-000000000001", json=a_test_policy)
    policy = mock_hub_instance.get_policy_by_id("00000000-0000-0000-0000-000000000001")
    for key in a_test_policy.keys():
        assert policy[key] == a_test_policy[key]

def test_get_policy_by_url(requests_mock, mock_hub_instance, a_test_policy):
    requests_mock.get(fake_hub_host + "/api/policy-rules/00000000-0000-0000-0000-000000000001", json=a_test_policy)
    policy = mock_hub_instance.get_policy_by_url(mock_hub_instance._get_policy_url() + "/00000000-0000-0000-0000-000000000001")
    for key in a_test_policy.keys():
        assert policy[key] == a_test_policy[key]

def test_update_policy_by_id(requests_mock, mock_hub_instance, a_test_policy, a_test_policy_for_create_or_update):
    policy_id = a_test_policy['_meta']['href'].split("/")[-1]

    requests_mock.put(fake_hub_host + "/api/policy-rules/" + policy_id,
        json=a_test_policy
    )
    response = mock_hub_instance.update_policy_by_id(policy_id, a_test_policy_for_create_or_update)
    assert response.status_code == 200
    assert response.json() == a_test_policy

def test_update_policy_by_url(requests_mock, mock_hub_instance, a_test_policy, a_test_policy_for_create_or_update):
    policy_id = a_test_policy['_meta']['href'].split("/")[-1]
    policy_url = mock_hub_instance._get_policy_url() + "/" + policy_id

    requests_mock.put(fake_hub_host + "/api/policy-rules/" + policy_id,
        json=a_test_policy
    )
    response = mock_hub_instance.update_policy_by_url(policy_url, a_test_policy_for_create_or_update)
    assert response.status_code == 200
    assert response.json() == a_test_policy

def test_create_policy(requests_mock, mock_hub_instance, a_test_policy, a_test_policy_for_create_or_update):
    requests_mock.post(fake_hub_host + "/api/policy-rules", headers={"location": a_test_policy['_meta']['href']}, status_code=201)
    # print(json.dumps(a_test_policy_for_create_or_update))
    new_policy_url = mock_hub_instance.create_policy(a_test_policy_for_create_or_update)
    assert new_policy_url == a_test_policy['_meta']['href']

def test_delete_policy_by_id(requests_mock, mock_hub_instance, a_test_policy):
    policy_id = a_test_policy['_meta']['href'].split("/")[-1]

    requests_mock.delete(fake_hub_host + "/api/policy-rules/" + a_test_policy['_meta']['href'].split("/")[-1], status_code=204)
    response = mock_hub_instance.delete_policy_by_id(policy_id)
    assert response.status_code == 204

def test_delete_policy_by_url(requests_mock, mock_hub_instance, a_test_policy):
    policy_url = mock_hub_instance._get_policy_url() + "/" + a_test_policy['_meta']['href'].split("/")[-1]

    requests_mock.delete(policy_url, status_code=204)
    response = mock_hub_instance.delete_policy_by_url(policy_url)
    assert response.status_code == 204

def test_get_vulnerability(requests_mock, mock_hub_instance, test_vulnerability_info):
    vulnerability_url = mock_hub_instance._get_vulnerabilities_url() + "/{}".format(test_vulnerability_info['vulnerabilityName'])

    requests_mock.get(vulnerability_url, json=test_vulnerability_info)
    response_json = mock_hub_instance.get_vulnerabilities(test_vulnerability_info['vulnerabilityName'])

    assert response_json == test_vulnerability_info

def test_get_projects_with_limit(requests_mock, mock_hub_instance, shared_datadir):
    url = mock_hub_instance.get_urlbase() + "/api/projects?limit=20"
    json_data = json.load((shared_datadir / 'sample-projects.json').open())
    requests_mock.get(url, json=json_data)
    projects = mock_hub_instance.get_projects(limit=20)

    assert json_data == projects
    assert 'totalCount' in projects
    assert projects['totalCount'] == 18

def test_get_projects_with_name_query(requests_mock, mock_hub_instance, shared_datadir):
    url = mock_hub_instance.get_urlbase() + "/api/projects?q=name:accelerator-initializer-ui&limit=100"
    json_data = json.load((shared_datadir / 'sample-projects-using-name-query.json').open())
    requests_mock.get(url, json=json_data)
    projects = mock_hub_instance.get_projects(parameters={'q':"name:accelerator-initializer-ui"})

    assert json_data == projects
    assert 'totalCount' in projects
    assert projects['totalCount'] == 1

def test_get_project_versions(requests_mock, mock_hub_instance, shared_datadir):
    baseurl = mock_hub_instance.get_urlbase()
    url = baseurl + "/api/projects/65f272df-3a2a-4022-8811-a57e05e82f52/versions?limit=100"
    json_data = json.load((shared_datadir / 'sample-project-versions.json').open())
    project_json_data = json.load((shared_datadir / 'sample-project.json').open())
    # replace project URL with the right one to agree with our mocked URL above
    project_json_data['_meta']['href'] = re.sub("https://.*/api", "{}/api".format(baseurl), project_json_data['_meta']['href'])
    requests_mock.get(url, json=json_data)
    versions = mock_hub_instance.get_project_versions(project_json_data)

    assert 'totalCount' in versions
    assert versions['totalCount'] == 1

def test_get_project_versions_with_parameters(requests_mock, mock_hub_instance, shared_datadir):
    baseurl = mock_hub_instance.get_urlbase()
    url = baseurl + "/api/projects/65f272df-3a2a-4022-8811-a57e05e82f52/versions?limit=100&q=versionName:1.0"
    json_data = json.load((shared_datadir / 'sample-project-versions.json').open())
    project_json_data = json.load((shared_datadir / 'sample-project.json').open())
    # replace project URL with the right one to agree with our mocked URL above
    project_json_data['_meta']['href'] = re.sub("https://.*/api", "{}/api".format(baseurl), project_json_data['_meta']['href'])
    requests_mock.get(url, json=json_data)
    versions = mock_hub_instance.get_project_versions(project_json_data, parameters={'q':'versionName:1.0'})

    assert 'totalCount' in versions
    assert versions['totalCount'] == 1
    assert 'items' in versions

def test_delete_project_version_by_name():
    # TODO: Write this test
    pass


def test_get_users(requests_mock, mock_hub_instance, shared_datadir):
    baseurl = mock_hub_instance.get_urlbase()
    url = baseurl + "/api/users"
    user_json_data = json.load((shared_datadir / "users.json").open())
    requests_mock.get(url, json=user_json_data)
    users = mock_hub_instance.get_users()

    assert 'totalCount' in users
    assert users['totalCount'] == 1 # cause there was one user in the sample data collected
    assert 'items' in users

def test_create_user(requests_mock, mock_hub_instance):
    pass

def test_get_user_by_id(requests_mock, mock_hub_instance):
    pass

def test_get_user_by_url(requests_mock, mock_hub_instance):
    pass

def test_update_user_by_id(requests_mock, mock_hub_instance):
    pass

def test_update_user_by_url(requests_mock, mock_hub_instance):
    pass

def test_delete_user_by_id(requests_mock, mock_hub_instance):
    pass

def test_delete_user_by_url(requests_mock, mock_hub_instance):
    pass
    
def test_get_project_by_name(requests_mock, mock_hub_instance, shared_datadir):
    url = mock_hub_instance.get_urlbase() + "/api/projects"
    projects_json = json.load((shared_datadir / "sample-projects.json").open())
    project_name = "accelerator-initializer-ui"
    requests_mock.get(url, json=projects_json)

    project = mock_hub_instance.get_project_by_name(project_name)

    assert project['name'] == project_name

def test_get_version_by_name(requests_mock, mock_hub_instance, shared_datadir):
    mock_hub_instance.get_project_versions = MagicMock(return_value=json.load((shared_datadir / "sample-project-versions.json").open()))

    mock_project_obj = MagicMock()
    version_name = "1.0" # a version that exists in sample-project-versions.json
    version = mock_hub_instance.get_version_by_name(mock_project_obj, version_name)

    assert version['versionName'] == version_name

def test_create_version_reports(requests_mock, mock_hub_instance):
    pass

def test_create_version_notices_report(requests_mock, mock_hub_instance):
    pass

@pytest.fixture()
def sample_bom_component_json(shared_datadir):
    yield json.load((shared_datadir / "sample-bom-component.json").open())

@pytest.fixture()
def no_roles_user(shared_datadir):
    yield json.load((shared_datadir / 'no-roles-user.json').open())

@pytest.fixture()
def no_roles_roles(shared_datadir):
    yield json.load((shared_datadir / 'no-roles-roles.json').open())

@pytest.fixture()
def sysadmin_user(shared_datadir):
    yield json.load((shared_datadir / 'sysadmin-user.json').open())

@pytest.fixture()
def sysadmin_roles(shared_datadir):
    yield json.load((shared_datadir / 'sysadmin-roles.json').open())

def test_user_has_role(no_roles_user, no_roles_roles, sysadmin_user, sysadmin_roles, mock_hub_instance):
    test_roles = [
        'License Manager', 
        'System Administrator', 
        'Policy Manager', 
        'Project Viewer', 
        'Global Code Scanner', 
        'Project Manager']
    
    mock_hub_instance.get_roles_for_user_or_group = MagicMock()
    mock_hub_instance.get_roles_for_user_or_group.return_value = no_roles_roles

    for test_role in test_roles:
        assert mock_hub_instance.user_has_role(no_roles_user, test_role) == False

    mock_hub_instance.get_roles_for_user_or_group.return_value = sysadmin_roles

    for test_role in test_roles:
        assert mock_hub_instance.user_has_role(sysadmin_user, test_role) == True

def test_get_link(mock_hub_instance):
    a_url = 'http://a-url'
    link_name = 'a_link_name'
    bd_rest_obj = {'_meta':{'links': [{'rel': link_name, 'href': a_url}]}}

    assert mock_hub_instance.get_link(bd_rest_obj, link_name) == a_url

def test_get_link_returns_None_for_invalid_bd_rest_object(mock_hub_instance):
    bd_rest_obj = {}

    assert mock_hub_instance.get_link(bd_rest_obj, 'a_link_name') == None

def test_validated_json_with_a_dictionary(mock_hub_instance):
    validated_json = mock_hub_instance._validated_json_data({'key':'value'})
    assert isinstance(validated_json, str)
    assert validated_json == '{"key": "value"}'

def test_validated_json_with_a_list(mock_hub_instance):
    validated_json = mock_hub_instance._validated_json_data(['item1', 'item2'])
    assert isinstance(validated_json, str)
    assert validated_json == '["item1", "item2"]'

def test_validated_json_with_a_json_str(mock_hub_instance):
    validated_json = mock_hub_instance._validated_json_data('{"key": "value"}')

    assert validated_json == '{"key": "value"}'

def test_validated_json_fails_with_invalid_json_str(mock_hub_instance):
    from json import JSONDecodeError

    with pytest.raises(JSONDecodeError) as e_info:
        validated_json = mock_hub_instance._validated_json_data('invalid json')

@pytest.fixture()
def code_locations(requests_mock, shared_datadir):
    data = json.load((shared_datadir / 'code_locations.json').open())
    requests_mock.get(
        "{}/api/codelocations?limit=100".format(fake_hub_host),
        json = data
    )
    yield data

def test_get_codelocations_all(mock_hub_instance, code_locations):
    code_locs = mock_hub_instance.get_codelocations()

    assert code_locs == code_locations

def test_get_codelocations_unmapped(mock_hub_instance, code_locations):
    code_locs = mock_hub_instance.get_codelocations(unmapped=True)

    assert code_locs != code_locations

    expected_data = copy.deepcopy(code_locations)
    expected_data['items'] = [cl for cl in code_locations['items'] if 'mappedProjectVersion' not in cl]
    expected_data['totalCount'] = len(expected_data['items'])

    assert code_locs == expected_data


