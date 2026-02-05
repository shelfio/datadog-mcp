"""
Monitor edit tool
"""

import logging

from mcp.types import CallToolRequest, CallToolResult, Tool, TextContent
import httpx

logger = logging.getLogger(__name__)

from ..utils.datadog_client import update_monitor


def get_tool_definition() -> Tool:
    """Get the tool definition for monitor_edit."""
    return Tool(
        name="monitor_edit",
        description="Update basic fields of an existing Datadog monitor. At least one update field must be provided.",
        inputSchema={
            "type": "object",
            "properties": {
                "monitor_id": {
                    "type": "integer",
                    "description": "The numeric ID of the monitor to update.",
                },
                "name": {
                    "type": "string",
                    "description": "New name for the monitor.",
                },
                "message": {
                    "type": "string",
                    "description": "New message/description for the monitor.",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "New list of tags for the monitor.",
                },
                "priority": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 5,
                    "description": "New priority level (1-5) for the monitor.",
                },
                "query": {
                    "type": "string",
                    "description": "New query for the monitor.",
                },
            },
            "additionalProperties": False,
            "required": ["monitor_id"],
        },
    )


async def handle_call(request: CallToolRequest) -> CallToolResult:
    """Handle the monitor_edit tool call."""
    try:
        args = request.arguments or {}

        monitor_id = args.get("monitor_id")

        if monitor_id is None:
            return CallToolResult(
                content=[TextContent(type="text", text="Error: monitor_id is required")],
                isError=True,
            )

        name = args.get("name")
        message = args.get("message")
        tags = args.get("tags")
        priority = args.get("priority")
        query = args.get("query")

        if priority is not None and (priority < 1 or priority > 5):
            return CallToolResult(
                content=[TextContent(type="text", text="Invalid priority: must be 1-5")],
                isError=True,
            )

        updates = {}
        if name is not None:
            updates["name"] = name
        if message is not None:
            updates["message"] = message
        if tags is not None:
            updates["tags"] = tags
        if priority is not None:
            updates["priority"] = priority
        if query is not None:
            updates["query"] = query

        if not updates:
            return CallToolResult(
                content=[TextContent(type="text", text="At least one field to update is required")],
                isError=True,
            )

        await update_monitor(monitor_id, **updates)

        return CallToolResult(
            content=[TextContent(type="text", text=f"Monitor {monitor_id} updated successfully")],
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
        logger.error(f"Error in monitor_edit: {e}")
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True,
        )
    except Exception as e:
        logger.error(f"Error in monitor_edit: {e}")
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True,
        )
