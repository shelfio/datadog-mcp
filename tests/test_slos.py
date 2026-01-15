"""
Tests for SLO listing functionality
"""

import pytest
import json
from unittest.mock import patch, AsyncMock, MagicMock
from datadog_mcp.tools import list_slos
from datadog_mcp.utils import datadog_client
from mcp.types import CallToolResult, TextContent


class TestSLOsToolDefinition:
    """Test SLOs tool definition"""

    def test_list_slos_tool_definition(self):
        """Test list_slos tool definition"""
        tool_def = list_slos.get_tool_definition()

        assert tool_def.name == "list_slos"
        assert "slo" in tool_def.description.lower()
        assert hasattr(tool_def, "inputSchema")

        schema = tool_def.inputSchema
        assert "properties" in schema

        properties = schema["properties"]
        expected_params = ["tags", "query", "limit", "offset", "format"]
        for param in expected_params:
            assert param in properties, f"Parameter {param} missing from list_slos schema"

    def test_list_slos_format_options(self):
        """Test list_slos format options"""
        tool_def = list_slos.get_tool_definition()
        schema = tool_def.inputSchema

        format_prop = schema["properties"]["format"]
        assert "enum" in format_prop
        assert "table" in format_prop["enum"]
        assert "json" in format_prop["enum"]
        assert "summary" in format_prop["enum"]


class TestSLOsRetrieval:
    """Test SLOs data retrieval"""

    @pytest.mark.asyncio
    async def test_fetch_slos_basic(self):
        """Test basic SLOs fetching"""
        mock_response = [
            {
                "id": "slo-123",
                "name": "API Availability",
                "type": "metric",
                "thresholds": [{"target": 0.99, "warning": 0.995}],
                "tags": ["team:backend"],
            },
            {
                "id": "slo-456",
                "name": "Latency SLO",
                "type": "metric",
                "thresholds": [{"target": 0.95}],
                "tags": ["team:frontend"],
            },
        ]

        with patch("datadog_mcp.utils.datadog_client.httpx.AsyncClient") as mock_client:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"data": mock_response}
            mock_resp.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_resp
            )

            result = await datadog_client.fetch_slos()

            assert isinstance(result, list)


