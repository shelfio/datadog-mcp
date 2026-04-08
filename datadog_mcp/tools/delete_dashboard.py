"""
Delete dashboard tool - delete a dashboard from Datadog
"""

import json
import logging
from typing import Any, Dict

from mcp.types import CallToolRequest, CallToolResult, Tool, TextContent

logger = logging.getLogger(__name__)

from ..utils.datadog_client import delete_dashboard


def get_tool_definition() -> Tool:
    """Get the tool definition for delete_dashboard."""
    return Tool(
        name="delete_dashboard",
        description="Delete a dashboard from Datadog by its ID. This operation cannot be undone. The dashboard will be moved to the trash and can be restored from there within 30 days.",
        inputSchema={
            "type": "object",
            "properties": {
                "dashboard_id": {
                    "type": "string",
                    "description": "The ID of the dashboard to delete",
                },
            },
            "additionalProperties": False,
            "required": ["dashboard_id"],
        },
    )


async def handle_call(request: CallToolRequest) -> CallToolResult:
    """Handle the delete_dashboard tool call."""
    try:
        args = request.arguments or {}

        dashboard_id = args.get("dashboard_id")

        if not dashboard_id:
            return CallToolResult(
                content=[TextContent(type="text", text="Error: dashboard_id parameter is required")],
                isError=True,
            )

        # Delete dashboard
        result = await delete_dashboard(dashboard_id)

        # Format success response
        content = f"Dashboard deleted successfully!\n\n"
        content += f"Dashboard ID '{dashboard_id}' has been moved to trash.\n"
        content += f"It can be restored from the trash within 30 days.\n"

        return CallToolResult(
            content=[TextContent(type="text", text=content)],
            isError=False,
        )

    except Exception as e:
        error_msg = f"Error deleting dashboard: {str(e)}"
        logger.error(error_msg)
        return CallToolResult(
            content=[TextContent(type="text", text=error_msg)],
            isError=True,
        )
