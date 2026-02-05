"""
Tests for get_monitor tool functionality
"""

import pytest
import json
from unittest.mock import patch, AsyncMock, MagicMock
import httpx
from datadog_mcp.tools import get_monitor
from datadog_mcp.utils import datadog_client
from mcp.types import CallToolResult, TextContent


class TestGetMonitorToolDefinition:
    """Test get_monitor tool definition"""

    def test_get_monitor_tool_definition(self):
        """Test get_monitor tool definition"""
        tool_def = get_monitor.get_tool_definition()

        assert tool_def.name == "get_monitor"
        assert "monitor" in tool_def.description.lower()
        assert hasattr(tool_def, "inputSchema")

        schema = tool_def.inputSchema
        assert "properties" in schema

        properties = schema["properties"]
        assert "monitor_id" in properties
        assert "format" in properties

    def test_get_monitor_required_fields(self):
        """Test get_monitor required fields"""
        tool_def = get_monitor.get_tool_definition()
        schema = tool_def.inputSchema

        assert "required" in schema
        assert "monitor_id" in schema["required"]

    def test_get_monitor_format_options(self):
        """Test get_monitor format options"""
        tool_def = get_monitor.get_tool_definition()
        schema = tool_def.inputSchema

        format_prop = schema["properties"]["format"]
        assert "enum" in format_prop
        assert "table" in format_prop["enum"]
        assert "json" in format_prop["enum"]

    def test_get_monitor_id_type(self):
        """Test monitor_id is integer type"""
        tool_def = get_monitor.get_tool_definition()
        schema = tool_def.inputSchema

        monitor_id_prop = schema["properties"]["monitor_id"]
        assert monitor_id_prop["type"] == "integer"


