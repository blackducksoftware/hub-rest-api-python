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


def test_get_upgrade_guidance_falls_back_when_transitive_variant_unavailable(mcp_server):
    """transitive-upgrade-guidance requires an originId that isn't always
    known; the tool should fall back to the standard upgrade-guidance
    endpoint rather than surfacing that as a failure."""
    server, mock_client = mcp_server
    standard_guidance = {
        "componentName": "Apache Commons BeanUtils",
        "versionName": "1.9.3",
        "shortTerm": {"versionName": "1.11.0"},
        "longTerm": {"versionName": "1.11.0"},
    }
    mock_client.get_json.side_effect = [Exception("404 not found"), standard_guidance]

    result = _call_tool(
        server, "get_upgrade_guidance",
        component_id="comp-1", component_version_id="ver-1",
    )

    assert result["available"] is True
    assert result["source"] == "upgrade-guidance"
    assert result["shortTerm"] == {"versionName": "1.11.0"}
    assert mock_client.get_json.call_count == 2
    assert "transitive-upgrade-guidance" in mock_client.get_json.call_args_list[0].args[0]
    assert mock_client.get_json.call_args_list[1].args[0].endswith("/upgrade-guidance")


def test_get_upgrade_guidance_reports_unavailable_when_both_endpoints_fail(mcp_server):
    server, mock_client = mcp_server
    mock_client.get_json.side_effect = [Exception("404"), Exception("404")]

    result = _call_tool(
        server, "get_upgrade_guidance",
        component_id="comp-1", component_version_id="ver-1",
    )

    assert result == {"available": False, "componentId": "comp-1", "componentVersionId": "ver-1"}


def test_list_project_components_extracts_ids_from_hrefs(mcp_server):
    server, mock_client = mcp_server

    def get_resource(name, parent=None, **kwargs):
        if name == "projects":
            return iter([{"name": "Acme", "_meta": {"href": "https://fake-hub-host/api/projects/p1"}}])
        if name == "versions":
            return iter([{"versionName": "1.0", "_meta": {"href": "https://fake-hub-host/api/projects/p1/versions/v1"}}])
        if name == "components":
            return iter([{
                "componentName": "ag-grid-community",
                "componentVersionName": "24.0.0",
                "component": "https://fake-hub-host/api/components/comp-1",
                "componentVersion": "https://fake-hub-host/api/components/comp-1/versions/ver-1",
                "matchTypes": ["DIRECT_DEPENDENCY"],
            }])
        raise AssertionError(f"unexpected resource name: {name}")

    mock_client.get_resource.side_effect = get_resource

    result = _call_tool(server, "list_project_components", project_name="Acme")

    assert result[0]["componentId"] == "comp-1"
    assert result[0]["componentVersionId"] == "ver-1"
    assert result[0]["matchTypes"] == ["DIRECT_DEPENDENCY"]
