import asyncio
from unittest.mock import patch

import pytest

# fastmcp is an optional 'mcp' extra, not part of the base test lockfile.
# Skip this module entirely rather than failing CI when it isn't installed.
pytest.importorskip("fastmcp")

from blackduck.mcp_server import BlackDuckMCPServer


@pytest.fixture
def mcp_server(monkeypatch):
    monkeypatch.setenv("BLACKDUCK_URL", "https://fake-hub-host")
    monkeypatch.setenv("BLACKDUCK_TOKEN", "fake-token")
    with patch("blackduck.mcp_server.Client") as mock_client_cls:
        server = BlackDuckMCPServer()
        yield server, mock_client_cls.return_value


def _call_tool(server, name, **kwargs):
    async def _run():
        tool = await server.mcp.get_tool(name)
        return tool.fn(**kwargs)
    return asyncio.run(_run())


def _fake_get_resource(vulnerable_component):
    def get_resource(name, parent=None, **kwargs):
        if name == "projects":
            return iter([{"name": "Acme", "_meta": {"href": "https://fake-hub-host/api/projects/p1"}}])
        if name == "versions":
            return iter([{"versionName": "1.0", "_meta": {"href": "https://fake-hub-host/api/projects/p1/versions/v1"}}])
        if name == "vulnerable-components":
            return iter([vulnerable_component])
        raise AssertionError(f"unexpected resource name: {name}")
    return get_resource


def test_get_project_vulnerabilities_reads_nested_vulnerability_object(mcp_server):
    """Regression test: BlackDuck's vulnerable-components response nests CVE
    details under a 'vulnerability' sub-object, not at the top level."""
    server, mock_client = mcp_server
    mock_client.get_resource.side_effect = _fake_get_resource({
        "componentName": "ag-grid-community",
        "componentVersionName": "24.0.0",
        "vulnerability": {
            "vulnerabilityId": "CVE-2024-38996",
            "severity": "CRITICAL",
            "description": "Prototype pollution via _.mergeDeep",
            "source": "NVD",
            "cweIds": ["CWE-1321"],
            "remediationStatus": "NEW",
        },
    })

    result = _call_tool(server, "get_project_vulnerabilities", project_name="Acme")

    assert result == [{
        "componentName": "ag-grid-community",
        "componentVersionName": "24.0.0",
        "vulnerabilityName": "CVE-2024-38996",
        "severity": "CRITICAL",
        "remediationStatus": "NEW",
        "description": "Prototype pollution via _.mergeDeep",
        "source": "NVD",
        "cweIds": ["CWE-1321"],
    }]


def test_get_project_vulnerabilities_handles_missing_vulnerability_object(mcp_server):
    server, mock_client = mcp_server
    mock_client.get_resource.side_effect = _fake_get_resource({
        "componentName": "some-lib",
        "componentVersionName": "1.0.0",
    })

    result = _call_tool(server, "get_project_vulnerabilities", project_name="Acme")

    assert result == [{
        "componentName": "some-lib",
        "componentVersionName": "1.0.0",
        "vulnerabilityName": None,
        "severity": None,
        "remediationStatus": None,
        "description": "",
        "source": None,
        "cweIds": [],
    }]
