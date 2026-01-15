"""
Dashboard update title tool
"""

import logging
from typing import Any, Dict

from mcp.types import CallToolRequest, CallToolResult, Tool, TextContent

logger = logging.getLogger(__name__)

from ..utils.datadog_client import update_dashboard_title


def get_tool_definition() -> Tool:
    """Get the tool definition for dashboard_update_title."""
    return Tool(
        name="dashboard_update_title",
        description="Update the title of a Datadog dashboard. Requires the dashboard ID and new title.",
        inputSchema={
            "type": "object",
            "properties": {
                "dashboard_id": {
                    "type": "string",
                    "description": "The ID of the dashboard to update (e.g., 'giw-w7a-maj'). Can be found in the dashboard URL.",
                },
                "new_title": {
                    "type": "string",
                    "description": "The new title for the dashboard.",
                },
            },
            "additionalProperties": False,
            "required": ["dashboard_id", "new_title"],
        },
    )


async def handle_call(request: CallToolRequest) -> CallToolResult:
    """Handle the dashboard_update_title tool call."""
    try:
        args = request.arguments or {}

        dashboard_id = args.get("dashboard_id")
        new_title = args.get("new_title")

        if not dashboard_id:
            return CallToolResult(
                content=[TextContent(type="text", text="Error: dashboard_id is required")],
                isError=True,
            )

        if not new_title:
            return CallToolResult(
                content=[TextContent(type="text", text="Error: new_title is required")],
                isError=True,
            )

        # Update the dashboard title
        result = await update_dashboard_title(
            dashboard_id=dashboard_id,
            new_title=new_title,
        )

        old_title = result.get("_old_title", "unknown")
        updated_title = result.get("title", new_title)
        dashboard_url = result.get("url", f"/dashboard/{dashboard_id}")

        content = f"Dashboard Title Updated Successfully\n"
        content += "=" * 35 + "\n\n"
        content += f"Dashboard ID: {dashboard_id}\n"
        content += f"Old Title:    {old_title}\n"
        content += f"New Title:    {updated_title}\n"
        content += f"URL:          {dashboard_url}\n"

        return CallToolResult(
            content=[TextContent(type="text", text=content)],
            isError=False,
        )

    except Exception as e:
        logger.error(f"Error in dashboard_update_title: {e}")
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True,
        )
