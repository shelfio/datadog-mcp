"""
Tests for monitor_edit tool functionality
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import httpx
from datadog_mcp.tools import monitor_edit
from datadog_mcp.utils import datadog_client
from mcp.types import CallToolResult, TextContent


class TestMonitorEditToolDefinition:
    """Test monitor_edit tool definition"""

    def test_monitor_edit_tool_definition(self):
        """Test monitor_edit tool definition"""
        tool_def = monitor_edit.get_tool_definition()

        assert tool_def.name == "monitor_edit"
        assert "monitor" in tool_def.description.lower()
        assert "update" in tool_def.description.lower()
        assert hasattr(tool_def, "inputSchema")

        schema = tool_def.inputSchema
        assert "properties" in schema

        properties = schema["properties"]
        assert "monitor_id" in properties
        assert "name" in properties
        assert "message" in properties
        assert "tags" in properties
        assert "priority" in properties

    def test_monitor_edit_required_fields(self):
        """Test monitor_edit required fields"""
        tool_def = monitor_edit.get_tool_definition()
        schema = tool_def.inputSchema

        assert "required" in schema
        assert "monitor_id" in schema["required"]
        assert len(schema["required"]) == 1

    def test_monitor_edit_monitor_id_type(self):
        """Test monitor_id is integer type"""
        tool_def = monitor_edit.get_tool_definition()
        schema = tool_def.inputSchema

        monitor_id_prop = schema["properties"]["monitor_id"]
        assert monitor_id_prop["type"] == "integer"

    def test_monitor_edit_priority_constraints(self):
        """Test priority has valid constraints"""
        tool_def = monitor_edit.get_tool_definition()
        schema = tool_def.inputSchema

        priority_prop = schema["properties"]["priority"]
        assert priority_prop["type"] == "integer"
        assert priority_prop["minimum"] == 1
        assert priority_prop["maximum"] == 5

    def test_monitor_edit_tags_array_type(self):
        """Test tags is array of strings"""
        tool_def = monitor_edit.get_tool_definition()
        schema = tool_def.inputSchema

        tags_prop = schema["properties"]["tags"]
        assert tags_prop["type"] == "array"
        assert tags_prop["items"]["type"] == "string"

    def test_monitor_edit_query_property(self):
        """Test query property exists with correct type and description"""
        tool_def = monitor_edit.get_tool_definition()
        schema = tool_def.inputSchema

        assert "query" in schema["properties"]
        query_prop = schema["properties"]["query"]
        assert query_prop["type"] == "string"
        assert "description" in query_prop
        assert "query" not in schema.get("required", [])


class TestMonitorEditRetrieval:
    """Test monitor update via update_monitor client function"""

    @pytest.mark.asyncio
    async def test_update_monitor_basic(self):
        """Test basic monitor update"""
        mock_get_response = {
            "id": 12345,
            "name": "Old Name",
            "type": "metric alert",
            "overall_state": "OK",
            "message": "Old message",
            "tags": ["env:prod"],
            "priority": 3,
            "query": "avg(last_5m):avg:system.cpu.user{*} > 90",
        }

        mock_put_response = {
            "id": 12345,
            "name": "New Name",
            "type": "metric alert",
            "overall_state": "OK",
            "message": "Old message",
            "tags": ["env:prod"],
            "priority": 3,
            "query": "avg(last_5m):avg:system.cpu.user{*} > 90",
        }

        with patch("datadog_mcp.utils.datadog_client.httpx.AsyncClient") as mock_client:
            mock_get = MagicMock()
            mock_get.json.return_value = mock_get_response
            mock_get.raise_for_status = MagicMock()

            mock_put = MagicMock()
            mock_put.json.return_value = mock_put_response
            mock_put.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_get
            )
            mock_client.return_value.__aenter__.return_value.put = AsyncMock(
                return_value=mock_put
            )

            result = await datadog_client.update_monitor(12345, name="New Name")

            assert isinstance(result, dict)
            assert result["name"] == "New Name"

    @pytest.mark.asyncio
    async def test_update_monitor_multiple_fields(self):
        """Test updating multiple fields at once"""
        mock_get_response = {
            "id": 12345,
            "name": "Old Name",
            "type": "metric alert",
            "overall_state": "OK",
            "message": "Old message",
            "tags": ["env:prod"],
            "priority": 3,
            "query": "test query",
        }

        mock_put_response = {
            "id": 12345,
            "name": "New Name",
            "type": "metric alert",
            "overall_state": "OK",
            "message": "New message",
            "tags": ["env:staging", "team:infra"],
            "priority": 1,
            "query": "test query",
        }

        with patch("datadog_mcp.utils.datadog_client.httpx.AsyncClient") as mock_client:
            mock_get = MagicMock()
            mock_get.json.return_value = mock_get_response
            mock_get.raise_for_status = MagicMock()

            mock_put = MagicMock()
            mock_put.json.return_value = mock_put_response
            mock_put.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_get
            )
            mock_client.return_value.__aenter__.return_value.put = AsyncMock(
                return_value=mock_put
            )

            result = await datadog_client.update_monitor(
                12345,
                name="New Name",
                message="New message",
                tags=["env:staging", "team:infra"],
                priority=1,
            )

            assert result["name"] == "New Name"
            assert result["message"] == "New message"
            assert result["priority"] == 1

    @pytest.mark.asyncio
    async def test_update_monitor_api_error(self):
        """Test update_monitor handles API errors"""
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
                await datadog_client.update_monitor(99999999, name="Test")


class TestMonitorEditHandlers:
    """Test monitor_edit tool handlers"""

    @pytest.mark.asyncio
    async def test_handle_monitor_edit_success_name(self):
        """Test successful monitor name update"""
        mock_request = MagicMock()
        mock_request.arguments = {"monitor_id": 12345, "name": "New Monitor Name"}

        mock_result = {
            "id": 12345,
            "name": "New Monitor Name",
        }

        with patch(
            "datadog_mcp.tools.monitor_edit.update_monitor",
            new_callable=AsyncMock,
        ) as mock_update:
            mock_update.return_value = mock_result

            result = await monitor_edit.handle_call(mock_request)

            assert isinstance(result, CallToolResult)
            assert result.isError is False
            assert "12345" in result.content[0].text
            assert "updated successfully" in result.content[0].text.lower()

    @pytest.mark.asyncio
    async def test_handle_monitor_edit_success_message(self):
        """Test successful monitor message update"""
        mock_request = MagicMock()
        mock_request.arguments = {"monitor_id": 12345, "message": "New alert message"}

        with patch(
            "datadog_mcp.tools.monitor_edit.update_monitor",
            new_callable=AsyncMock,
        ) as mock_update:
            mock_update.return_value = {"id": 12345}

            result = await monitor_edit.handle_call(mock_request)

            assert isinstance(result, CallToolResult)
            assert result.isError is False
            mock_update.assert_called_once_with(12345, message="New alert message")

    @pytest.mark.asyncio
    async def test_handle_monitor_edit_success_tags(self):
        """Test successful monitor tags update"""
        mock_request = MagicMock()
        mock_request.arguments = {
            "monitor_id": 12345,
            "tags": ["env:prod", "team:backend"],
        }

        with patch(
            "datadog_mcp.tools.monitor_edit.update_monitor",
            new_callable=AsyncMock,
        ) as mock_update:
            mock_update.return_value = {"id": 12345}

            result = await monitor_edit.handle_call(mock_request)

            assert isinstance(result, CallToolResult)
            assert result.isError is False
            mock_update.assert_called_once_with(
                12345, tags=["env:prod", "team:backend"]
            )

    @pytest.mark.asyncio
    async def test_handle_monitor_edit_success_priority(self):
        """Test successful monitor priority update"""
        mock_request = MagicMock()
        mock_request.arguments = {"monitor_id": 12345, "priority": 1}

        with patch(
            "datadog_mcp.tools.monitor_edit.update_monitor",
            new_callable=AsyncMock,
        ) as mock_update:
            mock_update.return_value = {"id": 12345}

            result = await monitor_edit.handle_call(mock_request)

            assert isinstance(result, CallToolResult)
            assert result.isError is False
            mock_update.assert_called_once_with(12345, priority=1)

    @pytest.mark.asyncio
    async def test_handle_monitor_edit_success_multiple_fields(self):
        """Test successful update of multiple fields"""
        mock_request = MagicMock()
        mock_request.arguments = {
            "monitor_id": 12345,
            "name": "New Name",
            "message": "New message",
            "tags": ["env:staging"],
            "priority": 2,
        }

        with patch(
            "datadog_mcp.tools.monitor_edit.update_monitor",
            new_callable=AsyncMock,
        ) as mock_update:
            mock_update.return_value = {"id": 12345}

            result = await monitor_edit.handle_call(mock_request)

            assert isinstance(result, CallToolResult)
            assert result.isError is False
            mock_update.assert_called_once_with(
                12345,
                name="New Name",
                message="New message",
                tags=["env:staging"],
                priority=2,
            )

    @pytest.mark.asyncio
    async def test_handle_monitor_edit_success_query_only(self):
        """Test successful monitor query-only update"""
        mock_request = MagicMock()
        mock_request.arguments = {
            "monitor_id": 12345,
            "query": "avg(last_5m):avg:system.cpu.user{*} > 95",
        }

        with patch(
            "datadog_mcp.tools.monitor_edit.update_monitor",
            new_callable=AsyncMock,
        ) as mock_update:
            mock_update.return_value = {"id": 12345}

            result = await monitor_edit.handle_call(mock_request)

            assert isinstance(result, CallToolResult)
            assert result.isError is False
            mock_update.assert_called_once_with(
                12345, query="avg(last_5m):avg:system.cpu.user{*} > 95"
            )

    @pytest.mark.asyncio
    async def test_handle_monitor_edit_success_query_with_other_fields(self):
        """Test successful update of query with other fields"""
        mock_request = MagicMock()
        mock_request.arguments = {
            "monitor_id": 12345,
            "name": "Updated Monitor",
            "query": "avg(last_10m):avg:system.memory.used{*} > 80",
        }

        with patch(
            "datadog_mcp.tools.monitor_edit.update_monitor",
            new_callable=AsyncMock,
        ) as mock_update:
            mock_update.return_value = {"id": 12345}

            result = await monitor_edit.handle_call(mock_request)

            assert isinstance(result, CallToolResult)
            assert result.isError is False
            mock_update.assert_called_once_with(
                12345,
                name="Updated Monitor",
                query="avg(last_10m):avg:system.memory.used{*} > 80",
            )

    @pytest.mark.asyncio
    async def test_handle_monitor_edit_missing_monitor_id(self):
        """Test error when monitor_id is missing"""
        mock_request = MagicMock()
        mock_request.arguments = {"name": "New Name"}

        result = await monitor_edit.handle_call(mock_request)

        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert "monitor_id" in result.content[0].text.lower()

    @pytest.mark.asyncio
    async def test_handle_monitor_edit_none_arguments(self):
        """Test error when arguments is None"""
        mock_request = MagicMock()
        mock_request.arguments = None

        result = await monitor_edit.handle_call(mock_request)

        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert "monitor_id" in result.content[0].text.lower()

    @pytest.mark.asyncio
    async def test_handle_monitor_edit_no_update_fields(self):
        """Test error when no update fields are provided"""
        mock_request = MagicMock()
        mock_request.arguments = {"monitor_id": 12345}

        result = await monitor_edit.handle_call(mock_request)

        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert "at least one field" in result.content[0].text.lower()

    @pytest.mark.asyncio
    async def test_handle_monitor_edit_api_error(self):
        """Test error handling when API call fails"""
        mock_request = MagicMock()
        mock_request.arguments = {"monitor_id": 12345, "name": "New Name"}

        with patch(
            "datadog_mcp.tools.monitor_edit.update_monitor",
            new_callable=AsyncMock,
        ) as mock_update:
            mock_update.side_effect = Exception("API error")

            result = await monitor_edit.handle_call(mock_request)

            assert isinstance(result, CallToolResult)
            assert result.isError is True
            assert "error" in result.content[0].text.lower()

    @pytest.mark.asyncio
    async def test_handle_monitor_edit_not_found(self):
        """Test handling of monitor not found (404)"""
        mock_request = MagicMock()
        mock_request.arguments = {"monitor_id": 99999999, "name": "New Name"}

        with patch(
            "datadog_mcp.tools.monitor_edit.update_monitor",
            new_callable=AsyncMock,
        ) as mock_update:
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_update.side_effect = httpx.HTTPStatusError(
                "Not Found",
                request=MagicMock(),
                response=mock_response,
            )

            result = await monitor_edit.handle_call(mock_request)

            assert isinstance(result, CallToolResult)
            assert result.isError is True
            assert "not found" in result.content[0].text.lower()

    @pytest.mark.asyncio
    async def test_handle_monitor_edit_permission_denied(self):
        """Test handling of permission denied (403)"""
        mock_request = MagicMock()
        mock_request.arguments = {"monitor_id": 12345, "name": "New Name"}

        with patch(
            "datadog_mcp.tools.monitor_edit.update_monitor",
            new_callable=AsyncMock,
        ) as mock_update:
            mock_response = MagicMock()
            mock_response.status_code = 403
            mock_update.side_effect = httpx.HTTPStatusError(
                "Forbidden",
                request=MagicMock(),
                response=mock_response,
            )

            result = await monitor_edit.handle_call(mock_request)

            assert isinstance(result, CallToolResult)
            assert result.isError is True
            assert "permission denied" in result.content[0].text.lower()


class TestMonitorEditValidation:
    """Test monitor_edit input validation"""

    @pytest.mark.asyncio
    async def test_invalid_priority_too_low(self):
        """Test error when priority is below 1"""
        mock_request = MagicMock()
        mock_request.arguments = {"monitor_id": 12345, "priority": 0}

        result = await monitor_edit.handle_call(mock_request)

        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert "priority" in result.content[0].text.lower()

    @pytest.mark.asyncio
    async def test_invalid_priority_too_high(self):
        """Test error when priority is above 5"""
        mock_request = MagicMock()
        mock_request.arguments = {"monitor_id": 12345, "priority": 6}

        result = await monitor_edit.handle_call(mock_request)

        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert "priority" in result.content[0].text.lower()

    @pytest.mark.asyncio
    async def test_invalid_priority_negative(self):
        """Test error when priority is negative"""
        mock_request = MagicMock()
        mock_request.arguments = {"monitor_id": 12345, "priority": -1}

        result = await monitor_edit.handle_call(mock_request)

        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert "priority" in result.content[0].text.lower()

    @pytest.mark.asyncio
    async def test_valid_priority_min(self):
        """Test valid priority at minimum (1)"""
        mock_request = MagicMock()
        mock_request.arguments = {"monitor_id": 12345, "priority": 1}

        with patch(
            "datadog_mcp.tools.monitor_edit.update_monitor",
            new_callable=AsyncMock,
        ) as mock_update:
            mock_update.return_value = {"id": 12345}

            result = await monitor_edit.handle_call(mock_request)

            assert isinstance(result, CallToolResult)
            assert result.isError is False

    @pytest.mark.asyncio
    async def test_valid_priority_max(self):
        """Test valid priority at maximum (5)"""
        mock_request = MagicMock()
        mock_request.arguments = {"monitor_id": 12345, "priority": 5}

        with patch(
            "datadog_mcp.tools.monitor_edit.update_monitor",
            new_callable=AsyncMock,
        ) as mock_update:
            mock_update.return_value = {"id": 12345}

            result = await monitor_edit.handle_call(mock_request)

            assert isinstance(result, CallToolResult)
            assert result.isError is False

    @pytest.mark.asyncio
    async def test_empty_name_is_valid(self):
        """Test that empty string name is accepted (may be valid for API)"""
        mock_request = MagicMock()
        mock_request.arguments = {"monitor_id": 12345, "name": ""}

        with patch(
            "datadog_mcp.tools.monitor_edit.update_monitor",
            new_callable=AsyncMock,
        ) as mock_update:
            mock_update.return_value = {"id": 12345}

            result = await monitor_edit.handle_call(mock_request)

            assert isinstance(result, CallToolResult)
            assert result.isError is False

    @pytest.mark.asyncio
    async def test_empty_tags_list_is_valid(self):
        """Test that empty tags list is accepted"""
        mock_request = MagicMock()
        mock_request.arguments = {"monitor_id": 12345, "tags": []}

        with patch(
            "datadog_mcp.tools.monitor_edit.update_monitor",
            new_callable=AsyncMock,
        ) as mock_update:
            mock_update.return_value = {"id": 12345}

            result = await monitor_edit.handle_call(mock_request)

            assert isinstance(result, CallToolResult)
            assert result.isError is False


if __name__ == "__main__":
    pytest.main([__file__])
