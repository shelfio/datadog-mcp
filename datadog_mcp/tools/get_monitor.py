"""
Get monitor tool
"""

import json
import logging
from typing import Any, Dict

from mcp.types import CallToolRequest, CallToolResult, Tool, TextContent

logger = logging.getLogger(__name__)

from ..utils.datadog_client import get_monitor


def get_tool_definition() -> Tool:
    """Get the tool definition for get_monitor."""
    return Tool(
        name="get_monitor",
        description="Get details for a specific monitor by ID from Datadog.",
        inputSchema={
            "type": "object",
            "properties": {
                "monitor_id": {
                    "type": "integer",
                    "description": "The ID of the monitor to retrieve",
                },
                "format": {
                    "type": "string",
                    "description": "Output format",
                    "enum": ["json", "formatted"],
                    "default": "formatted",
                },
            },
            "additionalProperties": False,
            "required": ["monitor_id"],
        },
    )


async def handle_call(request: CallToolRequest) -> CallToolResult:
    """Handle the get_monitor tool call."""
    try:
        args = request.arguments or {}
        monitor_id = args.get("monitor_id")
        format_type = args.get("format", "formatted")

        if not monitor_id:
            return CallToolResult(
                content=[TextContent(type="text", text="Error: monitor_id is required")],
                isError=True,
            )

        # Fetch monitor details
        monitor = await get_monitor(monitor_id)

        # Format output
        if format_type == "json":
            content = json.dumps(monitor, indent=2)
        else:  # formatted
            content = f"Monitor ID: {monitor.get('id', 'N/A')}\n"
            content += f"Name: {monitor.get('name', 'N/A')}\n"
            content += f"Type: {monitor.get('type', 'N/A')}\n"
            content += f"State: {monitor.get('overall_state', 'N/A')}\n"

            if monitor.get("message"):
                content += f"\nMessage: {monitor.get('message')}\n"

            if monitor.get("tags"):
                content += f"\nTags: {', '.join(monitor.get('tags', []))}\n"

            if monitor.get("query"):
                content += f"\nQuery: {monitor.get('query')}\n"

            if monitor.get("thresholds"):
                content += f"\nThresholds: {json.dumps(monitor.get('thresholds'), indent=2)}\n"

            if monitor.get("options"):
                content += f"\nOptions: {json.dumps(monitor.get('options'), indent=2)}\n"

        return CallToolResult(
            content=[TextContent(type="text", text=content)],
            isError=False,
        )

    except Exception as e:
        logger.error(f"Error in get_monitor: {e}")
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True,
        )
