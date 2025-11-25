"""
Tests for APM trace retrieval functionality
"""

import pytest
import json
from unittest.mock import patch, AsyncMock, MagicMock
from datadog_mcp.tools import get_traces
from datadog_mcp.utils import datadog_client
from mcp.types import CallToolResult, TextContent


class TestTraceToolDefinition:
    """Test the get_traces tool definition"""

    def test_get_traces_tool_definition(self):
        """Test that get_traces tool definition is properly structured"""
        tool_def = get_traces.get_tool_definition()

        assert tool_def.name == "get_traces"
        assert "trace" in tool_def.description.lower() or "apm" in tool_def.description.lower()
        assert hasattr(tool_def, 'inputSchema')

        # Check required schema properties
        schema = tool_def.inputSchema
        assert "properties" in schema

        # Should have common parameters
        properties = schema["properties"]
        expected_params = ["query", "filters", "time_range", "limit", "format"]
        for param in expected_params:
            assert param in properties, f"Parameter {param} missing from schema"


class TestTraceRetrieval:
    """Test trace retrieval functionality"""

    @pytest.mark.asyncio
    async def test_fetch_traces_basic(self):
        """Test basic trace fetching functionality"""
        # Mock the HTTP response
        mock_response_data = {
            "data": [
                {
                    "id": "trace-123",
                    "attributes": {
                        "start_timestamp": "2023-01-01T12:00:00Z",
                        "end_timestamp": "2023-01-01T12:00:00.050Z",
                        "service": "web-api",
                        "resource_name": "GET /api/users",
                        "operation_name": "http.request",
                        "status": "ok"
                    }
                }
            ],
            "meta": {
                "page": {
                    "after": "next_cursor"
                }
            }
        }

        with patch('datadog_mcp.utils.datadog_client.httpx.AsyncClient') as mock_client:
            mock_response = AsyncMock()
            mock_response.json = MagicMock(return_value=mock_response_data)
            mock_response.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            result = await datadog_client.fetch_traces()

            assert isinstance(result, dict)
            assert "data" in result
            assert len(result["data"]) > 0
            assert "attributes" in result["data"][0]

    @pytest.mark.asyncio
    async def test_fetch_traces_with_filters(self):
        """Test trace fetching with filters"""
        filters = {
            "service": "web-api",
            "env": "production",
            "status": "error"
        }

        mock_response_data = {
            "data": [
                {
                    "id": "trace-456",
                    "attributes": {
                        "start_timestamp": "2023-01-01T12:00:00Z",
                        "end_timestamp": "2023-01-01T12:00:00.100Z",
                        "service": "web-api",
                        "resource_name": "POST /api/orders",
                        "operation_name": "http.request",
                        "status": "error",
                        "env": "production"
                    }
                }
            ],
            "meta": {
                "page": {}
            }
        }

        with patch('datadog_mcp.utils.datadog_client.httpx.AsyncClient') as mock_client:
            mock_response = AsyncMock()
            mock_response.json = MagicMock(return_value=mock_response_data)
            mock_response.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            result = await datadog_client.fetch_traces(filters=filters)

            assert isinstance(result, dict)
            # Verify filter was applied (would be in the request payload)
            mock_client.return_value.__aenter__.return_value.post.assert_called_once()