class TestSLOsToolHandlers:
    """Test SLOs tool handlers"""

    @pytest.mark.asyncio
    async def test_handle_list_slos_success(self):
        """Test successful SLOs listing"""
        mock_request = MagicMock()
        mock_request.arguments = {"format": "table"}

        mock_slos = [
            {
                "id": "slo-123",
                "name": "API Availability SLO",
                "type": "metric",
                "description": "Ensures API uptime",
                "thresholds": [{"target": 0.99, "warning": 0.995}],
                "tags": ["team:backend", "env:prod"],
            },
            {
                "id": "slo-456",
                "name": "Response Time SLO",
                "type": "metric",
                "description": "P95 latency target",
                "thresholds": [{"target": 0.95}],
                "tags": ["team:frontend"],
            },
        ]

        with patch(
            "datadog_mcp.tools.list_slos.fetch_slos",
            new_callable=AsyncMock,
        ) as mock_fetch:
            mock_fetch.return_value = mock_slos

            result = await list_slos.handle_call(mock_request)

            assert isinstance(result, CallToolResult)
            assert result.isError is False
            assert len(result.content) > 0
            assert isinstance(result.content[0], TextContent)

            content_text = result.content[0].text
            assert "API Availability SLO" in content_text
            assert "Response Time SLO" in content_text

    @pytest.mark.asyncio
    async def test_handle_list_slos_json_format(self):
        """Test SLOs listing with JSON format"""
        mock_request = MagicMock()
        mock_request.arguments = {"format": "json"}

        mock_slos = [
            {
                "id": "slo-123",
                "name": "Test SLO",
                "type": "metric",
                "thresholds": [{"target": 0.99}],
                "tags": [],
            }
        ]

        with patch(
            "datadog_mcp.tools.list_slos.fetch_slos",
            new_callable=AsyncMock,
        ) as mock_fetch:
            mock_fetch.return_value = mock_slos

            result = await list_slos.handle_call(mock_request)

            assert isinstance(result, CallToolResult)
            assert result.isError is False

            # Verify JSON output
            content_text = result.content[0].text
            parsed = json.loads(content_text)
            assert len(parsed) == 1
            assert parsed[0]["name"] == "Test SLO"

    @pytest.mark.asyncio
    async def test_handle_list_slos_summary_format(self):
        """Test SLOs listing with summary format"""
        mock_request = MagicMock()
        mock_request.arguments = {"format": "summary"}

        mock_slos = [
            {"id": "1", "name": "SLO1", "type": "metric", "thresholds": [{"target": 0.99, "warning": 0.995}], "tags": []},
            {"id": "2", "name": "SLO2", "type": "metric", "thresholds": [{"target": 0.95}], "tags": []},
            {"id": "3", "name": "SLO3", "type": "monitor", "thresholds": [{"target": 0.999, "warning": 0.9995}], "tags": []},
        ]

        with patch(
            "datadog_mcp.tools.list_slos.fetch_slos",
            new_callable=AsyncMock,
        ) as mock_fetch:
            mock_fetch.return_value = mock_slos

            result = await list_slos.handle_call(mock_request)

            assert isinstance(result, CallToolResult)
            assert result.isError is False

            content_text = result.content[0].text
            assert "Found 3 SLOs" in content_text
            assert "By Type:" in content_text

    @pytest.mark.asyncio
    async def test_handle_list_slos_with_filters(self):
        """Test SLOs listing with filters"""
        mock_request = MagicMock()
        mock_request.arguments = {
            "tags": "team:backend",
            "query": "availability",
            "format": "table",
        }

        mock_slos = [
            {
                "id": "slo-123",
                "name": "API Availability",
                "type": "metric",
                "thresholds": [{"target": 0.99}],
                "tags": ["team:backend"],
            }
        ]

        with patch(
            "datadog_mcp.tools.list_slos.fetch_slos",
            new_callable=AsyncMock,
        ) as mock_fetch:
            mock_fetch.return_value = mock_slos

            result = await list_slos.handle_call(mock_request)

            assert isinstance(result, CallToolResult)
            assert result.isError is False

            # Verify fetch was called with filters
            mock_fetch.assert_called_once_with(
                tags="team:backend",
                query="availability",
                limit=50,
                offset=0,
            )

    @pytest.mark.asyncio
    async def test_handle_list_slos_no_results(self):
        """Test SLOs listing with no results"""
        mock_request = MagicMock()
        mock_request.arguments = {"format": "table"}

        with patch(
            "datadog_mcp.tools.list_slos.fetch_slos",
            new_callable=AsyncMock,
        ) as mock_fetch:
            mock_fetch.return_value = []

            result = await list_slos.handle_call(mock_request)

            assert isinstance(result, CallToolResult)
            assert result.isError is False
            assert "No SLOs found" in result.content[0].text

    @pytest.mark.asyncio
    async def test_handle_list_slos_error(self):
        """Test error handling in SLOs listing"""
        mock_request = MagicMock()
        mock_request.arguments = {}

        with patch(
            "datadog_mcp.tools.list_slos.fetch_slos",
            new_callable=AsyncMock,
        ) as mock_fetch:
            mock_fetch.side_effect = Exception("API error")

            result = await list_slos.handle_call(mock_request)

            assert isinstance(result, CallToolResult)
            assert result.isError is True
            assert "error" in result.content[0].text.lower()


class TestSLOsPagination:
    """Test SLOs pagination"""

    @pytest.mark.asyncio
    async def test_slos_pagination_params(self):
        """Test SLOs with pagination parameters"""
        mock_request = MagicMock()
        mock_request.arguments = {
            "limit": 10,
            "offset": 20,
            "format": "table",
        }

        mock_slos = [
            {"id": f"slo-{i}", "name": f"SLO {i}", "type": "metric", "thresholds": [{"target": 0.99}], "tags": []}
            for i in range(10)
        ]

        with patch(
            "datadog_mcp.tools.list_slos.fetch_slos",
            new_callable=AsyncMock,
        ) as mock_fetch:
            mock_fetch.return_value = mock_slos

            result = await list_slos.handle_call(mock_request)

            assert isinstance(result, CallToolResult)
            assert result.isError is False

            # Verify pagination params passed to fetch
            mock_fetch.assert_called_once_with(
                tags=None,
                query=None,
                limit=10,
                offset=20,
            )


class TestSLOsFormatting:
    """Test SLOs output formatting"""

    @pytest.mark.asyncio
    async def test_slos_table_shows_target(self):
        """Test that table format shows SLO target percentage"""
        mock_request = MagicMock()
        mock_request.arguments = {"format": "table"}

        mock_slos = [
            {
                "id": "slo-123",
                "name": "High Availability SLO",
                "type": "metric",
                "description": "",
                "thresholds": [{"target": 0.999, "warning": 0.9995}],
                "tags": [],
            }
        ]

        with patch(
            "datadog_mcp.tools.list_slos.fetch_slos",
            new_callable=AsyncMock,
        ) as mock_fetch:
            mock_fetch.return_value = mock_slos

            result = await list_slos.handle_call(mock_request)

            content_text = result.content[0].text
            # Target should be formatted as percentage
            assert "99.90%" in content_text or "Target:" in content_text


if __name__ == "__main__":
    pytest.main([__file__])
