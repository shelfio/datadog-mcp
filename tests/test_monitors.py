"""
Tests for monitors listing functionality
"""

import pytest
import json
from unittest.mock import patch, AsyncMock, MagicMock
from datadog_mcp.tools import list_monitors
from datadog_mcp.utils import datadog_client
from mcp.types import CallToolResult, TextContent


class TestMonitorsToolDefinition:
    """Test monitors tool definition"""

    def test_list_monitors_tool_definition(self):
        """Test list_monitors tool definition"""
        tool_def = list_monitors.get_tool_definition()

        assert tool_def.name == "list_monitors"
        assert "monitor" in tool_def.description.lower()
        assert hasattr(tool_def, "inputSchema")

        schema = tool_def.inputSchema
        assert "properties" in schema

        properties = schema["properties"]
        expected_params = ["tags", "name", "monitor_tags", "format", "page_size", "page"]
        for param in expected_params:
            assert param in properties, f"Parameter {param} missing from list_monitors schema"

    def test_list_monitors_format_options(self):
        """Test list_monitors format options"""
        tool_def = list_monitors.get_tool_definition()
        schema = tool_def.inputSchema

        format_prop = schema["properties"]["format"]
        assert "enum" in format_prop
        assert "table" in format_prop["enum"]
        assert "json" in format_prop["enum"]
        assert "summary" in format_prop["enum"]


class TestMonitorsRetrieval:
    """Test monitors data retrieval"""

    @pytest.mark.asyncio
    async def test_fetch_monitors_basic(self):
        """Test basic monitors fetching"""
        mock_response = [
            {
                "id": 12345,
                "name": "CPU High",
                "type": "metric alert",
                "overall_state": "OK",
                "tags": ["env:prod", "team:backend"],
            },
            {
                "id": 12346,
                "name": "Memory Usage",
                "type": "metric alert",
                "overall_state": "Alert",
                "tags": ["env:prod"],
            },
        ]

        with patch("datadog_mcp.utils.datadog_client.httpx.AsyncClient") as mock_client:
            mock_resp = MagicMock()
            mock_resp.json.return_value = mock_response
            mock_resp.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_resp
            )

            result = await datadog_client.fetch_monitors()

            assert isinstance(result, list)
            assert len(result) == 2


