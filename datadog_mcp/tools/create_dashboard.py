"""
Create dashboard tool - create a new dashboard in Datadog
"""

import json
import logging
from typing import Any, Dict

from mcp.types import CallToolRequest, CallToolResult, Tool, TextContent

logger = logging.getLogger(__name__)

from ..utils.datadog_client import create_dashboard


def get_tool_definition() -> Tool:
    """Get the tool definition for create_dashboard."""
    return Tool(
        name="create_dashboard",
        description="""Create a new dashboard in Datadog. Requires a JSON configuration including title, widgets, and optionally template variables.

Dashboard configuration should include:
- title: Dashboard title (required)
- description: Dashboard description
- widgets: Array of widget definitions (required)
- template_variables: Array of template variable definitions (optional)
- layout_type: 'ordered' or 'free' (required)
- is_read_only: Boolean indicating if dashboard is read-only
- notify_list: List of users to notify on changes
- reflow_type: 'auto' or 'fixed' (for ordered layouts)

Template variables support filtering dashboard queries dynamically. Each variable should have:
- name: Variable name
- prefix: Tag prefix to filter by (e.g., 'env', 'service')
- default: Default value
- available_values: Array of possible values (optional)

Example minimal dashboard:
{
  "title": "My Dashboard",
  "layout_type": "ordered",
  "widgets": [{
    "definition": {
      "type": "timeseries",
      "title": "CPU Usage",
      "requests": [{
        "q": "avg:system.cpu.user{*}",
        "display_type": "line"
      }]
    }
  }]
}""",
        inputSchema={
            "type": "object",
            "properties": {
                "dashboard_config": {
                    "type": "object",
                    "description": "The dashboard configuration as a JSON object. Must include title, layout_type, and widgets.",
                },
            },
            "additionalProperties": False,
            "required": ["dashboard_config"],
        },
    )


async def handle_call(request: CallToolRequest) -> CallToolResult:
    """Handle the create_dashboard tool call."""
    try:
        args = request.arguments or {}

        dashboard_config = args.get("dashboard_config")

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

        # Create dashboard
        result = await create_dashboard(dashboard_config)

        # Format success response
        content = f"Dashboard created successfully!\n\n"
        content += f"ID: {result.get('id', 'N/A')}\n"
        content += f"Title: {result.get('title', 'N/A')}\n"
        content += f"URL: {result.get('url', 'N/A')}\n"
        content += f"Created: {result.get('created_at', 'N/A')}\n"

        return CallToolResult(
            content=[TextContent(type="text", text=content)],
            isError=False,
        )

    except Exception as e:
        error_msg = f"Error creating dashboard: {str(e)}"
        logger.error(error_msg)
        return CallToolResult(
            content=[TextContent(type="text", text=error_msg)],
            isError=True,
        )