class TestTraceToolHandler:
    """Test the get_traces tool handler"""

    @pytest.mark.asyncio
    async def test_handle_traces_request_success(self):
        """Test successful trace request handling"""
        # Mock request
        mock_request = MagicMock()
        mock_request.arguments = {
            "query": "error",
            "time_range": "1h",
            "limit": 100,
            "format": "table"
        }

        # Mock trace data
        mock_traces_response = {
            "data": [
                {
                    "id": "trace-789",
                    "attributes": {
                        "start_timestamp": "2023-01-01T12:00:00Z",
                        "end_timestamp": "2023-01-01T12:00:00.075Z",
                        "service": "web-api",
                        "resource_name": "GET /api/error",
                        "operation_name": "http.request",
                        "status": "error",
                        "error": True,
                        "error.message": "Internal Server Error"
                    }
                }
            ],
            "meta": {
                "page": {}
            }
        }

        with patch('datadog_mcp.tools.get_traces.fetch_traces', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_traces_response

            result = await get_traces.handle_call(mock_request)

            assert isinstance(result, CallToolResult)
            assert result.isError is False
            assert len(result.content) > 0
            assert isinstance(result.content[0], TextContent)

            # Should contain trace information
            content_text = result.content[0].text
            assert "web-api" in content_text or "trace" in content_text.lower()

    @pytest.mark.asyncio
    async def test_handle_traces_request_with_json_format(self):
        """Test trace request with JSON format"""
        mock_request = MagicMock()
        mock_request.arguments = {
            "query": "service:web-api",
            "format": "json",
            "limit": 50
        }

        mock_traces_response = {
            "data": [
                {
                    "id": "trace-101",
                    "attributes": {
                        "start_timestamp": "2023-01-01T12:00:00Z",
                        "end_timestamp": "2023-01-01T12:00:00.025Z",
                        "service": "web-api",
                        "resource_name": "GET /api/status",
                        "operation_name": "http.request",
                        "status": "ok"
                    }
                }
            ],
            "meta": {
                "page": {}
            }
        }

        with patch('datadog_mcp.tools.get_traces.fetch_traces', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_traces_response

            result = await get_traces.handle_call(mock_request)

            assert isinstance(result, CallToolResult)
            assert result.isError is False

            content_text = result.content[0].text
            # Should be valid JSON when format is json
            if mock_request.arguments.get("format") == "json":
                try:
                    parsed = json.loads(content_text)
                    assert "traces" in parsed
                    assert "pagination" in parsed
                except json.JSONDecodeError:
                    pytest.fail("Response should be valid JSON when format=json")

    @pytest.mark.asyncio
    async def test_handle_traces_request_error(self):
        """Test error handling in trace requests"""
        mock_request = MagicMock()
        mock_request.arguments = {
            "query": "test",
            "time_range": "1h"
        }

        with patch('datadog_mcp.tools.get_traces.fetch_traces', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = Exception("API error")

            result = await get_traces.handle_call(mock_request)

            assert isinstance(result, CallToolResult)
            assert result.isError is True
            assert len(result.content) > 0
            assert "error" in result.content[0].text.lower()

    @pytest.mark.asyncio
    async def test_handle_traces_request_empty_results(self):
        """Test handling when no traces are found"""
        mock_request = MagicMock()
        mock_request.arguments = {
            "query": "nonexistent",
            "time_range": "1h"
        }

        mock_traces_response = {
            "data": [],
            "meta": {
                "page": {}
            }
        }

        with patch('datadog_mcp.tools.get_traces.fetch_traces', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_traces_response

            result = await get_traces.handle_call(mock_request)

            assert isinstance(result, CallToolResult)
            assert result.isError is False
            assert len(result.content) > 0

            content_text = result.content[0].text
            assert "no trace" in content_text.lower() or "no results" in content_text.lower()


class TestTraceFormatting:
    """Test trace data formatting"""

    def test_trace_table_formatting(self):
        """Test that traces can be formatted as table"""
        sample_traces = [
            {
                "trace_id": "trace-1",
                "timestamp": "2023-01-01T12:00:00Z",
                "service": "web-api",
                "resource_name": "GET /api/users",
                "duration": "50000000",  # Already extracted/calculated
                "status": "ok"
            },
            {
                "trace_id": "trace-2",
                "timestamp": "2023-01-01T12:01:00Z",
                "service": "database",
                "resource_name": "SELECT * FROM users",
                "duration": "10000000",  # Already extracted/calculated
                "status": "ok"
            }
        ]

        # Import formatter and test
        from datadog_mcp.utils.formatters import format_traces_as_table

        table_output = format_traces_as_table(sample_traces)
        assert isinstance(table_output, str)
        assert len(table_output) > 0
        assert "web-api" in table_output
        assert "database" in table_output

    def test_trace_text_formatting(self):
        """Test that traces can be formatted as text"""
        sample_traces = [
            {
                "trace_id": "trace-1",
                "timestamp": "2023-01-01T12:00:00Z",
                "service": "web-api",
                "resource_name": "GET /api/users",
                "duration": "50000000",
                "status": "ok"
            }
        ]

        from datadog_mcp.utils.formatters import format_traces_as_text

        text_output = format_traces_as_text(sample_traces)
        assert isinstance(text_output, str)
        assert len(text_output) > 0
        assert "web-api" in text_output

    def test_trace_json_formatting(self):
        """Test that traces can be formatted as JSON"""
        sample_traces = [
            {
                "trace_id": "trace-1",
                "timestamp": "2023-01-01T12:00:00Z",
                "service": "web-api",
                "resource_name": "GET /api/users"
            }
        ]

        json_output = json.dumps({"traces": sample_traces}, indent=2)
        assert isinstance(json_output, str)

        # Should be valid JSON
        parsed = json.loads(json_output)
        assert "traces" in parsed
        assert len(parsed["traces"]) == 1
        assert parsed["traces"][0]["service"] == "web-api"


class TestTraceFiltering:
    """Test trace filtering functionality"""

    @pytest.mark.asyncio
    async def test_traces_with_service_filter(self):
        """Test filtering traces by service"""
        filters = {"service": "web-api"}

        with patch('datadog_mcp.utils.datadog_client.httpx.AsyncClient') as mock_client:
            mock_response_data = {
                "data": [
                    {
                        "id": "trace-1",
                        "attributes": {
                            "service": "web-api",
                            "resource_name": "GET /api/status"
                        }
                    }
                ],
                "meta": {"page": {}}
            }

            mock_response = AsyncMock()
            mock_response.json = MagicMock(return_value=mock_response_data)
            mock_response.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            result = await datadog_client.fetch_traces(filters=filters)

            # Verify the request was made with proper filters
            call_args = mock_client.return_value.__aenter__.return_value.post.call_args
            assert call_args is not None

            # Verify the query string includes the filter
            payload = call_args.kwargs['json']
            query_str = payload['data']['attributes']['filter']['query']
            assert 'service:web-api' in query_str

    @pytest.mark.asyncio
    async def test_traces_with_time_range(self):
        """Test filtering traces by time range"""
        time_range = "4h"

        with patch('datadog_mcp.utils.datadog_client.httpx.AsyncClient') as mock_client:
            mock_response_data = {"data": [], "meta": {"page": {}}}

            mock_response = AsyncMock()
            mock_response.json = MagicMock(return_value=mock_response_data)
            mock_response.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            result = await datadog_client.fetch_traces(time_range=time_range)

            # Verify the request was made
            mock_client.return_value.__aenter__.return_value.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_traces_with_error_filter(self):
        """Test filtering traces with error status"""
        filters = {"status": "error"}

        with patch('datadog_mcp.utils.datadog_client.httpx.AsyncClient') as mock_client:
            mock_response_data = {
                "data": [
                    {
                        "id": "trace-error",
                        "attributes": {
                            "service": "web-api",
                            "status": "error",
                            "error": True,
                            "error.message": "Internal error"
                        }
                    }
                ],
                "meta": {"page": {}}
            }

            mock_response = AsyncMock()
            mock_response.json = MagicMock(return_value=mock_response_data)
            mock_response.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            result = await datadog_client.fetch_traces(filters=filters)

            # Verify the request was made
            call_args = mock_client.return_value.__aenter__.return_value.post.call_args
            assert call_args is not None

    @pytest.mark.asyncio
    async def test_traces_with_multiple_filters_and_special_chars(self):
        """Test filtering with multiple filters and special characters"""
        filters = {
            "service": "web-api",
            "env": "production",
            "resource_name": "GET /api/users"  # Has spaces, should be quoted
        }

        with patch('datadog_mcp.utils.datadog_client.httpx.AsyncClient') as mock_client:
            mock_response_data = {"data": [], "meta": {"page": {}}}

            mock_response = AsyncMock()
            mock_response.json = MagicMock(return_value=mock_response_data)
            mock_response.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            result = await datadog_client.fetch_traces(filters=filters)

            # Verify the query string is built correctly
            call_args = mock_client.return_value.__aenter__.return_value.post.call_args
            payload = call_args.kwargs['json']
            query_str = payload['data']['attributes']['filter']['query']

            # Should contain all filters joined with AND
            assert 'service:web-api' in query_str
            assert 'env:production' in query_str
            # Resource name with spaces should be quoted
            assert 'resource_name:"GET /api/users"' in query_str
            assert ' AND ' in query_str


if __name__ == "__main__":
    pytest.main([__file__])
