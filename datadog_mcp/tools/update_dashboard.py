"""
Update dashboard tool - update an existing dashboard in Datadog
"""

import json
import logging
from typing import Any, Dict

from mcp.types import CallToolRequest, CallToolResult, Tool, TextContent

logger = logging.getLogger(__name__)

from ..utils.datadog_client import update_dashboard


def get_tool_definition() -> Tool:
    """Get the tool definition for update_dashboard."""
    return Tool(
        name="update_dashboard",
        description="""Update an existing dashboard in Datadog. Requires the dashboard ID and a complete JSON configuration.

Note: This is a full replacement operation - you must provide the complete dashboard configuration including all widgets and settings you want to keep.

Dashboard configuration should include:
- title: Dashboard title (required)
- description: Dashboard description
- widgets: Array of widget definitions (required)
- template_variables: Array of template variable definitions (optional)
- layout_type: 'ordered' or 'free' (required)
- is_read_only: Boolean indicating if dashboard is read-only
- notify_list: List of users to notify on changes
- reflow_type: 'auto' or 'fixed' (for ordered layouts)

To update a dashboard while preserving existing content, first use get_dashboard to retrieve the current configuration, modify it, then use this tool.""",
        inputSchema={
            "type": "object",
            "properties": {
                "dashboard_id": {
                    "type": "string",
                    "description": "The ID of the dashboard to update",
                },
                "dashboard_config": {
                    "type": "object",
                    "description": "The complete dashboard configuration as a JSON object. Must include title, layout_type, and widgets.",
                },
            },
            "additionalProperties": False,
            "required": ["dashboard_id", "dashboard_config"],
        },
    )


async def handle_call(request: CallToolRequest) -> CallToolResult:
    """Handle the update_dashboard tool call."""
    try:
        args = request.arguments or {}

        dashboard_id = args.get("dashboard_id")
        dashboard_config = args.get("dashboard_config")

        if not dashboard_id:
            return CallToolResult(
                content=[TextContent(type="text", text="Error: dashboard_id parameter is required")],
                isError=True,
            )

        if not dashboard_config:
            return CallToolResult(
                content=[TextContent(type="text", text="Error: dashboard_config parameter is required")],
                isError=True,
            )

        # Validate required fields
        if "title" not in dashboard_config:
            return CallToolResult(
                content=[TextContent(type="text", text="Error: dashboard_config must include 'title'")],
                isError=True,
            )

        if "layout_type" not in dashboard_config:
            return CallToolResult(
                content=[TextContent(type="text", text="Error: dashboard_config must include 'layout_type' ('ordered' or 'free')")],
                isError=True,
            )

        if "widgets" not in dashboard_config:
            return CallToolResult(
                content=[TextContent(type="text", text="Error: dashboard_config must include 'widgets' array")],
                isError=True,
            )

        # Update dashboard
        result = await update_dashboard(dashboard_id, dashboard_config)

        # Format success response
        content = f"Dashboard updated successfully!\n\n"
        content += f"ID: {result.get('id', 'N/A')}\n"
        content += f"Title: {result.get('title', 'N/A')}\n"
        content += f"URL: {result.get('url', 'N/A')}\n"
        content += f"Modified: {result.get('modified_at', 'N/A')}\n"

        return CallToolResult(
            content=[TextContent(type="text", text=content)],
            isError=False,
        )

    except Exception as e:
        error_msg = f"Error updating dashboard: {str(e)}"
        logger.error(error_msg)
        return CallToolResult(
            content=[TextContent(type="text", text=error_msg)],
            isError=True,
        )
