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

from .tools import get_fingerprints, list_pipelines, get_logs, get_teams, get_metrics, get_metric_fields, get_metric_field_values, list_metrics, list_service_definitions, get_service_definition, list_monitors, list_slos, get_logs_field_values, get_monitor, create_monitor, update_monitor, delete_monitor, create_notebook, get_notebook, update_notebook, add_notebook_cell, update_notebook_cell, delete_notebook_cell, delete_notebook, query_metric_formula, check_deployment, get_traces, aggregate_traces
from .utils.secrets_provider import get_secret_provider, close_secret_provider, is_aws_secrets_configured

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
    "get_monitor": {
        "definition": get_monitor.get_tool_definition,
        "handler": get_monitor.handle_call,
    },
    "create_monitor": {
        "definition": create_monitor.get_tool_definition,
        "handler": create_monitor.handle_call,
    },
    "update_monitor": {
        "definition": update_monitor.get_tool_definition,
        "handler": update_monitor.handle_call,
    },
    "delete_monitor": {
        "definition": delete_monitor.get_tool_definition,
        "handler": delete_monitor.handle_call,
    },
    "list_slos": {
        "definition": list_slos.get_tool_definition,
        "handler": list_slos.handle_call,
    },
    "create_notebook": {
        "definition": create_notebook.get_tool_definition,
        "handler": create_notebook.handle_call,
    },
    "get_notebook": {
        "definition": get_notebook.get_tool_definition,
        "handler": get_notebook.handle_call,
    },
    "update_notebook": {
        "definition": update_notebook.get_tool_definition,
        "handler": update_notebook.handle_call,
    },
    "add_notebook_cell": {
        "definition": add_notebook_cell.get_tool_definition,
        "handler": add_notebook_cell.handle_call,
    },
    "update_notebook_cell": {
        "definition": update_notebook_cell.get_tool_definition,
        "handler": update_notebook_cell.handle_call,
    },
    "delete_notebook_cell": {
        "definition": delete_notebook_cell.get_tool_definition,
        "handler": delete_notebook_cell.handle_call,
    },
    "delete_notebook": {
        "definition": delete_notebook.get_tool_definition,
        "handler": delete_notebook.handle_call,
    },
    "query_metric_formula": {
        "definition": query_metric_formula.get_tool_definition,
        "handler": query_metric_formula.handle_call,
    },
    "check_deployment": {
        "definition": check_deployment.get_tool_definition,
        "handler": check_deployment.handle_call,
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

        # Initialize AWS Secrets Manager provider if configured
        # Credentials are fetched lazily on first tool call via get_auth_headers()
        if is_aws_secrets_configured():
            logger.info("AWS Secrets Manager configured (credentials will be fetched on first use)")

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
    finally:
        # Clean up AWS Secrets Manager provider
        await close_secret_provider()
        logger.info("Datadog MCP Server shutdown complete")


def cli_main():
    """Main entry point for console scripts."""
    asyncio.run(async_main())


if __name__ == "__main__":
    cli_main()