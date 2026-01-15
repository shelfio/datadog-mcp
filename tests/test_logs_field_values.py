"""
Tests for logs field values discovery functionality
"""

import pytest
import json
from unittest.mock import patch, AsyncMock, MagicMock
from datadog_mcp.tools import get_logs_field_values
from datadog_mcp.utils import datadog_client
from mcp.types import CallToolResult, TextContent


class TestLogsFieldValuesToolDefinition:
    """Test logs field values tool definition"""

    def test_get_logs_field_values_tool_definition(self):
        """Test get_logs_field_values tool definition"""
        tool_def = get_logs_field_values.get_tool_definition()

        assert tool_def.name == "get_logs_field_values"
        assert "field" in tool_def.description.lower()
        assert hasattr(tool_def, "inputSchema")

        schema = tool_def.inputSchema
        assert "properties" in schema

        properties = schema["properties"]
        expected_params = ["field_name", "time_range", "query", "limit", "format"]
        for param in expected_params:
            assert param in properties, f"Parameter {param} missing from get_logs_field_values schema"

        # field_name should be required
        assert "required" in schema
        assert "field_name" in schema["required"]

    def test_get_logs_field_values_format_options(self):
        """Test get_logs_field_values format options"""
        tool_def = get_logs_field_values.get_tool_definition()
        schema = tool_def.inputSchema

        format_prop = schema["properties"]["format"]
        assert "enum" in format_prop
        assert "table" in format_prop["enum"]
        assert "list" in format_prop["enum"]
        assert "json" in format_prop["enum"]

    def test_get_logs_field_values_time_range_options(self):
        """Test get_logs_field_values time range options"""
        tool_def = get_logs_field_values.get_tool_definition()
        schema = tool_def.inputSchema

        time_range_prop = schema["properties"]["time_range"]
        assert "enum" in time_range_prop
        expected_ranges = ["1h", "4h", "8h", "1d", "7d", "14d", "30d"]
        for time_range in expected_ranges:
            assert time_range in time_range_prop["enum"]


class TestLogsFieldValuesRetrieval:
    """Test logs field values data retrieval"""

    @pytest.mark.asyncio
    async def test_fetch_logs_filter_values_basic(self):
        """Test basic logs filter values fetching via tool handler"""
        # This tests the full flow through the handler with mocked API
        mock_request = MagicMock()
        mock_request.arguments = {
            "field_name": "service",
            "time_range": "1h",
            "format": "json",
        }

        mock_response = {
            "field": "service",
            "time_range": "1h",
            "values": [
                {"value": "web-api", "count": 1500},
                {"value": "worker", "count": 800},
                {"value": "scheduler", "count": 200},
            ],
            "total_values": 3,
        }

        with patch(
            "datadog_mcp.tools.get_logs_field_values.fetch_logs_filter_values",
            new_callable=AsyncMock,
        ) as mock_fetch:
            mock_fetch.return_value = mock_response

            result = await get_logs_field_values.handle_call(mock_request)

            assert isinstance(result, CallToolResult)
            assert result.isError is False

            content_text = result.content[0].text
            parsed = json.loads(content_text)
            assert "field" in parsed
            assert parsed["field"] == "service"
            assert len(parsed["values"]) == 3


