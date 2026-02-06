"""
Update monitor tool
"""

import json
import logging
from typing import Any, Dict, Optional

from mcp.types import CallToolRequest, CallToolResult, Tool, TextContent

logger = logging.getLogger(__name__)

from ..utils.datadog_client import update_monitor


def get_tool_definition() -> Tool:
    """Get the tool definition for update_monitor."""
    return Tool(
        name="update_monitor",
        description="Update an existing monitor in Datadog.",
        inputSchema={
            "type": "object",
            "properties": {
                "monitor_id": {
                    "type": "string",
                    "description": "The ID of the monitor to update",
                },
                "name": {
                    "type": "string",
                    "description": "The new name for the monitor",
                },
                "query": {
                    "type": "string",
                    "description": "The new query for the monitor",
                },
                "message": {
                    "type": "string",
                    "description": "The new message to send when the monitor alerts",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "New tags to apply to the monitor",
                },
                "thresholds": {
                    "type": "object",
                    "description": "New alert and warning thresholds as a JSON object",
                },
            },
            "additionalProperties": False,
            "required": ["monitor_id"],
        },
    )


async def handle_call(request: CallToolRequest) -> CallToolResult:
    """Handle the update_monitor tool call."""
    try:
        args = request.arguments or {}
        monitor_id = args.get("monitor_id")

        if not monitor_id:
            return CallToolResult(
                content=[TextContent(type="text", text="Error: monitor_id is required")],
                isError=True,
            )

        # Convert monitor_id to int if it's a string
        try:
            monitor_id = int(monitor_id)
        except (ValueError, TypeError):
            return CallToolResult(
                content=[TextContent(type="text", text="Error: monitor_id must be a valid integer")],
                isError=True,
            )

        # Prepare update parameters
        name = args.get("name")
        query = args.get("query")
        message = args.get("message")
        tags = args.get("tags")
        thresholds = args.get("thresholds")

        # Update monitor
        result = await update_monitor(
            monitor_id=monitor_id,
            name=name,
            query=query,
            message=message,
            tags=tags,
            thresholds=thresholds,
        )

        # Format response
        content = f"Monitor {monitor_id} updated successfully!\n\n"
        content += f"Name: {result.get('name', 'N/A')}\n"
        content += f"Type: {result.get('type', 'N/A')}\n"
        content += f"State: {result.get('overall_state', 'N/A')}\n"

        return CallToolResult(
            content=[TextContent(type="text", text=content)],
            isError=False,
        )

    except Exception as e:
        logger.error(f"Error in update_monitor: {e}")
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True,
        )
