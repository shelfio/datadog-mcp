"""
Delete monitor tool
"""

import logging

from mcp.types import CallToolRequest, CallToolResult, Tool, TextContent

logger = logging.getLogger(__name__)

from ..utils.datadog_client import delete_monitor


def get_tool_definition() -> Tool:
    """Get the tool definition for delete_monitor."""
    return Tool(
        name="delete_monitor",
        description="Delete a monitor from Datadog.",
        inputSchema={
            "type": "object",
            "properties": {
                "monitor_id": {
                    "type": "string",
                    "description": "The ID of the monitor to delete",
                },
            },
            "additionalProperties": False,
            "required": ["monitor_id"],
        },
    )


async def handle_call(request: CallToolRequest) -> CallToolResult:
    """Handle the delete_monitor tool call."""
    try:
        args = request.params.arguments or {}
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

        # Delete monitor
        result = await delete_monitor(monitor_id)

        # Format response
        content = f"Monitor {monitor_id} deleted successfully!"

        return CallToolResult(
            content=[TextContent(type="text", text=content)],
            isError=False,
        )

    except Exception as e:
        logger.error(f"Error in delete_monitor: {e}")
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True,
        )
