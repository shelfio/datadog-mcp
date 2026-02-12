"""
Tests for query_metric_formula and check_deployment tools
"""

import pytest
import json
from unittest.mock import patch, AsyncMock, MagicMock
from datadog_mcp.tools import query_metric_formula, check_deployment
from datadog_mcp.utils import datadog_client
from mcp.types import CallToolResult, TextContent


class TestQueryMetricFormulaToolDefinition:
    """Test query_metric_formula tool definition"""

    def test_tool_definition_exists(self):
        """Test that tool definition is properly defined"""
        tool_def = query_metric_formula.get_tool_definition()

        assert tool_def.name == "query_metric_formula"
        assert "formula" in tool_def.description.lower()
        assert hasattr(tool_def, "inputSchema")

    def test_tool_schema_properties(self):
        """Test tool schema has all required properties"""
        tool_def = query_metric_formula.get_tool_definition()
        schema = tool_def.inputSchema

        assert "properties" in schema
        properties = schema["properties"]

        expected_params = ["formula", "queries", "time_range", "filters", "format"]
        for param in expected_params:
            assert param in properties, f"Parameter {param} missing from schema"

    def test_tool_required_fields(self):
        """Test required fields are specified"""
        tool_def = query_metric_formula.get_tool_definition()
        schema = tool_def.inputSchema

        assert "required" in schema
        required = schema["required"]
        assert "formula" in required
        assert "queries" in required

    def test_format_enum_values(self):
        """Test format parameter has correct enum values"""
        tool_def = query_metric_formula.get_tool_definition()
        schema = tool_def.inputSchema
        format_prop = schema["properties"]["format"]

        assert "enum" in format_prop
        assert "summary" in format_prop["enum"]
        assert "timeseries" in format_prop["enum"]
        assert "json" in format_prop["enum"]


class TestCheckDeploymentToolDefinition:
    """Test check_deployment tool definition"""

    def test_tool_definition_exists(self):
        """Test that tool definition is properly defined"""
        tool_def = check_deployment.get_tool_definition()

        assert tool_def.name == "check_deployment"
        assert "deploy" in tool_def.description.lower()
        assert hasattr(tool_def, "inputSchema")

    def test_tool_schema_properties(self):
        """Test tool schema has all required properties"""
        tool_def = check_deployment.get_tool_definition()
        schema = tool_def.inputSchema

        assert "properties" in schema
        properties = schema["properties"]

        expected_params = ["service", "version_field", "version_value", "environment", "time_range", "format"]
        for param in expected_params:
            assert param in properties, f"Parameter {param} missing from schema"

    def test_tool_required_fields(self):
        """Test required fields are specified"""
        tool_def = check_deployment.get_tool_definition()
        schema = tool_def.inputSchema

        assert "required" in schema
        required = schema["required"]
        assert "service" in required
        assert "version_field" in required
        assert "version_value" in required


