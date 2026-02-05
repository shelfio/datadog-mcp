"""
Tests for notification rules functionality
"""

import pytest
import json
from unittest.mock import patch, AsyncMock, MagicMock
from datadog_mcp.tools import list_notification_rules
from datadog_mcp.utils import datadog_client
from mcp.types import CallToolResult, TextContent


class TestNotificationRulesToolDefinition:
    """Test notification rules tool definition"""

    def test_list_notification_rules_tool_definition(self):
        """Test list_notification_rules tool definition"""
        tool_def = list_notification_rules.get_tool_definition()

        assert tool_def.name == "list_notification_rules"
        assert "notification" in tool_def.description.lower()
        assert hasattr(tool_def, "inputSchema")

        schema = tool_def.inputSchema
        assert "properties" in schema

        properties = schema["properties"]
        expected_params = ["text", "tags", "recipients", "format", "page_size", "page"]
        for param in expected_params:
            assert param in properties, f"Parameter {param} missing from list_notification_rules schema"

    def test_list_notification_rules_format_options(self):
        """Test list_notification_rules format options"""
        tool_def = list_notification_rules.get_tool_definition()
        schema = tool_def.inputSchema

        format_prop = schema["properties"]["format"]
        assert "enum" in format_prop
        assert "table" in format_prop["enum"]
        assert "json" in format_prop["enum"]
        assert "summary" in format_prop["enum"]


class TestNotificationRulesRetrieval:
    """Test notification rules data retrieval"""

    @pytest.mark.asyncio
    async def test_fetch_notification_rules_basic(self):
        """Test basic notification rules fetching"""
        mock_response = {
            "data": [
                {
                    "id": "rule-123",
                    "type": "monitor-notification-rule",
                    "attributes": {
                        "name": "Production Alerts",
                        "filter": {
                            "scope": "env:prod",
                            "tags": ["team:platform"]
                        },
                        "recipients": ["@slack-alerts"],
                    }
                },
                {
                    "id": "rule-456",
                    "type": "monitor-notification-rule",
                    "attributes": {
                        "name": "Critical Alerts",
                        "filter": {
                            "scope": "priority:critical",
                            "tags": []
                        },
                        "recipients": ["@pagerduty"],
                        "conditional_recipients": {
                            "conditions": [],
                            "fallback_recipients": []
                        }
                    }
                },
            ]
        }

        with patch("datadog_mcp.utils.datadog_client.httpx.AsyncClient") as mock_client:
            mock_resp = MagicMock()
            mock_resp.json.return_value = mock_response
            mock_resp.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_resp
            )

            result = await datadog_client.fetch_notification_rules()

            assert isinstance(result, list)
            assert len(result) == 2
            assert result[0]["id"] == "rule-123"

    @pytest.mark.asyncio
    async def test_fetch_notification_rules_with_filters(self):
        """Test notification rules fetching with filter parameters"""
        mock_response = {"data": []}

        with patch("datadog_mcp.utils.datadog_client.httpx.AsyncClient") as mock_client:
            mock_resp = MagicMock()
            mock_resp.json.return_value = mock_response
            mock_resp.raise_for_status = MagicMock()

            mock_get = AsyncMock(return_value=mock_resp)
            mock_client.return_value.__aenter__.return_value.get = mock_get

            await datadog_client.fetch_notification_rules(
                text="prod",
                tags="team:platform",
                recipients="@slack",
                page_size=25,
                page=1,
            )

            call_args = mock_get.call_args
            params = call_args.kwargs.get("params", {})
            assert params.get("filter[text]") == "prod"
            assert params.get("filter[tags]") == "team:platform"
            assert params.get("filter[recipients]") == "@slack"
            assert params.get("page[size]") == 25
            assert params.get("page[offset]") == 1


