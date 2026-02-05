"""
Get monitor tool
"""

import json
import logging

from mcp.types import CallToolRequest, CallToolResult, Tool, TextContent
import httpx

logger = logging.getLogger(__name__)

from ..utils.datadog_client import fetch_monitor


def get_tool_definition() -> Tool:
    """Get the tool definition for get_monitor."""
    return Tool(
        name="get_monitor",
        description="Get details for a specific Datadog monitor by ID.",
        inputSchema={
            "type": "object",
            "properties": {
                "monitor_id": {
                    "type": "integer",
                    "description": "The numeric ID of the monitor to fetch.",
                },
                "format": {
                    "type": "string",
                    "description": "Output format",
                    "enum": ["table", "json"],
                    "default": "table",
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
        format_type = args.get("format", "table")

        if monitor_id is None:
            return CallToolResult(
                content=[TextContent(type="text", text="Error: monitor_id is required")],
                isError=True,
            )

        monitor = await fetch_monitor(monitor_id)

        if format_type == "json":
            content = json.dumps(monitor, indent=2)
        else:
            monitor_name = monitor.get("name", "Unnamed")
            monitor_type = monitor.get("type", "unknown")
            overall_state = monitor.get("overall_state", "unknown")
            priority = monitor.get("priority", "N/A")
            query = monitor.get("query", "N/A")
            message = monitor.get("message", "")

            tags = monitor.get("tags", [])
            tags_str = ", ".join(tags[:5])
            if len(tags) > 5:
                tags_str += f" (+{len(tags) - 5} more)"

            message_truncated = message[:100] + "..." if len(message) > 100 else message
            message_truncated = message_truncated.replace("\n", " ")

            content = f"Monitor Details\n"
            content += "=" * 15 + "\n\n"
            content += f"ID:       {monitor_id}\n"
            content += f"Name:     {monitor_name}\n"
            content += f"Type:     {monitor_type}\n"
            content += f"State:    {overall_state}\n"
            content += f"Priority: {priority}\n"
            content += f"Tags:     {tags_str if tags_str else 'None'}\n"
            content += f"Query:    {query}\n"
            content += f"Message:  {message_truncated if message_truncated else 'None'}\n"

        return CallToolResult(
            content=[TextContent(type="text", text=content)],
            isError=False,
        )

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return CallToolResult(
                content=[TextContent(type="text", text="Monitor not found")],
                isError=True,
            )
        elif e.response.status_code == 403:
            return CallToolResult(
                content=[TextContent(type="text", text="Permission denied")],
                isError=True,
            )
        logger.error(f"Error in get_monitor: {e}")
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True,
        )
    except Exception as e:
        logger.error(f"Error in get_monitor: {e}")
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True,
        )