class TestGetMonitorRetrieval:
    """Test monitor data retrieval via fetch_monitor"""

    @pytest.mark.asyncio
    async def test_fetch_monitor_basic(self):
        """Test basic monitor fetching"""
        mock_response_data = {
            "id": 12345,
            "name": "CPU High Alert",
            "type": "metric alert",
            "overall_state": "OK",
            "priority": 2,
            "query": "avg(last_5m):avg:system.cpu.user{*} > 90",
            "message": "CPU usage is too high",
            "tags": ["env:prod", "team:backend"],
        }

        with patch("datadog_mcp.utils.datadog_client.httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await datadog_client.fetch_monitor(12345)

            assert isinstance(result, dict)
            assert result["id"] == 12345
            assert result["name"] == "CPU High Alert"
            assert result["type"] == "metric alert"
            assert result["overall_state"] == "OK"

    @pytest.mark.asyncio
    async def test_fetch_monitor_with_all_fields(self):
        """Test monitor fetching returns all expected fields"""
        mock_response_data = {
            "id": 99999,
            "name": "Memory Usage Alert",
            "type": "metric alert",
            "overall_state": "Alert",
            "priority": 1,
            "query": "avg(last_5m):avg:system.mem.used{*} > 80",
            "message": "Memory usage critical!\n@slack-alerts",
            "tags": ["env:prod", "team:infra", "service:api"],
            "created": "2024-01-01T00:00:00Z",
            "modified": "2024-01-15T12:00:00Z",
        }

        with patch("datadog_mcp.utils.datadog_client.httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await datadog_client.fetch_monitor(99999)

            assert result["id"] == 99999
            assert result["priority"] == 1
            assert result["query"] == "avg(last_5m):avg:system.mem.used{*} > 80"
            assert len(result["tags"]) == 3

    @pytest.mark.asyncio
    async def test_fetch_monitor_api_error(self):
        """Test fetch_monitor handles API errors"""
        with patch("datadog_mcp.utils.datadog_client.httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Not Found",
                request=MagicMock(),
                response=MagicMock(status_code=404),
            )

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            with pytest.raises(httpx.HTTPStatusError):
                await datadog_client.fetch_monitor(99999999)


class TestGetMonitorHandlers:
    """Test get_monitor tool handlers"""

    @pytest.mark.asyncio
    async def test_handle_get_monitor_success_table(self):
        """Test successful monitor retrieval with table format"""
        mock_request = MagicMock()
        mock_request.arguments = {"monitor_id": 12345, "format": "table"}

        mock_monitor = {
            "id": 12345,
            "name": "CPU High Alert",
            "type": "metric alert",
            "overall_state": "OK",
            "priority": 2,
            "query": "avg(last_5m):avg:system.cpu.user{*} > 90",
            "message": "CPU usage is too high",
            "tags": ["env:prod", "team:backend"],
        }

        with patch(
            "datadog_mcp.tools.get_monitor.fetch_monitor",
            new_callable=AsyncMock,
        ) as mock_fetch:
            mock_fetch.return_value = mock_monitor

            result = await get_monitor.handle_call(mock_request)

            assert isinstance(result, CallToolResult)
            assert result.isError is False
            assert len(result.content) > 0
            assert isinstance(result.content[0], TextContent)

            content_text = result.content[0].text
            assert "12345" in content_text
            assert "CPU High Alert" in content_text
            assert "metric alert" in content_text
            assert "OK" in content_text

    @pytest.mark.asyncio
    async def test_handle_get_monitor_success_json(self):
        """Test successful monitor retrieval with JSON format"""
        mock_request = MagicMock()
        mock_request.arguments = {"monitor_id": 12345, "format": "json"}

        mock_monitor = {
            "id": 12345,
            "name": "Test Monitor",
            "type": "metric alert",
            "overall_state": "OK",
            "priority": 3,
            "query": "avg(last_5m):avg:system.cpu.user{*} > 90",
            "message": "Alert message",
            "tags": [],
        }

        with patch(
            "datadog_mcp.tools.get_monitor.fetch_monitor",
            new_callable=AsyncMock,
        ) as mock_fetch:
            mock_fetch.return_value = mock_monitor

            result = await get_monitor.handle_call(mock_request)

            assert isinstance(result, CallToolResult)
            assert result.isError is False

            content_text = result.content[0].text
            parsed = json.loads(content_text)
            assert parsed["id"] == 12345
            assert parsed["name"] == "Test Monitor"

    @pytest.mark.asyncio
    async def test_handle_get_monitor_default_format(self):
        """Test monitor retrieval with default format (table)"""
        mock_request = MagicMock()
        mock_request.arguments = {"monitor_id": 12345}

        mock_monitor = {
            "id": 12345,
            "name": "Test Monitor",
            "type": "metric alert",
            "overall_state": "OK",
            "priority": None,
            "query": "test query",
            "message": "",
            "tags": [],
        }

        with patch(
            "datadog_mcp.tools.get_monitor.fetch_monitor",
            new_callable=AsyncMock,
        ) as mock_fetch:
            mock_fetch.return_value = mock_monitor

            result = await get_monitor.handle_call(mock_request)

            assert isinstance(result, CallToolResult)
            assert result.isError is False
            assert "Monitor Details" in result.content[0].text

    @pytest.mark.asyncio
    async def test_handle_get_monitor_missing_monitor_id(self):
        """Test error when monitor_id is missing"""
        mock_request = MagicMock()
        mock_request.arguments = {"format": "table"}

        result = await get_monitor.handle_call(mock_request)

        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert "monitor_id" in result.content[0].text.lower()

    @pytest.mark.asyncio
    async def test_handle_get_monitor_none_arguments(self):
        """Test error when arguments is None"""
        mock_request = MagicMock()
        mock_request.arguments = None

        result = await get_monitor.handle_call(mock_request)

        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert "monitor_id" in result.content[0].text.lower()

    @pytest.mark.asyncio
    async def test_handle_get_monitor_api_error(self):
        """Test error handling when API call fails"""
        mock_request = MagicMock()
        mock_request.arguments = {"monitor_id": 99999}

        with patch(
            "datadog_mcp.tools.get_monitor.fetch_monitor",
            new_callable=AsyncMock,
        ) as mock_fetch:
            mock_fetch.side_effect = Exception("API error")

            result = await get_monitor.handle_call(mock_request)

            assert isinstance(result, CallToolResult)
            assert result.isError is True
            assert "error" in result.content[0].text.lower()

    @pytest.mark.asyncio
    async def test_handle_get_monitor_not_found(self):
        """Test handling of monitor not found (404)"""
        mock_request = MagicMock()
        mock_request.arguments = {"monitor_id": 99999999}

        with patch(
            "datadog_mcp.tools.get_monitor.fetch_monitor",
            new_callable=AsyncMock,
        ) as mock_fetch:
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_fetch.side_effect = httpx.HTTPStatusError(
                "Not Found",
                request=MagicMock(),
                response=mock_response,
            )

            result = await get_monitor.handle_call(mock_request)

            assert isinstance(result, CallToolResult)
            assert result.isError is True
            assert "not found" in result.content[0].text.lower()

    @pytest.mark.asyncio
    async def test_handle_get_monitor_permission_denied(self):
        """Test handling of permission denied (403)"""
        mock_request = MagicMock()
        mock_request.arguments = {"monitor_id": 12345}

        with patch(
            "datadog_mcp.tools.get_monitor.fetch_monitor",
            new_callable=AsyncMock,
        ) as mock_fetch:
            mock_response = MagicMock()
            mock_response.status_code = 403
            mock_fetch.side_effect = httpx.HTTPStatusError(
                "Forbidden",
                request=MagicMock(),
                response=mock_response,
            )

            result = await get_monitor.handle_call(mock_request)

            assert isinstance(result, CallToolResult)
            assert result.isError is True
            assert "permission denied" in result.content[0].text.lower()

    @pytest.mark.asyncio
    async def test_handle_get_monitor_truncates_long_message(self):
        """Test that long messages are truncated in table format"""
        mock_request = MagicMock()
        mock_request.arguments = {"monitor_id": 12345, "format": "table"}

        long_message = "A" * 200

        mock_monitor = {
            "id": 12345,
            "name": "Test Monitor",
            "type": "metric alert",
            "overall_state": "OK",
            "priority": 2,
            "query": "test query",
            "message": long_message,
            "tags": [],
        }

        with patch(
            "datadog_mcp.tools.get_monitor.fetch_monitor",
            new_callable=AsyncMock,
        ) as mock_fetch:
            mock_fetch.return_value = mock_monitor

            result = await get_monitor.handle_call(mock_request)

            assert isinstance(result, CallToolResult)
            assert result.isError is False
            assert "..." in result.content[0].text

    @pytest.mark.asyncio
    async def test_handle_get_monitor_many_tags_truncated(self):
        """Test that many tags are truncated in table format"""
        mock_request = MagicMock()
        mock_request.arguments = {"monitor_id": 12345, "format": "table"}

        mock_monitor = {
            "id": 12345,
            "name": "Test Monitor",
            "type": "metric alert",
            "overall_state": "OK",
            "priority": 2,
            "query": "test query",
            "message": "",
            "tags": ["tag1", "tag2", "tag3", "tag4", "tag5", "tag6", "tag7"],
        }

        with patch(
            "datadog_mcp.tools.get_monitor.fetch_monitor",
            new_callable=AsyncMock,
        ) as mock_fetch:
            mock_fetch.return_value = mock_monitor

            result = await get_monitor.handle_call(mock_request)

            assert isinstance(result, CallToolResult)
            assert result.isError is False
            assert "+2 more" in result.content[0].text


if __name__ == "__main__":
    pytest.main([__file__])
