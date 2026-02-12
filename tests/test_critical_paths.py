"""
Critical path tests for Datadog MCP
Tests monitor CRUD, CI visibility, and notebook operations
"""

import pytest
from unittest.mock import AsyncMock, patch
from datadog_mcp.tools import (
    get_monitor,
    create_monitor,
    update_monitor,
    delete_monitor,
)
from mcp.types import CallToolRequest


class TestMonitorCRUD:
    """Test monitor create, read, update, delete operations"""

    @pytest.mark.asyncio
    async def test_get_monitor_with_string_id(self):
        """Test that get_monitor accepts string monitor IDs and converts to int"""
        request = CallToolRequest(
            method="tools/call",
            params={
                "name": "get_monitor",
                "arguments": {"monitor_id": "12345"}
            }
        )

        with patch("datadog_mcp.tools.get_monitor.get_monitor", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {
                "id": 12345,
                "name": "CPU Alert",
                "type": "metric alert",
                "overall_state": "ok",
                "query": "avg:system.cpu{*}",
            }

            result = await get_monitor.handle_call(request)

            assert result.isError is False
            assert "12345" in result.content[0].text
            # Verify monitor_id was converted to int
            mock_get.assert_called_once_with(12345)

    @pytest.mark.asyncio
    async def test_get_monitor_invalid_id_format(self):
        """Test that get_monitor rejects non-numeric string IDs"""
        request = CallToolRequest(
            method="tools/call",
            params={
                "name": "get_monitor",
                "arguments": {"monitor_id": "not-a-number"}
            }
        )

        result = await get_monitor.handle_call(request)

        assert result.isError is True
        assert "valid integer" in result.content[0].text

    @pytest.mark.asyncio
    async def test_get_monitor_missing_id(self):
        """Test that get_monitor requires monitor_id"""
        request = CallToolRequest(
            method="tools/call",
            params={
                "name": "get_monitor",
                "arguments": {}
            }
        )

        result = await get_monitor.handle_call(request)

        assert result.isError is True
        assert "required" in result.content[0].text

    @pytest.mark.asyncio
    async def test_create_monitor(self):
        """Test monitor creation with valid parameters"""
        request = CallToolRequest(
            method="tools/call",
            params={
                "name": "create_monitor",
                "arguments": {
                    "name": "Test Monitor",
                    "type": "metric alert",
                    "query": "avg:system.cpu{*} > 0.8",
                    "message": "CPU too high",
                    "tags": ["test", "critical"],
                }
            }
        )

        with patch("datadog_mcp.tools.create_monitor.create_monitor", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = {
                "id": 12345,
                "name": "Test Monitor",
                "type": "metric alert",
                "overall_state": "ok",
            }

            result = await create_monitor.handle_call(request)

            assert result.isError is False
            assert "created successfully" in result.content[0].text or "12345" in result.content[0].text

    @pytest.mark.asyncio
    async def test_update_monitor_with_string_id(self):
        """Test that update_monitor accepts string monitor IDs and converts to int"""
        request = CallToolRequest(
            method="tools/call",
            params={
                "name": "update_monitor",
                "arguments": {
                    "monitor_id": "12345",
                    "name": "Updated Monitor",
                    "query": "avg:system.cpu{*} > 0.9",
                }
            }
        )

        with patch("datadog_mcp.tools.update_monitor.update_monitor", new_callable=AsyncMock) as mock_update:
            mock_update.return_value = {
                "id": 12345,
                "name": "Updated Monitor",
                "type": "metric alert",
                "overall_state": "ok",
            }

            result = await update_monitor.handle_call(request)

            assert result.isError is False
            assert "updated successfully" in result.content[0].text or "12345" in result.content[0].text
            # Verify monitor_id was converted to int
            call_kwargs = mock_update.call_args[1]
            assert call_kwargs["monitor_id"] == 12345

    @pytest.mark.asyncio
    async def test_update_monitor_invalid_id(self):
        """Test that update_monitor rejects non-numeric string IDs"""
        request = CallToolRequest(
            method="tools/call",
            params={
                "name": "update_monitor",
                "arguments": {
                    "monitor_id": "invalid",
                    "name": "Updated Monitor",
                }
            }
        )

        result = await update_monitor.handle_call(request)

        assert result.isError is True
        assert "valid integer" in result.content[0].text

    @pytest.mark.asyncio
    async def test_delete_monitor_with_string_id(self):
        """Test that delete_monitor accepts string monitor IDs and converts to int"""
        request = CallToolRequest(
            method="tools/call",
            params={
                "name": "delete_monitor",
                "arguments": {"monitor_id": "12345"}
            }
        )

        with patch("datadog_mcp.tools.delete_monitor.delete_monitor", new_callable=AsyncMock) as mock_delete:
            mock_delete.return_value = None

            result = await delete_monitor.handle_call(request)

            assert result.isError is False
            assert "deleted successfully" in result.content[0].text or "12345" in result.content[0].text
            # Verify monitor_id was converted to int
            mock_delete.assert_called_once_with(12345)

    @pytest.mark.asyncio
    async def test_delete_monitor_invalid_id_format(self):
        """Test that delete_monitor rejects non-numeric string IDs"""
        request = CallToolRequest(
            method="tools/call",
            params={
                "name": "delete_monitor",
                "arguments": {"monitor_id": "abc"}
            }
        )

        result = await delete_monitor.handle_call(request)

        assert result.isError is True
        assert "valid integer" in result.content[0].text

    @pytest.mark.asyncio
    async def test_delete_monitor_missing_id(self):
        """Test that delete_monitor requires monitor_id"""
        request = CallToolRequest(
            method="tools/call",
            params={
                "name": "delete_monitor",
                "arguments": {}
            }
        )

        result = await delete_monitor.handle_call(request)

        assert result.isError is True
        assert "required" in result.content[0].text


class TestParameterTypeConversion:
    """Test that parameter type conversions work correctly"""

    @pytest.mark.asyncio
    async def test_monitor_id_int_conversion(self):
        """Test various string-to-int conversions"""
        test_cases = [
            ("0", 0, True),           # Valid zero
            ("12345", 12345, True),   # Normal case
            ("999999999", 999999999, True),  # Large number
            ("abc", None, False),     # Invalid
            ("12.34", None, False),   # Float string
            ("", None, False),        # Empty string
        ]

        for string_id, expected_int, should_succeed in test_cases:
            request = CallToolRequest(
                method="tools/call",
                params={
                    "name": "get_monitor",
                    "arguments": {"monitor_id": string_id}
                }
            )

            with patch("datadog_mcp.tools.get_monitor.get_monitor", new_callable=AsyncMock) as mock_get:
                mock_get.return_value = {"id": expected_int or 0, "name": "Test"}

                result = await get_monitor.handle_call(request)

                if should_succeed:
                    assert result.isError is False, f"Expected success for {string_id}"
                else:
                    assert result.isError is True, f"Expected error for {string_id}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