class TestLogsFieldValuesToolHandlers:
    """Test logs field values tool handlers"""

    @pytest.mark.asyncio
    async def test_handle_get_logs_field_values_success(self):
        """Test successful logs field values retrieval"""
        mock_request = MagicMock()
        mock_request.arguments = {
            "field_name": "service",
            "time_range": "1h",
            "format": "table",
        }

        mock_response = {
            "field": "service",
            "time_range": "1h",
            "values": [
                {"value": "web-api", "count": 1500},
                {"value": "worker", "count": 800},
            ],
            "total_values": 2,
        }

        with patch(
            "datadog_mcp.tools.get_logs_field_values.fetch_logs_filter_values",
            new_callable=AsyncMock,
        ) as mock_fetch:
            mock_fetch.return_value = mock_response

            result = await get_logs_field_values.handle_call(mock_request)

            assert isinstance(result, CallToolResult)
            assert result.isError is False
            assert len(result.content) > 0
            assert isinstance(result.content[0], TextContent)

            content_text = result.content[0].text
            assert "service" in content_text.lower()
            assert "web-api" in content_text

    @pytest.mark.asyncio
    async def test_handle_get_logs_field_values_json_format(self):
        """Test logs field values with JSON format"""
        mock_request = MagicMock()
        mock_request.arguments = {
            "field_name": "env",
            "format": "json",
        }

        mock_response = {
            "field": "env",
            "time_range": "1h",
            "values": [
                {"value": "prod", "count": 5000},
                {"value": "staging", "count": 1000},
            ],
            "total_values": 2,
        }

        with patch(
            "datadog_mcp.tools.get_logs_field_values.fetch_logs_filter_values",
            new_callable=AsyncMock,
        ) as mock_fetch:
            mock_fetch.return_value = mock_response

            result = await get_logs_field_values.handle_call(mock_request)

            assert isinstance(result, CallToolResult)
            assert result.isError is False

            # Verify JSON output
            content_text = result.content[0].text
            parsed = json.loads(content_text)
            assert "field" in parsed
            assert parsed["field"] == "env"

    @pytest.mark.asyncio
    async def test_handle_get_logs_field_values_list_format(self):
        """Test logs field values with list format"""
        mock_request = MagicMock()
        mock_request.arguments = {
            "field_name": "status",
            "format": "list",
        }

        mock_response = {
            "field": "status",
            "time_range": "1h",
            "values": [
                {"value": "info", "count": 10000},
                {"value": "error", "count": 500},
                {"value": "warn", "count": 200},
            ],
            "total_values": 3,
        }

        with patch(
            "datadog_mcp.tools.get_logs_field_values.fetch_logs_filter_values",
            new_callable=AsyncMock,
        ) as mock_fetch:
            mock_fetch.return_value = mock_response

            result = await get_logs_field_values.handle_call(mock_request)

            assert isinstance(result, CallToolResult)
            assert result.isError is False

            content_text = result.content[0].text
            # List format should show values with bullet points or similar
            assert "info" in content_text
            assert "error" in content_text

    @pytest.mark.asyncio
    async def test_handle_get_logs_field_values_missing_field_name(self):
        """Test error when field_name is missing"""
        mock_request = MagicMock()
        mock_request.arguments = {"time_range": "1h"}

        result = await get_logs_field_values.handle_call(mock_request)

        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert "field_name" in result.content[0].text.lower()

    @pytest.mark.asyncio
    async def test_handle_get_logs_field_values_with_query(self):
        """Test logs field values with optional query filter"""
        mock_request = MagicMock()
        mock_request.arguments = {
            "field_name": "host",
            "query": "service:web-api",
            "time_range": "4h",
            "format": "table",
        }

        mock_response = {
            "field": "host",
            "time_range": "4h",
            "values": [
                {"value": "web-01", "count": 500},
                {"value": "web-02", "count": 450},
            ],
            "total_values": 2,
        }

        with patch(
            "datadog_mcp.tools.get_logs_field_values.fetch_logs_filter_values",
            new_callable=AsyncMock,
        ) as mock_fetch:
            mock_fetch.return_value = mock_response

            result = await get_logs_field_values.handle_call(mock_request)

            assert isinstance(result, CallToolResult)
            assert result.isError is False

            # Verify fetch was called with query
            mock_fetch.assert_called_once_with(
                field_name="host",
                time_range="4h",
                query="service:web-api",
                limit=100,
            )

    @pytest.mark.asyncio
    async def test_handle_get_logs_field_values_with_limit(self):
        """Test logs field values with custom limit"""
        mock_request = MagicMock()
        mock_request.arguments = {
            "field_name": "source",
            "limit": 50,
            "format": "table",
        }

        mock_response = {
            "field": "source",
            "time_range": "1h",
            "values": [{"value": f"source-{i}", "count": 100 - i} for i in range(50)],
            "total_values": 50,
        }

        with patch(
            "datadog_mcp.tools.get_logs_field_values.fetch_logs_filter_values",
            new_callable=AsyncMock,
        ) as mock_fetch:
            mock_fetch.return_value = mock_response

            result = await get_logs_field_values.handle_call(mock_request)

            assert isinstance(result, CallToolResult)
            assert result.isError is False

            mock_fetch.assert_called_once_with(
                field_name="source",
                time_range="1h",
                query=None,
                limit=50,
            )

    @pytest.mark.asyncio
    async def test_handle_get_logs_field_values_no_results(self):
        """Test logs field values with no results"""
        mock_request = MagicMock()
        mock_request.arguments = {
            "field_name": "nonexistent_field",
            "format": "table",
        }

        mock_response = {
            "field": "nonexistent_field",
            "time_range": "1h",
            "values": [],
            "total_values": 0,
        }

        with patch(
            "datadog_mcp.tools.get_logs_field_values.fetch_logs_filter_values",
            new_callable=AsyncMock,
        ) as mock_fetch:
            mock_fetch.return_value = mock_response

            result = await get_logs_field_values.handle_call(mock_request)

            assert isinstance(result, CallToolResult)
            assert result.isError is False
            assert "no values found" in result.content[0].text.lower()

    @pytest.mark.asyncio
    async def test_handle_get_logs_field_values_error(self):
        """Test error handling in logs field values"""
        mock_request = MagicMock()
        mock_request.arguments = {
            "field_name": "service",
        }

        with patch(
            "datadog_mcp.tools.get_logs_field_values.fetch_logs_filter_values",
            new_callable=AsyncMock,
        ) as mock_fetch:
            mock_fetch.side_effect = Exception("API error")

            result = await get_logs_field_values.handle_call(mock_request)

            assert isinstance(result, CallToolResult)
            assert result.isError is True
            assert "error" in result.content[0].text.lower()


class TestLogsFieldValuesFormatting:
    """Test logs field values output formatting"""

    def test_format_as_table(self):
        """Test table formatting function"""
        response = {
            "field": "service",
            "time_range": "1h",
            "values": [
                {"value": "web-api", "count": 1500},
                {"value": "worker", "count": 800},
            ],
            "total_values": 2,
        }

        result = get_logs_field_values._format_as_table(response)

        assert "service" in result
        assert "1h" in result
        assert "web-api" in result
        assert "1500" in result

    def test_format_as_list(self):
        """Test list formatting function"""
        response = {
            "field": "env",
            "time_range": "4h",
            "values": [
                {"value": "prod", "count": 5000},
                {"value": "staging", "count": 1000},
            ],
            "total_values": 2,
        }

        result = get_logs_field_values._format_as_list(response)

        assert "env" in result
        assert "4h" in result
        assert "prod" in result
        assert "5000" in result or "occurrences" in result

    def test_format_as_table_empty_values(self):
        """Test table formatting with empty values"""
        response = {
            "field": "service",
            "time_range": "1h",
            "values": [],
            "total_values": 0,
        }

        result = get_logs_field_values._format_as_table(response)

        assert "no values found" in result.lower()

    def test_format_as_list_empty_values(self):
        """Test list formatting with empty values"""
        response = {
            "field": "service",
            "time_range": "1h",
            "values": [],
            "total_values": 0,
        }

        result = get_logs_field_values._format_as_list(response)

        assert "no values found" in result.lower()


if __name__ == "__main__":
    pytest.main([__file__])