class TestMonitorsToolHandlers:
    """Test monitors tool handlers"""

    @pytest.mark.asyncio
    async def test_handle_list_monitors_success(self):
        """Test successful monitors listing"""
        mock_request = MagicMock()
        mock_request.arguments = {"format": "table"}

        mock_monitors = [
            {
                "id": 12345,
                "name": "CPU High Alert",
                "type": "metric alert",
                "overall_state": "OK",
                "tags": ["env:prod", "team:backend"],
            },
            {
                "id": 12346,
                "name": "Memory Usage Alert",
                "type": "metric alert",
                "overall_state": "Alert",
                "tags": ["env:prod"],
            },
        ]

        with patch(
            "datadog_mcp.tools.list_monitors.fetch_monitors",
            new_callable=AsyncMock,
        ) as mock_fetch:
            mock_fetch.return_value = mock_monitors

            result = await list_monitors.handle_call(mock_request)

            assert isinstance(result, CallToolResult)
            assert result.isError is False
            assert len(result.content) > 0
            assert isinstance(result.content[0], TextContent)

            content_text = result.content[0].text
            assert "CPU High Alert" in content_text
            assert "Memory Usage Alert" in content_text

    @pytest.mark.asyncio
    async def test_handle_list_monitors_json_format(self):
        """Test monitors listing with JSON format"""
        mock_request = MagicMock()
        mock_request.arguments = {"format": "json"}

        mock_monitors = [
            {
                "id": 12345,
                "name": "Test Monitor",
                "type": "metric alert",
                "overall_state": "OK",
                "tags": [],
            }
        ]

        with patch(
            "datadog_mcp.tools.list_monitors.fetch_monitors",
            new_callable=AsyncMock,
        ) as mock_fetch:
            mock_fetch.return_value = mock_monitors

            result = await list_monitors.handle_call(mock_request)

            assert isinstance(result, CallToolResult)
            assert result.isError is False

            # Verify JSON output
            content_text = result.content[0].text
            parsed = json.loads(content_text)
            assert len(parsed) == 1
            assert parsed[0]["name"] == "Test Monitor"

    @pytest.mark.asyncio
    async def test_handle_list_monitors_summary_format(self):
        """Test monitors listing with summary format"""
        mock_request = MagicMock()
        mock_request.arguments = {"format": "summary"}

        mock_monitors = [
            {"id": 1, "name": "Mon1", "type": "metric alert", "overall_state": "OK", "tags": []},
            {"id": 2, "name": "Mon2", "type": "metric alert", "overall_state": "Alert", "tags": []},
            {"id": 3, "name": "Mon3", "type": "log alert", "overall_state": "OK", "tags": []},
        ]

        with patch(
            "datadog_mcp.tools.list_monitors.fetch_monitors",
            new_callable=AsyncMock,
        ) as mock_fetch:
            mock_fetch.return_value = mock_monitors

            result = await list_monitors.handle_call(mock_request)

            assert isinstance(result, CallToolResult)
            assert result.isError is False

            content_text = result.content[0].text
            assert "Found 3 monitors" in content_text
            assert "By Type:" in content_text
            assert "By State:" in content_text

    @pytest.mark.asyncio
    async def test_handle_list_monitors_with_filters(self):
        """Test monitors listing with filters"""
        mock_request = MagicMock()
        mock_request.arguments = {
            "tags": "env:prod",
            "name": "CPU",
            "monitor_tags": "team:backend",
            "format": "table",
        }

        mock_monitors = [
            {
                "id": 12345,
                "name": "CPU Alert",
                "type": "metric alert",
                "overall_state": "OK",
                "tags": ["env:prod"],
            }
        ]

        with patch(
            "datadog_mcp.tools.list_monitors.fetch_monitors",
            new_callable=AsyncMock,
        ) as mock_fetch:
            mock_fetch.return_value = mock_monitors

            result = await list_monitors.handle_call(mock_request)

            assert isinstance(result, CallToolResult)
            assert result.isError is False

            # Verify fetch was called with filters
            mock_fetch.assert_called_once_with(
                tags="env:prod",
                name="CPU",
                monitor_tags="team:backend",
                page_size=50,
                page=0,
            )

    @pytest.mark.asyncio
    async def test_handle_list_monitors_no_results(self):
        """Test monitors listing with no results"""
        mock_request = MagicMock()
        mock_request.arguments = {"format": "table"}

        with patch(
            "datadog_mcp.tools.list_monitors.fetch_monitors",
            new_callable=AsyncMock,
        ) as mock_fetch:
            mock_fetch.return_value = []

            result = await list_monitors.handle_call(mock_request)

            assert isinstance(result, CallToolResult)
            assert result.isError is False
            assert "No monitors found" in result.content[0].text

    @pytest.mark.asyncio
    async def test_handle_list_monitors_error(self):
        """Test error handling in monitors listing"""
        mock_request = MagicMock()
        mock_request.arguments = {}

        with patch(
            "datadog_mcp.tools.list_monitors.fetch_monitors",
            new_callable=AsyncMock,
        ) as mock_fetch:
            mock_fetch.side_effect = Exception("API error")

            result = await list_monitors.handle_call(mock_request)

            assert isinstance(result, CallToolResult)
            assert result.isError is True
            assert "error" in result.content[0].text.lower()


class TestMonitorsPagination:
    """Test monitors pagination"""

    @pytest.mark.asyncio
    async def test_monitors_pagination_params(self):
        """Test monitors with pagination parameters"""
        mock_request = MagicMock()
        mock_request.arguments = {
            "page_size": 10,
            "page": 2,
            "format": "table",
        }

        mock_monitors = [
            {"id": i, "name": f"Monitor {i}", "type": "metric alert", "overall_state": "OK", "tags": []}
            for i in range(10)
        ]

        with patch(
            "datadog_mcp.tools.list_monitors.fetch_monitors",
            new_callable=AsyncMock,
        ) as mock_fetch:
            mock_fetch.return_value = mock_monitors

            result = await list_monitors.handle_call(mock_request)

            assert isinstance(result, CallToolResult)
            assert result.isError is False

            # Verify pagination params passed to fetch
            mock_fetch.assert_called_once_with(
                tags="",
                name="",
                monitor_tags="",
                page_size=10,
                page=2,
            )


if __name__ == "__main__":
    pytest.main([__file__])
