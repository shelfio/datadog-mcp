"""
Tests for dashboard management functionality
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from datadog_mcp.tools import dashboard_update_title
from datadog_mcp.utils import datadog_client
from mcp.types import CallToolResult, TextContent


class TestDashboardToolDefinitions:
    """Test dashboard tool definitions"""

    def test_dashboard_update_title_tool_definition(self):
        """Test dashboard_update_title tool definition"""
        tool_def = dashboard_update_title.get_tool_definition()

        assert tool_def.name == "dashboard_update_title"
        assert "dashboard" in tool_def.description.lower()
        assert "title" in tool_def.description.lower()
        assert hasattr(tool_def, "inputSchema")

        schema = tool_def.inputSchema
        assert "properties" in schema

        properties = schema["properties"]
        assert "dashboard_id" in properties
        assert "new_title" in properties

        # Check required fields
        assert "required" in schema
        assert "dashboard_id" in schema["required"]
        assert "new_title" in schema["required"]


class TestDashboardRetrieval:
    """Test dashboard data retrieval"""

    @pytest.mark.asyncio
    async def test_fetch_dashboard_basic(self):
        """Test basic dashboard fetching"""
        mock_response_data = {
            "id": "abc-123-xyz",
            "title": "Test Dashboard",
            "widgets": [],
            "url": "/dashboard/abc-123-xyz",
        }

        with patch("datadog_mcp.utils.datadog_client.httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await datadog_client.fetch_dashboard("abc-123-xyz")

            assert isinstance(result, dict)
            assert result["id"] == "abc-123-xyz"
            assert result["title"] == "Test Dashboard"

    @pytest.mark.asyncio
    async def test_update_dashboard_title_api(self):
        """Test dashboard title update via API"""
        mock_get_response_data = {
            "id": "abc-123-xyz",
            "title": "Old Title",
            "widgets": [],
            "url": "/dashboard/abc-123-xyz",
        }

        mock_put_response_data = {
            "id": "abc-123-xyz",
            "title": "New Title",
            "widgets": [],
            "url": "/dashboard/abc-123-xyz",
        }

        with patch("datadog_mcp.utils.datadog_client.httpx.AsyncClient") as mock_client:
            # Mock GET response for fetch_dashboard
            mock_get = MagicMock()
            mock_get.json.return_value = mock_get_response_data
            mock_get.raise_for_status = MagicMock()

            # Mock PUT response for update
            mock_put = MagicMock()
            mock_put.json.return_value = mock_put_response_data
            mock_put.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_get
            )
            mock_client.return_value.__aenter__.return_value.put = AsyncMock(
                return_value=mock_put
            )

            result = await datadog_client.update_dashboard_title(
                "abc-123-xyz", "New Title"
            )

            assert isinstance(result, dict)
            assert result["title"] == "New Title"
            assert result["_old_title"] == "Old Title"


class TestDashboardToolHandlers:
    """Test dashboard tool handlers"""

    @pytest.mark.asyncio
    async def test_handle_dashboard_update_title_success(self):
        """Test successful dashboard title update"""
        mock_request = MagicMock()
        mock_request.arguments = {
            "dashboard_id": "abc-123-xyz",
            "new_title": "Updated Dashboard Title",
        }

        mock_update_result = {
            "id": "abc-123-xyz",
            "title": "Updated Dashboard Title",
            "url": "/dashboard/abc-123-xyz",
            "_old_title": "Old Dashboard Title",
        }

        with patch(
            "datadog_mcp.tools.dashboard_update_title.update_dashboard_title",
            new_callable=AsyncMock,
        ) as mock_update:
            mock_update.return_value = mock_update_result

            result = await dashboard_update_title.handle_call(mock_request)

            assert isinstance(result, CallToolResult)
            assert result.isError is False
            assert len(result.content) > 0
            assert isinstance(result.content[0], TextContent)

            content_text = result.content[0].text
            assert "abc-123-xyz" in content_text
            assert "Updated Dashboard Title" in content_text

    @pytest.mark.asyncio
    async def test_handle_dashboard_update_title_missing_dashboard_id(self):
        """Test error when dashboard_id is missing"""
        mock_request = MagicMock()
        mock_request.arguments = {"new_title": "New Title"}

        result = await dashboard_update_title.handle_call(mock_request)

        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert "dashboard_id" in result.content[0].text.lower()

    @pytest.mark.asyncio
    async def test_handle_dashboard_update_title_missing_new_title(self):
        """Test error when new_title is missing"""
        mock_request = MagicMock()
        mock_request.arguments = {"dashboard_id": "abc-123-xyz"}

        result = await dashboard_update_title.handle_call(mock_request)

        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert "new_title" in result.content[0].text.lower()

    @pytest.mark.asyncio
    async def test_handle_dashboard_update_title_api_error(self):
        """Test error handling when API call fails"""
        mock_request = MagicMock()
        mock_request.arguments = {
            "dashboard_id": "invalid-id",
            "new_title": "New Title",
        }

        with patch(
            "datadog_mcp.tools.dashboard_update_title.update_dashboard_title",
            new_callable=AsyncMock,
        ) as mock_update:
            mock_update.side_effect = Exception("Dashboard not found")

            result = await dashboard_update_title.handle_call(mock_request)

            assert isinstance(result, CallToolResult)
            assert result.isError is True
            assert "error" in result.content[0].text.lower()


class TestDashboardValidation:
    """Test dashboard input validation"""

    @pytest.mark.asyncio
    async def test_empty_dashboard_id(self):
        """Test handling of empty dashboard ID"""
        mock_request = MagicMock()
        mock_request.arguments = {"dashboard_id": "", "new_title": "New Title"}

        result = await dashboard_update_title.handle_call(mock_request)

        assert isinstance(result, CallToolResult)
        assert result.isError is True

    @pytest.mark.asyncio
    async def test_empty_new_title(self):
        """Test handling of empty new title"""
        mock_request = MagicMock()
        mock_request.arguments = {"dashboard_id": "abc-123-xyz", "new_title": ""}

        result = await dashboard_update_title.handle_call(mock_request)

        assert isinstance(result, CallToolResult)
        assert result.isError is True


if __name__ == "__main__":
    pytest.main([__file__])
