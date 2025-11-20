#!/usr/bin/env python3
"""
Datadog CI Visibility MCP Server

Provides tools to query Datadog CI pipelines with filtering capabilities.
"""

import asyncio
import logging
from typing import List

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import Tool, ServerCapabilities, TextContent

from .tools import get_fingerprints, list_pipelines, get_logs, get_teams, get_metrics, get_metric_fields, get_metric_field_values, list_metrics, list_service_definitions, get_service_definition, list_monitors, list_slos, get_logs_field_values, get_traces, aggregate_traces

# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True
)
logger = logging.getLogger("datadog-mcp-server")

# Create MCP server instance
server = Server("datadog-mcp-server")

# Tool registry
TOOLS = {
    "list_ci_pipelines": {
        "definition": list_pipelines.get_tool_definition,
        "handler": list_pipelines.handle_call,
    },
    "get_pipeline_fingerprints": {
        "definition": get_fingerprints.get_tool_definition,
        "handler": get_fingerprints.handle_call,
    },
    "get_logs": {
        "definition": get_logs.get_tool_definition,
        "handler": get_logs.handle_call,
    },
    "get_logs_field_values": {
        "definition": get_logs_field_values.get_tool_definition,
        "handler": get_logs_field_values.handle_call,
    },
    "get_teams": {
        "definition": get_teams.get_tool_definition,
        "handler": get_teams.handle_call,
    },
    "get_metrics": {
        "definition": get_metrics.get_tool_definition,
        "handler": get_metrics.handle_call,
    },
    "get_metric_fields": {
        "definition": get_metric_fields.get_tool_definition,
        "handler": get_metric_fields.handle_call,
    },
    "get_metric_field_values": {
        "definition": get_metric_field_values.get_tool_definition,
        "handler": get_metric_field_values.handle_call,
    },
    "list_metrics": {
        "definition": list_metrics.get_tool_definition,
        "handler": list_metrics.handle_call,
    },
    "list_service_definitions": {
        "definition": list_service_definitions.get_tool_definition,
        "handler": list_service_definitions.handle_call,
    },
    "get_service_definition": {
        "definition": get_service_definition.get_tool_definition,
        "handler": get_service_definition.handle_call,
    },
    "list_monitors": {
        "definition": list_monitors.get_tool_definition,
        "handler": list_monitors.handle_call,
    },
    "list_slos": {
        "definition": list_slos.get_tool_definition,
        "handler": list_slos.handle_call,
    },
    "get_traces": {
        "definition": get_traces.get_tool_definition,
        "handler": get_traces.handle_call,
    },
    "aggregate_traces": {
        "definition": aggregate_traces.get_tool_definition,
        "handler": aggregate_traces.handle_call,
    },
}


@server.list_tools()
async def handle_list_tools() -> List[Tool]:
    """List available tools."""
    return [tool_config["definition"]() for tool_config in TOOLS.values()]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict):
    """Handle tool calls."""
    try:
        if name in TOOLS:
            # Create mock request for compatibility with existing tools
            class MockRequest:
                def __init__(self, name, arguments):
                    self.name = name
                    self.arguments = arguments
            
            handler = TOOLS[name]["handler"]
            request = MockRequest(name, arguments)
            result = await handler(request)
            
            # Extract content from CallToolResult and return as list
            if hasattr(result, 'content'):
                return result.content
            else:
                return [TextContent(type="text", text="Unexpected response format")]
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
    except Exception as e:
        logger.error(f"Error handling tool call: {e}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def async_main():
    """Async main entry point."""
    try:
        logger.info("Starting Datadog MCP Server...")
        # Run the server using stdio transport
        async with stdio_server() as (read_stream, write_stream):
            logger.info("Server transport initialized")
            await server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="datadog-mcp-server",
                    server_version="1.0.0",
                    capabilities=ServerCapabilities(
                        tools={}
                    ),
                ),
            )
    except Exception as e:
        logger.error(f"Server startup failed: {e}")
        raise


def cli_main():
    """Main entry point for console scripts."""
    asyncio.run(async_main())


if __name__ == "__main__":
    cli_main()