"""
Create monitor tool
"""

import json
import logging
from typing import Any, Dict, Optional

from mcp.types import CallToolRequest, CallToolResult, Tool, TextContent

logger = logging.getLogger(__name__)

from ..utils.datadog_client import create_monitor


def get_tool_definition() -> Tool:
    """Get the tool definition for create_monitor."""
    return Tool(
        name="create_monitor",
        description="Create a new monitor in Datadog.",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The name of the monitor",
                },
                "type": {
                    "type": "string",
                    "description": "The monitor type (e.g., 'metric alert', 'log alert')",
                },
                "query": {
                    "type": "string",
                    "description": "The monitor query",
                },
                "message": {
                    "type": "string",
                    "description": "The message to send when the monitor alerts",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tags to apply to the monitor",
                },
                "thresholds": {
                    "type": "object",
                    "description": "Alert and warning thresholds as a JSON object",
                },
            },
            "additionalProperties": False,
            "required": ["name", "type", "query"],
        },
    )


async def handle_call(request: CallToolRequest) -> CallToolResult:
    """Handle the create_monitor tool call."""
    try:
        args = request.arguments or {}
        name = args.get("name")
        monitor_type = args.get("type")
        query = args.get("query")
        message = args.get("message")
        tags = args.get("tags")
        thresholds = args.get("thresholds")

        # Validate required parameters
        if not name or not monitor_type or not query:
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text="Error: name, type, and query are required",
                    )
                ],
                isError=True,
            )

        # Create monitor
        result = await create_monitor(
            name=name,
            type=monitor_type,
            query=query,
            message=message,
            tags=tags,
            thresholds=thresholds,
        )

        # Format response
        content = f"Monitor created successfully!\n\n"
        content += f"Monitor ID: {result.get('id', 'N/A')}\n"
        content += f"Name: {result.get('name', 'N/A')}\n"
        content += f"Type: {result.get('type', 'N/A')}\n"
        content += f"State: {result.get('overall_state', 'N/A')}\n"

        return CallToolResult(
            content=[TextContent(type="text", text=content)],
            isError=False,
        )

    except Exception as e:
        logger.error(f"Error in create_monitor: {e}")
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True,
        )
