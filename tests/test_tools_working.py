"""
Working tests for individual tools using correct API signatures
"""

import pytest
from unittest.mock import AsyncMock, patch
from datadog_mcp.tools import get_logs, get_teams, get_metrics, list_metrics
from mcp.types import CallToolResult, TextContent


class TestLogsToolWorking:
    """Working tests for logs functionality"""
    
    def test_logs_tool_definition(self):
        """Test logs tool definition structure"""
        tool_def = get_logs.get_tool_definition()
        assert tool_def.name == "get_logs"
        assert "log" in tool_def.description.lower()
        assert "properties" in tool_def.inputSchema
    
    @pytest.mark.asyncio
    async def test_logs_handler_success(self, sample_request, sample_logs_data, mock_env_credentials):
        """Test successful logs handler call"""
        sample_request.arguments = {
            "query": "error",
            "time_range": "1h",
            "limit": 100,
            "format": "table"
        }

        with patch('datadog_mcp.tools.get_logs.fetch_logs', new_callable=AsyncMock) as mock_fetch:
            # Mock should return dict with "data" and "meta" keys
            mock_fetch.return_value = {
                "data": sample_logs_data,
                "meta": {"page": {"after": None}}
            }

            result = await get_logs.handle_call(sample_request)

            assert isinstance(result, CallToolResult)
            assert result.isError is False
            assert len(result.content) > 0
            assert isinstance(result.content[0], TextContent)
    
    @pytest.mark.asyncio
    async def test_logs_handler_error(self, sample_request, mock_env_credentials):
        """Test logs handler error handling"""
        sample_request.arguments = {"query": "test"}

        with patch('datadog_mcp.tools.get_logs.fetch_logs', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = Exception("API error")

            result = await get_logs.handle_call(sample_request)

            assert isinstance(result, CallToolResult)
            assert result.isError is True
            assert "error" in result.content[0].text.lower()


class TestTeamsToolWorking:
    """Working tests for teams functionality"""
    
    def test_teams_tool_definition(self):
        """Test teams tool definition structure"""
        tool_def = get_teams.get_tool_definition()
        assert tool_def.name == "get_teams"
        assert "team" in tool_def.description.lower()
    
    @pytest.mark.asyncio
    async def test_teams_handler_success(self, sample_request, sample_teams_data, mock_env_credentials):
        """Test successful teams handler call"""
        sample_request.arguments = {
            "format": "table",
            "include_members": True
        }

        with patch('datadog_mcp.tools.get_teams.fetch_teams', new_callable=AsyncMock) as mock_fetch, \
             patch('datadog_mcp.tools.get_teams.fetch_team_memberships', new_callable=AsyncMock) as mock_members:
            # Mock should return dict with "data" and "meta" keys
            mock_fetch.return_value = {
                "data": sample_teams_data.get("teams", []),
                "meta": {"pagination": {}}
            }
            mock_members.return_value = {"data": []}

            result = await get_teams.handle_call(sample_request)

            assert isinstance(result, CallToolResult)
            assert result.isError is False
            assert len(result.content) > 0
    
    @pytest.mark.asyncio
    async def test_teams_handler_error(self, sample_request, mock_env_credentials):
        """Test teams handler error handling"""
        sample_request.arguments = {}

        with patch('datadog_mcp.tools.get_teams.fetch_teams', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = Exception("Teams API error")

            result = await get_teams.handle_call(sample_request)

            assert isinstance(result, CallToolResult)
            assert result.isError is True


class TestMetricsToolWorking:
    """Working tests for metrics functionality"""
    
    def test_metrics_tool_definition(self):
        """Test metrics tool definition structure"""
        tool_def = get_metrics.get_tool_definition()
        assert tool_def.name == "get_metrics"
        assert "metric" in tool_def.description.lower()
        
        properties = tool_def.inputSchema["properties"]
        assert "metric_name" in properties
    
    @pytest.mark.asyncio
    async def test_metrics_handler_success(self, sample_request, sample_metrics_data, mock_env_credentials):
        """Test successful metrics handler call"""
        sample_request.arguments = {
            "metric_name": "system.cpu.user",
            "time_range": "1h",
            "aggregation": "avg",
            "format": "table"
        }

        with patch('datadog_mcp.tools.get_metrics.fetch_metrics', new_callable=AsyncMock) as mock_fetch:
            # Extract the series from nested API response structure for what formatters expect
            mock_fetch.return_value = sample_metrics_data["data"]["attributes"]

            result = await get_metrics.handle_call(sample_request)

            assert isinstance(result, CallToolResult)
            assert result.isError is False
            assert len(result.content) > 0
    
    def test_list_metrics_tool_definition(self):
        """Test list_metrics tool definition"""
        tool_def = list_metrics.get_tool_definition()
        assert tool_def.name == "list_metrics"
        assert "list" in tool_def.description.lower()
    
    @pytest.mark.asyncio
    async def test_list_metrics_handler_success(self, sample_request, mock_env_credentials):
        """Test successful list_metrics handler call"""
        sample_request.arguments = {
            "limit": 100,
            "format": "list"
        }

        # Mock should return dict with "data" and optional "meta" keys
        mock_fetch_response = {
            "data": [
                {
                    "id": "system.cpu.user",
                    "type": "gauge",
                    "attributes": {
                        "description": "Average CPU usage",
                        "unit": "percent"
                    }
                },
                {
                    "id": "aws.apigateway.count",
                    "type": "count",
                    "attributes": {
                        "description": "API Gateway request count",
                        "unit": "requests"
                    }
                }
            ],
            "meta": {"pagination": {}}
        }

        with patch('datadog_mcp.tools.list_metrics.fetch_metrics_list', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_fetch_response

            result = await list_metrics.handle_call(sample_request)

            assert isinstance(result, CallToolResult)
            assert result.isError is False


class TestToolParameterValidation:
    """Test tool parameter validation"""
    
    @pytest.mark.asyncio
    async def test_logs_with_minimal_params(self, mock_env_credentials):
        """Test logs tool with minimal parameters"""
        from datadog_mcp.tools.get_logs import handle_call

        request = type('Request', (), {})()
        request.params = type('Params', (), {})()
        request.params.arguments = {}  # Empty arguments

        with patch('datadog_mcp.tools.get_logs.fetch_logs', new_callable=AsyncMock) as mock_fetch:
            # Mock should return dict with "data" and "meta" keys
            mock_fetch.return_value = {
                "data": [],
                "meta": {"page": {"after": None}}
            }

            result = await handle_call(request)

            # Should handle gracefully
            assert isinstance(result, CallToolResult)
    
    @pytest.mark.asyncio
    async def test_metrics_with_minimal_params(self, mock_env_credentials):
        """Test metrics tool with minimal parameters"""
        from datadog_mcp.tools.get_metrics import handle_call

        request = type('Request', (), {})()
        request.params = type('Params', (), {})()
        request.params.arguments = {"metric_name": "system.cpu.user"}

        with patch('datadog_mcp.tools.get_metrics.fetch_metrics', new_callable=AsyncMock) as mock_fetch:
            # Return just the attributes part that formatters expect
            mock_fetch.return_value = {"series": []}

            result = await handle_call(request)

            assert isinstance(result, CallToolResult)


class TestDataFormatting:
    """Test data formatting functionality"""
    
    def test_basic_data_structures(self, sample_logs_data, sample_metrics_data, sample_teams_data):
        """Test that sample data has expected structure"""
        # Logs data
        assert isinstance(sample_logs_data, list)
        assert len(sample_logs_data) > 0
        assert "message" in sample_logs_data[0]
        assert "timestamp" in sample_logs_data[0]
        
        # Metrics data
        assert "data" in sample_metrics_data
        assert "attributes" in sample_metrics_data["data"]
        assert "series" in sample_metrics_data["data"]["attributes"]
        
        # Teams data
        assert "teams" in sample_teams_data
        assert "users" in sample_teams_data
        assert len(sample_teams_data["teams"]) > 0
    
    def test_json_serialization(self, sample_logs_data):
        """Test that data can be JSON serialized"""
        import json
        
        # Should not raise exception
        json_str = json.dumps(sample_logs_data)
        assert isinstance(json_str, str)
        
        # Should be deserializable
        parsed = json.loads(json_str)
        assert parsed == sample_logs_data


class TestActualAPIFunctions:
    """Test the actual API function signatures"""
    
    def test_datadog_client_functions_exist(self):
        """Test that expected functions exist in datadog_client"""
        from datadog_mcp.utils import datadog_client
        
        expected_functions = [
            'fetch_logs',
            'fetch_teams', 
            'fetch_metrics',
            'fetch_metrics_list',
            'fetch_ci_pipelines'
        ]
        
        for func_name in expected_functions:
            assert hasattr(datadog_client, func_name), f"Function {func_name} not found"
            assert callable(getattr(datadog_client, func_name))
    
    @pytest.mark.asyncio
    async def test_api_functions_callable(self, mock_httpx_client, mock_env_credentials):
        """Test that API functions can be called without errors"""
        from datadog_mcp.utils import datadog_client

        # Test fetch_logs
        result = await datadog_client.fetch_logs()
        assert isinstance(result, dict)
        assert "data" in result

        # Test fetch_teams
        result = await datadog_client.fetch_teams()
        assert isinstance(result, dict)

        # Test fetch_ci_pipelines
        result = await datadog_client.fetch_ci_pipelines()
        assert isinstance(result, dict)
        assert "data" in result


if __name__ == "__main__":
    pytest.main([__file__])