class TestFetchMetricFormula:
    """Test metric formula fetching"""

    @pytest.mark.asyncio
    async def test_fetch_metric_formula_basic(self):
        """Test basic metric formula fetching"""
        mock_response = {
            "data": {
                "attributes": {
                    "series": [
                        {
                            "pointlist": [
                                [1640995200000, 5.5],
                                [1640995260000, 6.2],
                            ],
                            "tags": ["formula:result"],
                        }
                    ]
                }
            }
        }

        with patch("datadog_mcp.utils.datadog_client.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post.return_value.json.return_value = mock_response
            mock_client.return_value.__aenter__.return_value.post.return_value.raise_for_status.return_value = None

            result = await datadog_client.fetch_metric_formula(
                formula="a / b * 100",
                queries={
                    "a": {"metric_name": "errors", "aggregation": "sum"},
                    "b": {"metric_name": "requests", "aggregation": "sum"},
                },
            )

            assert isinstance(result, dict)
            assert "data" in result

    @pytest.mark.asyncio
    async def test_fetch_metric_formula_with_filters(self):
        """Test metric formula with filters"""
        mock_response = {
            "data": {
                "attributes": {
                    "series": [
                        {
                            "pointlist": [[1640995200000, 5.5]],
                            "tags": ["formula:result"],
                        }
                    ]
                }
            }
        }

        with patch("datadog_mcp.utils.datadog_client.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post.return_value.json.return_value = mock_response
            mock_client.return_value.__aenter__.return_value.post.return_value.raise_for_status.return_value = None

            result = await datadog_client.fetch_metric_formula(
                formula="a - b",
                queries={
                    "a": {"metric_name": "memory.total", "aggregation": "avg"},
                    "b": {"metric_name": "memory.free", "aggregation": "avg"},
                },
                filters={"service": "web", "env": "prod"},
            )

            assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_fetch_metric_formula_missing_metric_name(self):
        """Test error when metric_name is missing"""
        with pytest.raises(ValueError, match="missing 'metric_name'"):
            await datadog_client.fetch_metric_formula(
                formula="a + b",
                queries={"a": {"aggregation": "sum"}},
            )

    @pytest.mark.asyncio
    async def test_fetch_metric_formula_with_different_time_ranges(self):
        """Test formula with different time ranges"""
        time_ranges = ["1h", "4h", "1d", "7d"]
        mock_response = {
            "data": {"attributes": {"series": [{"pointlist": [[1640995200000, 5.5]]}]}}
        }

        for time_range in time_ranges:
            with patch("datadog_mcp.utils.datadog_client.httpx.AsyncClient") as mock_client:
                mock_response_obj = AsyncMock()
                mock_response_obj.json = AsyncMock(return_value=mock_response)
                mock_response_obj.raise_for_status = AsyncMock(return_value=None)

                mock_client.return_value.__aenter__.return_value.post.return_value = mock_response_obj

                result = await datadog_client.fetch_metric_formula(
                    formula="a / b",
                    queries={
                        "a": {"metric_name": "metric1"},
                        "b": {"metric_name": "metric2"},
                    },
                    time_range=time_range,
                )

                assert isinstance(result, dict)


class TestCheckDeploymentStatus:
    """Test deployment status checking"""

    @pytest.mark.asyncio
    async def test_check_deployment_found(self):
        """Test deployment status check when version is found"""
        mock_logs = {
            "data": [
                {
                    "timestamp": "2026-02-05T10:00:00Z",
                    "service": "web",
                    "message": "Deployed version abc123",
                }
            ],
            "meta": {"page": {}},
        }

        with patch("datadog_mcp.utils.datadog_client.fetch_logs", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_logs

            result = await datadog_client.check_deployment_status(
                service="web",
                version_field="git.commit.sha",
                version_value="abc123",
            )

            assert result["status"] == "deployed"
            assert result["service"] == "web"
            assert result["log_count"] == 1
            assert result["first_seen"] is not None
            assert result["last_seen"] is not None

    @pytest.mark.asyncio
    async def test_check_deployment_not_found(self):
        """Test deployment status check when version is not found"""
        mock_logs = {"data": [], "meta": {"page": {}}}

        with patch("datadog_mcp.utils.datadog_client.fetch_logs", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_logs

            result = await datadog_client.check_deployment_status(
                service="web",
                version_field="git.commit.sha",
                version_value="nonexistent",
            )

            assert result["status"] == "not_found"
            assert result["log_count"] == 0
            assert result["first_seen"] is None
            assert result["last_seen"] is None

    @pytest.mark.asyncio
    async def test_check_deployment_with_environment(self):
        """Test deployment check with environment filter"""
        mock_logs = {
            "data": [
                {
                    "timestamp": "2026-02-05T10:00:00Z",
                    "service": "api",
                    "message": "Deployed v1.2.3",
                }
            ],
            "meta": {"page": {}},
        }

        with patch("datadog_mcp.utils.datadog_client.fetch_logs", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_logs

            result = await datadog_client.check_deployment_status(
                service="api",
                version_field="version",
                version_value="v1.2.3",
                environment="prod",
            )

            assert result["status"] == "deployed"
            assert result["environment"] == "prod"

    @pytest.mark.asyncio
    async def test_check_deployment_multiple_logs(self):
        """Test deployment check with multiple log entries"""
        mock_logs = {
            "data": [
                {"timestamp": "2026-02-05T10:05:00Z", "service": "web", "message": "Version still running"},
                {"timestamp": "2026-02-05T10:00:00Z", "service": "web", "message": "Deployed version"},
            ],
            "meta": {"page": {}},
        }

        with patch("datadog_mcp.utils.datadog_client.fetch_logs", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_logs

            result = await datadog_client.check_deployment_status(
                service="web",
                version_field="git.commit.sha",
                version_value="abc123",
                time_range="1h",
            )

            assert result["status"] == "deployed"
            assert result["log_count"] == 2


class TestQueryMetricFormulaHandler:
    """Test query_metric_formula tool handler"""

    @pytest.mark.asyncio
    async def test_handle_formula_success(self):
        """Test successful formula query"""
        mock_request = MagicMock()
        mock_request.params = MagicMock()
        mock_request.params.arguments = {
            "formula": "a / b * 100",
            "queries": {
                "a": {"metric_name": "errors", "aggregation": "sum"},
                "b": {"metric_name": "requests", "aggregation": "sum"},
            },
            "time_range": "1h",
            "format": "summary",
        }

        mock_formula_result = {
            "data": {
                "attributes": {
                    "series": [
                        {
                            "pointlist": [
                                [1640995200000, 5.5],
                                [1640995260000, 6.2],
                            ]
                        }
                    ]
                }
            }
        }

        with patch("datadog_mcp.tools.query_metric_formula.fetch_metric_formula", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_formula_result

            result = await query_metric_formula.handle_call(mock_request)

            assert isinstance(result, CallToolResult)
            assert result.isError is False
            assert len(result.content) > 0
            assert isinstance(result.content[0], TextContent)

    @pytest.mark.asyncio
    async def test_handle_formula_missing_formula(self):
        """Test error when formula is missing"""
        mock_request = MagicMock()
        mock_request.arguments = {
            "queries": {"a": {"metric_name": "metric1"}},
        }
        mock_request.params = MagicMock()
        mock_request.params.arguments = mock_request.arguments

        result = await query_metric_formula.handle_call(mock_request)

        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert "formula" in result.content[0].text.lower()

    @pytest.mark.asyncio
    async def test_handle_formula_variable_mismatch(self):
        """Test error when formula variables don't match queries"""
        mock_request = MagicMock()
        mock_request.arguments = {
            "formula": "a / b * c",  # Expects a, b, c
            "queries": {
                "a": {"metric_name": "metric1"},
                "b": {"metric_name": "metric2"},
                # Missing 'c'
            },
        }
        mock_request.params = MagicMock()
        mock_request.params.arguments = mock_request.arguments

        result = await query_metric_formula.handle_call(mock_request)

        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert "undefined" in result.content[0].text.lower()

    @pytest.mark.asyncio
    async def test_handle_formula_with_filters(self):
        """Test formula query with filters"""
        mock_request = MagicMock()
        mock_request.arguments = {
            "formula": "a - b",
            "queries": {
                "a": {"metric_name": "memory.total"},
                "b": {"metric_name": "memory.free"},
            },
            "filters": {"service": "web"},
            "format": "timeseries",
        }
        mock_request.params = MagicMock()
        mock_request.params.arguments = mock_request.arguments

        mock_formula_result = {
            "data": {"attributes": {"series": [{"pointlist": [[1640995200000, 5.5]]}]}}
        }

        with patch("datadog_mcp.tools.query_metric_formula.fetch_metric_formula", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_formula_result

            result = await query_metric_formula.handle_call(mock_request)

            assert isinstance(result, CallToolResult)
            assert result.isError is False

    @pytest.mark.asyncio
    async def test_handle_formula_json_format(self):
        """Test formula query with JSON output"""
        mock_request = MagicMock()
        mock_request.arguments = {
            "formula": "a + b",
            "queries": {
                "a": {"metric_name": "metric1"},
                "b": {"metric_name": "metric2"},
            },
            "format": "json",
        }
        mock_request.params = MagicMock()
        mock_request.params.arguments = mock_request.arguments

        mock_formula_result = {
            "data": {"attributes": {"series": [{"pointlist": [[1640995200000, 5.5]]}]}}
        }

        with patch("datadog_mcp.tools.query_metric_formula.fetch_metric_formula", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_formula_result

            result = await query_metric_formula.handle_call(mock_request)

            assert isinstance(result, CallToolResult)
            assert result.isError is False
            # JSON format should be valid JSON
            content_text = result.content[0].text
            assert "=" in content_text  # At minimum should have separator


class TestCheckDeploymentHandler:
    """Test check_deployment tool handler"""

    @pytest.mark.asyncio
    async def test_handle_deployment_check_success(self):
        """Test successful deployment check"""
        mock_request = MagicMock()
        mock_request.arguments = {
            "service": "web",
            "version_field": "git.commit.sha",
            "version_value": "abc123",
            "format": "summary",
        }
        mock_request.params = MagicMock()
        mock_request.params.arguments = mock_request.arguments

        mock_status = {
            "status": "deployed",
            "service": "web",
            "version_field": "git.commit.sha",
            "version_value": "abc123",
            "log_count": 5,
            "first_seen": "2026-02-05T10:00:00Z",
            "last_seen": "2026-02-05T10:10:00Z",
            "logs": [],
        }

        with patch("datadog_mcp.tools.check_deployment.check_deployment_status", new_callable=AsyncMock) as mock_check:
            mock_check.return_value = mock_status

            result = await check_deployment.handle_call(mock_request)

            assert isinstance(result, CallToolResult)
            assert result.isError is False
            assert len(result.content) > 0
            content_text = result.content[0].text
            assert "✅" in content_text or "logs found" in content_text.lower()

    @pytest.mark.asyncio
    async def test_handle_deployment_check_not_found(self):
        """Test deployment check when version not found"""
        mock_request = MagicMock()
        mock_request.arguments = {
            "service": "api",
            "version_field": "version",
            "version_value": "nonexistent",
            "format": "summary",
        }
        mock_request.params = MagicMock()
        mock_request.params.arguments = mock_request.arguments

        mock_status = {
            "status": "not_found",
            "service": "api",
            "version_field": "version",
            "version_value": "nonexistent",
            "log_count": 0,
            "first_seen": None,
            "last_seen": None,
            "logs": [],
        }

        with patch("datadog_mcp.tools.check_deployment.check_deployment_status", new_callable=AsyncMock) as mock_check:
            mock_check.return_value = mock_status

            result = await check_deployment.handle_call(mock_request)

            assert isinstance(result, CallToolResult)
            assert result.isError is False
            content_text = result.content[0].text
            assert "not found" in content_text.lower() or "❌" in content_text

    @pytest.mark.asyncio
    async def test_handle_deployment_missing_service(self):
        """Test error when service is missing"""
        mock_request = MagicMock()
        mock_request.arguments = {
            "version_field": "git.commit.sha",
            "version_value": "abc123",
        }
        mock_request.params = MagicMock()
        mock_request.params.arguments = mock_request.arguments

        result = await check_deployment.handle_call(mock_request)

        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert "service" in result.content[0].text.lower()

    @pytest.mark.asyncio
    async def test_handle_deployment_with_environment(self):
        """Test deployment check with environment filter"""
        mock_request = MagicMock()
        mock_request.arguments = {
            "service": "web",
            "version_field": "git.commit.sha",
            "version_value": "abc123",
            "environment": "prod",
            "format": "detailed",
        }
        mock_request.params = MagicMock()
        mock_request.params.arguments = mock_request.arguments

        mock_status = {
            "status": "deployed",
            "service": "web",
            "version_field": "git.commit.sha",
            "version_value": "abc123",
            "environment": "prod",
            "log_count": 3,
            "first_seen": "2026-02-05T10:00:00Z",
            "last_seen": "2026-02-05T10:05:00Z",
            "logs": [
                {
                    "timestamp": "2026-02-05T10:05:00Z",
                    "service": "web",
                    "message": "Version running",
                }
            ],
        }

        with patch("datadog_mcp.tools.check_deployment.check_deployment_status", new_callable=AsyncMock) as mock_check:
            mock_check.return_value = mock_status

            result = await check_deployment.handle_call(mock_request)

            assert isinstance(result, CallToolResult)
            assert result.isError is False


class TestFormatters:
    """Test formatter functions for new tools"""

    def test_format_formula_result_summary(self):
        """Test formula result summary formatting"""
        result = {
            "data": {
                "attributes": {
                    "series": [
                        {
                            "pointlist": [
                                [1640995200000, 5.5],
                                [1640995260000, 6.2],
                                [1640995320000, 5.8],
                            ]
                        }
                    ]
                }
            }
        }

        from datadog_mcp.utils.formatters import format_formula_result_summary

        formatted = format_formula_result_summary(result)

        assert isinstance(formatted, str)
        assert len(formatted) > 0
        # Should contain statistics
        assert ("Latest" in formatted or "latest" in formatted.lower())

    def test_format_formula_result_timeseries(self):
        """Test formula result timeseries formatting"""
        result = {
            "data": {
                "attributes": {
                    "series": [
                        {
                            "pointlist": [
                                [1640995200000, 5.5],
                                [1640995260000, 6.2],
                            ]
                        }
                    ]
                }
            }
        }

        from datadog_mcp.utils.formatters import format_formula_result_timeseries

        formatted = format_formula_result_timeseries(result)

        assert isinstance(formatted, str)
        assert len(formatted) > 0
        # Should contain points
        assert "point" in formatted.lower() or len(formatted.split("\n")) > 2

    def test_format_deployment_status_summary(self):
        """Test deployment status summary formatting"""
        status = {
            "status": "deployed",
            "service": "web",
            "version_field": "git.commit.sha",
            "version_value": "abc123",
            "environment": "prod",
            "log_count": 5,
            "first_seen": "2026-02-05T10:00:00Z",
            "last_seen": "2026-02-05T10:10:00Z",
        }

        from datadog_mcp.utils.formatters import format_deployment_status_summary

        formatted = format_deployment_status_summary(status)

        assert isinstance(formatted, str)
        assert len(formatted) > 0
        assert "web" in formatted
        assert "abc123" in formatted
        assert "✅" in formatted  # Deployed indicator

    def test_format_deployment_status_not_found(self):
        """Test deployment status formatting when not found"""
        status = {
            "status": "not_found",
            "service": "api",
            "version_field": "version",
            "version_value": "v2.0.0",
            "environment": "all",
            "log_count": 0,
            "first_seen": None,
            "last_seen": None,
        }

        from datadog_mcp.utils.formatters import format_deployment_status_summary

        formatted = format_deployment_status_summary(status)

        assert isinstance(formatted, str)
        assert len(formatted) > 0
        assert "❌" in formatted  # Not found indicator


if __name__ == "__main__":
    pytest.main([__file__])
