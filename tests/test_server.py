"""
Tests for the core MCP server functionality
"""

import pytest
import asyncio
import os
from unittest.mock import patch, MagicMock, AsyncMock
from datadog_mcp.server import server, TOOLS, handle_list_tools, handle_call_tool
from mcp.types import Tool, TextContent


class TestServerConfiguration:
    """Test server configuration and setup"""
    
    def test_tools_registry_structure(self):
        """Test that TOOLS registry has the expected structure"""
        assert isinstance(TOOLS, dict)
        assert len(TOOLS) > 0
        
        # Check each tool has required keys
        for tool_name, tool_config in TOOLS.items():
            assert "definition" in tool_config
            assert "handler" in tool_config
            assert callable(tool_config["definition"])
            assert callable(tool_config["handler"])
    
    def test_expected_tools_are_registered(self):
        """Test that all expected tools are registered"""
        expected_tools = [
            "list_ci_pipelines",
            "get_pipeline_fingerprints",
            "get_logs",
            "get_logs_field_values",
            "get_teams",
            "get_metrics",
            "get_metric_fields",
            "get_metric_field_values",
            "list_metrics",
            "list_service_definitions",
            "get_service_definition",
            "list_monitors",
            "list_slos",
            "dashboard_update_title",
        ]

        for tool_name in expected_tools:
            assert tool_name in TOOLS, f"Tool {tool_name} not registered"


class TestToolHandling:
    """Test MCP tool handling functionality"""
    
    @pytest.mark.asyncio
    async def test_handle_list_tools(self):
        """Test that handle_list_tools returns proper Tool objects"""
        tools = await handle_list_tools()
        
        assert isinstance(tools, list)
        assert len(tools) > 0
        
        # Check each tool is a proper Tool object
        for tool in tools:
            assert isinstance(tool, Tool)
            assert hasattr(tool, 'name')
            assert hasattr(tool, 'description')
    
    @pytest.mark.asyncio
    async def test_handle_call_tool_unknown_tool(self):
        """Test handling of unknown tool calls"""
        result = await handle_call_tool("nonexistent_tool", {})
        
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Unknown tool" in result[0].text
    
    @pytest.mark.asyncio
    async def test_handle_call_tool_with_mock_handler(self):
        """Test successful tool call with mocked handler"""
        # Mock a tool handler that returns expected result
        mock_result = MagicMock()
        mock_result.content = [TextContent(type="text", text="Test result")]
        
        mock_handler = AsyncMock(return_value=mock_result)
        
        # Temporarily patch TOOLS
        original_tools = TOOLS.copy()
        TOOLS["test_tool"] = {
            "definition": lambda: Tool(name="test_tool", description="Test tool"),
            "handler": mock_handler
        }
        
        try:
            result = await handle_call_tool("test_tool", {"param": "value"})
            
            assert isinstance(result, list)
            assert len(result) == 1
            assert isinstance(result[0], TextContent)
            assert result[0].text == "Test result"
            
            # Verify handler was called with proper request structure
            mock_handler.assert_called_once()
            call_args = mock_handler.call_args[0][0]
            assert call_args.name == "test_tool"
            assert call_args.arguments == {"param": "value"}
            
        finally:
            # Restore original TOOLS
            TOOLS.clear()
            TOOLS.update(original_tools)
    
    @pytest.mark.asyncio
    async def test_handle_call_tool_exception_handling(self):
        """Test exception handling in tool calls"""
        # Mock a tool handler that raises an exception
        mock_handler = AsyncMock(side_effect=Exception("Test error"))
        
        original_tools = TOOLS.copy()
        TOOLS["error_tool"] = {
            "definition": lambda: Tool(name="error_tool", description="Error tool"),
            "handler": mock_handler
        }
        
        try:
            result = await handle_call_tool("error_tool", {})
            
            assert isinstance(result, list)
            assert len(result) == 1
            assert isinstance(result[0], TextContent)
            assert "Error: Test error" in result[0].text
            
        finally:
            TOOLS.clear()
            TOOLS.update(original_tools)


class TestServerIntegration:
    """Integration tests for server functionality"""
    
    def test_server_instance_exists(self):
        """Test that server instance is properly created"""
        assert server is not None
        assert hasattr(server, 'name')
    
    @pytest.mark.asyncio
    async def test_server_tool_integration(self):
        """Test integration between server and tool system"""
        # Test that we can list tools and they match our TOOLS registry
        tools = await handle_list_tools()
        tool_names = [tool.name for tool in tools]
        
        # Should have same number of tools as registered
        assert len(tool_names) == len(TOOLS)
        
        # All registered tools should be listed
        for registered_name in TOOLS.keys():
            # Get the actual tool name from definition
            tool_def = TOOLS[registered_name]["definition"]()
            assert tool_def.name in tool_names


class TestEnvironmentConfiguration:
    """Test environment configuration requirements"""
    
    def test_datadog_credentials_required(self):
        """Test that missing Datadog credentials are handled"""
        # Test with missing credentials
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="Datadog API credentials not configured"):
                # Re-import to trigger credential check
                import importlib
                from datadog_mcp.utils import datadog_client
                importlib.reload(datadog_client)
    
    def test_datadog_credentials_present(self):
        """Test that valid credentials don't raise errors"""
        with patch.dict(os.environ, {"DD_API_KEY": "test_key", "DD_APP_KEY": "test_app_key"}):
            # Should not raise any errors
            import importlib
            from datadog_mcp.utils import datadog_client
            importlib.reload(datadog_client)
            
            # Verify credentials are loaded
            assert datadog_client.DATADOG_API_KEY == "test_key"
            assert datadog_client.DATADOG_APP_KEY == "test_app_key"


if __name__ == "__main__":
    pytest.main([__file__])