class TestNotificationRulesToolHandlers:
    """Test notification rules tool handlers"""

    @pytest.mark.asyncio
    async def test_handle_list_notification_rules_success(self):
        """Test successful notification rules listing"""
        mock_request = MagicMock()
        mock_request.arguments = {"format": "table"}

        mock_rules = [
            {
                "id": "rule-123",
                "type": "monitor-notification-rule",
                "attributes": {
                    "name": "Production Alerts",
                    "filter": {
                        "scope": "env:prod",
                        "tags": ["team:platform", "priority:high"]
                    },
                    "recipients": ["@slack-alerts", "@pagerduty"],
                    "conditional_recipients": {
                        "conditions": [
                            {"scope": "severity:critical", "recipients": ["@pagerduty-oncall"]}
                        ],
                        "fallback_recipients": ["@slack-fallback"]
                    }
                }
            },
            {
                "id": "rule-456",
                "type": "monitor-notification-rule",
                "attributes": {
                    "name": "Critical Alerts",
                    "filter": {
                        "scope": "priority:critical",
                        "tags": []
                    },
                    "recipients": ["@pagerduty"],
                }
            },
        ]

        with patch(
            "datadog_mcp.tools.list_notification_rules.fetch_notification_rules",
            new_callable=AsyncMock,
        ) as mock_fetch:
            mock_fetch.return_value = mock_rules

            result = await list_notification_rules.handle_call(mock_request)

            assert isinstance(result, CallToolResult)
            assert result.isError is False
            assert len(result.content) > 0
            assert isinstance(result.content[0], TextContent)

            content_text = result.content[0].text
            assert "Production Alerts" in content_text
            assert "Critical Alerts" in content_text
            assert "1." in content_text
            assert "2." in content_text

    @pytest.mark.asyncio
    async def test_handle_list_notification_rules_table_format_details(self):
        """Test table format shows ID, name, scope, tags, recipients, conditional recipients"""
        mock_request = MagicMock()
        mock_request.arguments = {"format": "table"}

        mock_rules = [
            {
                "id": "rule-123",
                "type": "monitor-notification-rule",
                "attributes": {
                    "name": "Production Alerts",
                    "filter": {
                        "scope": "env:prod",
                        "tags": ["team:platform", "priority:high"]
                    },
                    "recipients": ["@slack-alerts", "@pagerduty"],
                    "conditional_recipients": {
                        "conditions": [
                            {"scope": "severity:critical", "recipients": ["@pagerduty-oncall"]}
                        ],
                        "fallback_recipients": ["@slack-fallback"]
                    }
                }
            },
        ]

        with patch(
            "datadog_mcp.tools.list_notification_rules.fetch_notification_rules",
            new_callable=AsyncMock,
        ) as mock_fetch:
            mock_fetch.return_value = mock_rules

            result = await list_notification_rules.handle_call(mock_request)

            content_text = result.content[0].text
            assert "rule-123" in content_text
            assert "Production Alerts" in content_text
            assert "env:prod" in content_text
            assert "team:platform" in content_text
            assert "@slack-alerts" in content_text
            assert "@pagerduty-oncall" in content_text

    @pytest.mark.asyncio
    async def test_handle_list_notification_rules_json_format(self):
        """Test notification rules listing with JSON format"""
        mock_request = MagicMock()
        mock_request.arguments = {"format": "json"}

        mock_rules = [
            {
                "id": "rule-123",
                "type": "monitor-notification-rule",
                "attributes": {
                    "name": "Test Rule",
                    "filter": {"scope": "env:test", "tags": []},
                    "recipients": ["@slack-test"],
                }
            }
        ]

        with patch(
            "datadog_mcp.tools.list_notification_rules.fetch_notification_rules",
            new_callable=AsyncMock,
        ) as mock_fetch:
            mock_fetch.return_value = mock_rules

            result = await list_notification_rules.handle_call(mock_request)

            assert isinstance(result, CallToolResult)
            assert result.isError is False

            content_text = result.content[0].text
            parsed = json.loads(content_text)
            assert len(parsed) == 1
            assert parsed[0]["id"] == "rule-123"

    @pytest.mark.asyncio
    async def test_handle_list_notification_rules_summary_format(self):
        """Test notification rules listing with summary format"""
        mock_request = MagicMock()
        mock_request.arguments = {"format": "summary"}

        mock_rules = [
            {
                "id": "rule-1",
                "attributes": {"name": "Rule1", "filter": {"scope": "env:prod", "tags": []}, "recipients": ["@slack"]}
            },
            {
                "id": "rule-2",
                "attributes": {"name": "Rule2", "filter": {"scope": "env:staging", "tags": []}, "recipients": ["@email"]}
            },
            {
                "id": "rule-3",
                "attributes": {"name": "Rule3", "filter": {"scope": "env:prod", "tags": []}, "recipients": ["@pagerduty"]}
            },
        ]

        with patch(
            "datadog_mcp.tools.list_notification_rules.fetch_notification_rules",
            new_callable=AsyncMock,
        ) as mock_fetch:
            mock_fetch.return_value = mock_rules

            result = await list_notification_rules.handle_call(mock_request)

            assert isinstance(result, CallToolResult)
            assert result.isError is False

            content_text = result.content[0].text
            assert "Found 3 notification rules" in content_text

    @pytest.mark.asyncio
    async def test_handle_list_notification_rules_no_results(self):
        """Test notification rules listing with no results"""
        mock_request = MagicMock()
        mock_request.arguments = {"format": "table"}

        with patch(
            "datadog_mcp.tools.list_notification_rules.fetch_notification_rules",
            new_callable=AsyncMock,
        ) as mock_fetch:
            mock_fetch.return_value = []

            result = await list_notification_rules.handle_call(mock_request)

            assert isinstance(result, CallToolResult)
            assert result.isError is False
            assert "No notification rules found" in result.content[0].text

    @pytest.mark.asyncio
    async def test_handle_list_notification_rules_error(self):
        """Test error handling in notification rules listing"""
        mock_request = MagicMock()
        mock_request.arguments = {}

        with patch(
            "datadog_mcp.tools.list_notification_rules.fetch_notification_rules",
            new_callable=AsyncMock,
        ) as mock_fetch:
            mock_fetch.side_effect = Exception("API error")

            result = await list_notification_rules.handle_call(mock_request)

            assert isinstance(result, CallToolResult)
            assert result.isError is True
            assert "error" in result.content[0].text.lower()


if __name__ == "__main__":
    pytest.main([__file__])
