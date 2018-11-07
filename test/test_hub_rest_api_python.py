#!/usr/bin/env python

import json
import pytest
from blackduck.HubRestApi import HubInstance
from unittest.mock import patch, MagicMock, mock_open


fake_hub_host = "https://my-hub-host"

policies_json_file = open("policies.json")
policies = json.loads(policies_json_file.read())
assert 'items' in policies
test_policy = policies['items'][0]

def return_auth_token(api_token):
    if api_token:
        return ("the-token", "the-csrf-token")
    else:
        return ("the-token", None)

invalid_bearer_token="anInvalidTokenValue"
invalid_csrf_token="anInvalidCSRFTokenValue"

@pytest.fixture()
def mock_hub_instance(requests_mock):
    requests_mock.post(
        "https://my-hub-host/j_spring_security_check", 
        headers={"Set-Cookie": 'AUTHORIZATION_BEARER={}; Path=/; secure; Secure; HttpOnly'.format(invalid_bearer_token)}
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

    yield HubInstance(fake_hub_host, api_token=invalid_bearer_token)

@pytest.fixture()
def policy_info_json(requests_mock):
    with open("policies.json") as policies_json_file:
        yield json.loads(policies_json_file.read())

@pytest.fixture()
def a_test_policy(requests_mock):
    yield test_policy

@pytest.fixture()
def a_test_policy_for_create_or_update(requests_mock):
        a_policy_for_creating_or_updating = dict(
            (attr, test_policy[attr]) for attr in 
            ['name', 'description', 'enabled', 'overridable', 'expression', 'severity'] if attr in test_policy)
        yield a_policy_for_creating_or_updating

def test_get_policy_url(mock_hub_instance):
    assert mock_hub_instance._get_policy_url() == fake_hub_host + "/api/policy-rules"

def test_get_parameter_string(mock_hub_instance):
    assert mock_hub_instance._get_parameter_string({"limit":"100"}) == "?limit=100"
    assert mock_hub_instance._get_parameter_string({"limit":"100", "q":"name:my-name"}) == "?limit=100&q=name:my-name"
    assert mock_hub_instance._get_parameter_string({"limit":"100", "sort":"updatedAt"}) == "?limit=100&sort=updatedAt"

def test_hub_instance_username_password_for_auth(mock_hub_instance):
    assert mock_hub_instance.get_headers() == {"Authorization":"Bearer {}".format(invalid_bearer_token)}

def test_hub_instance_api_token_for_auth(mock_hub_instance_using_api_token):
    assert mock_hub_instance_using_api_token.get_headers() == {
                'X-CSRF-TOKEN': invalid_csrf_token, 
                'Authorization': 'Bearer {}'.format(invalid_bearer_token), 
                'Content-Type': 'application/json'}

def test_hub_instance_with_write_config(requests_mock):
    requests_mock.post(
        "https://my-hub-host/j_spring_security_check", 
        headers={"Set-Cookie": 'AUTHORIZATION_BEARER={}; Path=/; secure; Secure; HttpOnly'.format(invalid_bearer_token)}
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
    with patch.object(HubInstance, "write_config") as mock_write_config:
        hub = HubInstance(fake_hub_host, "a_username", "a_password", write_config_flag=False)

        assert not mock_write_config.called

def test_get_policy_by_id(requests_mock, mock_hub_instance, a_test_policy):
    requests_mock.get(fake_hub_host + "/api/policy-rules/00000000-0000-0000-0000-000000000001", json=test_policy)
    policy = mock_hub_instance.get_policy_by_id("00000000-0000-0000-0000-000000000001")
    for key in a_test_policy.keys():
        assert policy[key] == a_test_policy[key]

def test_get_policy_by_url(requests_mock, mock_hub_instance, a_test_policy):
    requests_mock.get(fake_hub_host + "/api/policy-rules/00000000-0000-0000-0000-000000000001", json=test_policy)
    policy = mock_hub_instance.get_policy_by_url(mock_hub_instance._get_policy_url() + "/00000000-0000-0000-0000-000000000001")
    for key in a_test_policy.keys():
        assert policy[key] == a_test_policy[key]

def test_update_policy_by_id(requests_mock, mock_hub_instance, a_test_policy, a_test_policy_for_create_or_update):
    policy_id = a_test_policy['_meta']['href'].split("/")[-1]

    requests_mock.put(fake_hub_host + "/api/policy-rules/" + policy_id,
        json=test_policy
    )
    response = mock_hub_instance.update_policy_by_id(policy_id, a_test_policy_for_create_or_update)
    assert response.status_code == 200
    assert response.json() == a_test_policy

def test_update_policy_by_url(requests_mock, mock_hub_instance, a_test_policy, a_test_policy_for_create_or_update):
    policy_id = a_test_policy['_meta']['href'].split("/")[-1]
    policy_url = mock_hub_instance._get_policy_url() + "/" + policy_id

    requests_mock.put(fake_hub_host + "/api/policy-rules/" + policy_id,
        json=test_policy
    )
    response = mock_hub_instance.update_policy_by_url(policy_url, a_test_policy_for_create_or_update)
    assert response.status_code == 200
    assert response.json() == a_test_policy

def test_create_policy(requests_mock, mock_hub_instance, a_test_policy, a_test_policy_for_create_or_update):
    requests_mock.post(fake_hub_host + "/api/policy-rules", headers={"location": a_test_policy['_meta']['href']}, status_code=201)
    new_policy_url = mock_hub_instance.create_policy(a_test_policy_for_create_or_update)
    assert new_policy_url == a_test_policy['_meta']['href']

def test_delete_policy_by_id(requests_mock, mock_hub_instance, a_test_policy):
    policy_id = a_test_policy['_meta']['href'].split("/")[-1]

    requests_mock.delete(fake_hub_host + "/api/policy-rules/" + a_test_policy['_meta']['href'].split("/")[-1], status_code=204)
    response = mock_hub_instance.delete_policy_by_id(policy_id)
    assert response.status_code == 204

def test_delete_policy_by_url(requests_mock, mock_hub_instance, a_test_policy):
    policy_url = mock_hub_instance._get_policy_url() + "/" + a_test_policy['_meta']['href'].split("/")[-1]

    requests_mock.delete(fake_hub_host + "/api/policy-rules/" + a_test_policy['_meta']['href'].split("/")[-1], status_code=204)
    response = mock_hub_instance.delete_policy_by_url(policy_url)
    assert response.status_code == 204


