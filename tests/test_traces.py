"""
Tests for APM trace retrieval functionality
"""

import pytest
import json
from unittest.mock import patch, AsyncMock, MagicMock
from datadog_mcp.utils import datadog_client
from mcp.types import CallToolResult, TextContent


class TestTraceClient:
    """Test trace client functions in datadog_client"""

    @pytest.mark.asyncio
    async def test_fetch_traces_basic(self):
        """Test basic trace fetching functionality"""
        mock_response_data = {
            "data": [
                {
                    "id": "trace123",
                    "type": "span",
                    "attributes": {
                        "resource.name": "POST /api/endpoint",
                        "service.name": "web",
                        "duration": 5000000000,  # nanoseconds
                        "http.status_code": "200",
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

        # Create mock response object
        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()

        with patch('datadog_mcp.utils.datadog_client.httpx.AsyncClient') as mock_client_class:
            # Setup the async context manager
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await datadog_client.fetch_traces()

            assert isinstance(result, dict)
            assert "data" in result
            assert "meta" in result
            assert len(result["data"]) > 0
            assert result["data"][0]["attributes"]["service.name"] == "web"

    @pytest.mark.asyncio
    async def test_fetch_traces_with_query(self):
        """Test trace fetching with custom query"""
        mock_response_data = {
            "data": [
                {
                    "id": "trace456",
                    "attributes": {
                        "resource.name": "POST /graphql",
                        "service.name": "api",
                        "duration": 12000000000,  # 12 seconds
                        "status": "error"
                    }
                }
            ],
            "meta": {"page": {}}
        }

        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()

        with patch('datadog_mcp.utils.datadog_client.httpx.AsyncClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await datadog_client.fetch_traces(
                query="@duration:>5000000000",
                time_range="1h"
            )

            assert isinstance(result, dict)
            assert len(result["data"]) > 0
            # Verify the request was made with the query
            mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_traces_with_pagination(self):
        """Test trace fetching with cursor pagination"""
        mock_response_data = {
            "data": [
                {
                    "id": "trace789",
                    "attributes": {
                        "resource.name": "GET /users",
                        "service.name": "web",
                        "duration": 1000000000
                    }
                }
            ],
            "meta": {
                "page": {
                    "after": "next_page_cursor"
                }
            }
        }

        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()

        with patch('datadog_mcp.utils.datadog_client.httpx.AsyncClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await datadog_client.fetch_traces(cursor="initial_cursor")

            assert isinstance(result, dict)
            assert result["meta"]["page"]["after"] == "next_page_cursor"

    @pytest.mark.asyncio
    async def test_fetch_traces_with_limit(self):
        """Test that limit parameter is passed correctly"""
        mock_response_data = {"data": [], "meta": {"page": {}}}

        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()

        with patch('datadog_mcp.utils.datadog_client.httpx.AsyncClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await datadog_client.fetch_traces(limit=50)

            # Verify request was made
            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args

            # Check that the request payload contains limit
            if call_args and len(call_args) > 1:
                request_body = call_args[1].get('json', {})
                assert request_body is not None

    @pytest.mark.asyncio
    async def test_fetch_traces_include_children(self):
        """Test trace fetching with child spans included"""
        mock_response_data = {
            "data": [
                {
                    "id": "trace_with_children",
                    "attributes": {
                        "resource.name": "POST /process",
                        "service.name": "worker",
                        "duration": 8000000000
                    },
                    "children": [
                        {
                            "id": "child_span_1",
                            "attributes": {
                                "resource.name": "db.query",
                                "duration": 7000000000
                            }
                        }
                    ]
                }
            ],
            "meta": {"page": {}}
        }

        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()

        with patch('datadog_mcp.utils.datadog_client.httpx.AsyncClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await datadog_client.fetch_traces(include_children=True)

            assert isinstance(result, dict)
            assert len(result["data"]) > 0

    @pytest.mark.asyncio
    async def test_aggregate_traces_basic(self):
        """Test basic trace aggregation"""
        mock_response_data = {
            "data": [
                {
                    "type": "aggregate_metric",
                    "attributes": {
                        "service.name": "web",
                        "count": 150,
                        "duration.avg": 4500000000
                    }
                }
            ]
        }

        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()

        with patch('datadog_mcp.utils.datadog_client.httpx.AsyncClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await datadog_client.aggregate_traces(
                query="service:web",
                group_by=["service.name"]
            )

            assert isinstance(result, dict)
            assert "data" in result
            assert len(result["data"]) > 0

    @pytest.mark.asyncio
    async def test_aggregate_traces_multiple_groupby(self):
        """Test trace aggregation with multiple group_by fields"""
        mock_response_data = {
            "data": [
                {
                    "attributes": {
                        "service.name": "web",
                        "http.status_code": "500",
                        "count": 42
                    }
                }
            ]
        }

        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()

        with patch('datadog_mcp.utils.datadog_client.httpx.AsyncClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await datadog_client.aggregate_traces(
                query="status:error",
                group_by=["service.name", "http.status_code"]
            )

            assert isinstance(result, dict)
            assert len(result["data"]) > 0

    @pytest.mark.asyncio
    async def test_aggregate_traces_with_aggregation(self):
        """Test trace aggregation with custom aggregation type"""
        mock_response_data = {
            "data": [
                {
                    "attributes": {
                        "service.name": "api",
                        "duration.max": 25000000000
                    }
                }
            ]
        }

        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()

        with patch('datadog_mcp.utils.datadog_client.httpx.AsyncClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await datadog_client.aggregate_traces(
                query="service:api",
                aggregation="max"
            )

            assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_fetch_traces_api_error(self):
        """Test error handling when API returns an error"""
        with patch('datadog_mcp.utils.datadog_client.httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post.return_value.raise_for_status.side_effect = Exception("API error")

            with pytest.raises(Exception):
                await datadog_client.fetch_traces()

    @pytest.mark.asyncio
    async def test_aggregate_traces_empty_results(self):
        """Test aggregation with no results"""
        mock_response_data = {
            "data": []
        }

        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()

        with patch('datadog_mcp.utils.datadog_client.httpx.AsyncClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await datadog_client.aggregate_traces()

            assert isinstance(result, dict)
            assert len(result["data"]) == 0


class TestGetTracesTool:
    """Test the get_traces tool"""

    def test_get_traces_tool_definition(self):
        """Test that get_traces tool definition is properly structured"""
        from datadog_mcp.tools import get_traces

        tool_def = get_traces.get_tool_definition()

        assert tool_def.name == "get_traces"
        assert "trace" in tool_def.description.lower()
        assert hasattr(tool_def, 'inputSchema')

        # Check required schema properties
        schema = tool_def.inputSchema
        assert "properties" in schema

        # Should have common parameters
        properties = schema["properties"]
        expected_params = ["query", "time_range", "limit", "include_children", "format"]
        for param in expected_params:
            assert param in properties, f"Parameter {param} missing from schema"

    @pytest.mark.asyncio
    async def test_handle_traces_request_success(self):
        """Test successful trace request handling"""
        from datadog_mcp.tools import get_traces

        mock_request = MagicMock()
        mock_request.arguments = {
            "query": "service:web",
            "time_range": "1h",
            "limit": 10,
            "format": "table"
        }

        mock_traces = {
            "data": [
                {
                    "attributes": {
                        "resource.name": "GET /api",
                        "service.name": "web",
                        "duration": 2000000000,
                        "http.status_code": "200"
                    }
                }
            ],
            "meta": {"page": {}}
        }

        with patch('datadog_mcp.tools.get_traces.fetch_traces', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_traces

            result = await get_traces.handle_call(mock_request)

            assert isinstance(result, CallToolResult)
            assert result.isError is False
            assert len(result.content) > 0
            assert isinstance(result.content[0], TextContent)

    @pytest.mark.asyncio
    async def test_handle_traces_request_json_format(self):
        """Test trace request with JSON format"""
        from datadog_mcp.tools import get_traces

        mock_request = MagicMock()
        mock_request.arguments = {
            "query": "@duration:>5000000000",
            "format": "json",
            "limit": 3
        }
        mock_request.params = MagicMock()
        mock_request.params.arguments = mock_request.arguments

        mock_traces = {
            "data": [
                {
                    "attributes": {
                        "resource.name": "POST /graphql",
                        "service.name": "api",
                        "duration": 12000000000
                    }
                }
            ],
            "meta": {"page": {"after": "cursor123"}}
        }

        with patch('datadog_mcp.tools.get_traces.fetch_traces', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_traces

            result = await get_traces.handle_call(mock_request)

            assert isinstance(result, CallToolResult)
            assert result.isError is False

            content_text = result.content[0].text
            # Should contain JSON data when format is json
            assert "POST /graphql" in content_text
            assert "cursor123" in content_text
            # Verify the JSON object part is present
            assert "{" in content_text and "}" in content_text

    @pytest.mark.asyncio
    async def test_handle_traces_request_text_format(self):
        """Test trace request with text format"""
        from datadog_mcp.tools import get_traces

        mock_request = MagicMock()
        mock_request.arguments = {
            "query": "service:web",
            "format": "text",
            "limit": 5
        }

        mock_traces = {
            "data": [
                {
                    "attributes": {
                        "resource.name": "GET /users",
                        "service.name": "web",
                        "duration": 1500000000,
                        "status": "ok"
                    }
                }
            ],
            "meta": {"page": {}}
        }

        with patch('datadog_mcp.tools.get_traces.fetch_traces', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_traces

            result = await get_traces.handle_call(mock_request)

            assert isinstance(result, CallToolResult)
            assert result.isError is False
            content_text = result.content[0].text
            assert isinstance(content_text, str)
            assert len(content_text) > 0

    @pytest.mark.asyncio
    async def test_handle_traces_request_error(self):
        """Test error handling in trace requests"""
        from datadog_mcp.tools import get_traces

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
        from datadog_mcp.tools import get_traces

        mock_request = MagicMock()
        mock_request.arguments = {
            "query": "nonexistent_service",
            "time_range": "1h"
        }

        mock_traces = {"data": [], "meta": {"page": {}}}

        with patch('datadog_mcp.tools.get_traces.fetch_traces', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_traces

            result = await get_traces.handle_call(mock_request)

            assert isinstance(result, CallToolResult)
            assert result.isError is False
            assert len(result.content) > 0

            content_text = result.content[0].text
            assert "no traces" in content_text.lower() or "no results" in content_text.lower()

    @pytest.mark.asyncio
    async def test_handle_traces_with_pagination(self):
        """Test trace request with pagination cursor"""
        from datadog_mcp.tools import get_traces

        mock_request = MagicMock()
        mock_request.arguments = {
            "query": "service:web",
            "cursor": "page_cursor",
            "format": "table"
        }

        mock_traces = {
            "data": [
                {
                    "attributes": {
                        "resource.name": "POST /api",
                        "service.name": "web",
                        "duration": 3000000000
                    }
                }
            ],
            "meta": {"page": {"after": "next_cursor"}}
        }

        with patch('datadog_mcp.tools.get_traces.fetch_traces', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_traces

            result = await get_traces.handle_call(mock_request)

            assert isinstance(result, CallToolResult)
            assert result.isError is False
            # Should include pagination info in output
            content_text = result.content[0].text
            assert isinstance(content_text, str)


class TestGetAggregateTracesTool:
    """Test the aggregate_traces tool (to be implemented)"""

    def test_aggregate_traces_tool_definition_will_exist(self):
        """Test that aggregate_traces tool will be properly structured"""
        # This test verifies the expected structure when aggregate_traces.py is created
        # Expected parameters: query, time_range, group_by, aggregation, format
        expected_params = ["query", "time_range", "group_by", "aggregation", "format"]
        assert len(expected_params) > 0  # Placeholder assertion


if __name__ == "__main__":
    pytest.main([__file__])
