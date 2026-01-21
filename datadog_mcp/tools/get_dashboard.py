"""
Get dashboard tool - retrieve a specific dashboard from Datadog
"""

import json
import logging
from typing import Any, Dict

from mcp.types import CallToolRequest, CallToolResult, Tool, TextContent

logger = logging.getLogger(__name__)

from ..utils.datadog_client import fetch_dashboard


def get_tool_definition() -> Tool:
    """Get the tool definition for get_dashboard."""
    return Tool(
        name="get_dashboard",
        description="Retrieve a specific dashboard from Datadog by its ID. Returns the full dashboard configuration including widgets, template variables, and layout.",
        inputSchema={
            "type": "object",
            "properties": {
                "dashboard_id": {
                    "type": "string",
                    "description": "The ID of the dashboard to retrieve",
                },
                "format": {
                    "type": "string",
                    "description": "Output format",
                    "enum": ["json", "formatted", "summary"],
                    "default": "formatted",
                },
            },
            "additionalProperties": False,
            "required": ["dashboard_id"],
        },
    )


async def handle_call(request: CallToolRequest) -> CallToolResult:
    """Handle the get_dashboard tool call."""
    try:
        args = request.arguments or {}

        dashboard_id = args.get("dashboard_id")
        format_type = args.get("format", "formatted")

        if not dashboard_id:
            return CallToolResult(
                content=[TextContent(type="text", text="Error: dashboard_id parameter is required")],
                isError=True,
            )

        # Fetch dashboard data
        dashboard = await fetch_dashboard(dashboard_id)

        # Format output
        if format_type == "json":
            content = json.dumps(dashboard, indent=2)
        elif format_type == "summary":
            content = f"Dashboard: {dashboard.get('title', 'N/A')}\n"
            content += f"ID: {dashboard.get('id', 'N/A')}\n"
            content += f"Description: {dashboard.get('description', 'N/A')}\n"
            content += f"Author: {dashboard.get('author_handle', 'N/A')}\n"
            content += f"Created: {dashboard.get('created_at', 'N/A')}\n"
            content += f"Modified: {dashboard.get('modified_at', 'N/A')}\n"
            content += f"URL: {dashboard.get('url', 'N/A')}\n"
            content += f"Layout Type: {dashboard.get('layout_type', 'N/A')}\n"
            content += f"Is Read-Only: {dashboard.get('is_read_only', False)}\n"

            # Template variables
            template_variables = dashboard.get("template_variables", [])
            if template_variables:
                content += f"\nTemplate Variables ({len(template_variables)}):\n"
                for var in template_variables:
                    content += f"  - {var.get('name', 'N/A')}: {var.get('prefix', 'N/A')} (default: {var.get('default', 'N/A')})\n"

            # Widgets
            widgets = dashboard.get("widgets", [])
            content += f"\nWidgets ({len(widgets)}):\n"
            for i, widget in enumerate(widgets, 1):
                definition = widget.get("definition", {})
                widget_type = definition.get("type", "N/A")
                title = definition.get("title", "N/A")
                content += f"  {i}. {widget_type}: {title}\n"
        else:  # formatted
            content = "=" * 80 + "\n"
            content += f"Dashboard: {dashboard.get('title', 'N/A')}\n"
            content += "=" * 80 + "\n\n"

            content += f"ID: {dashboard.get('id', 'N/A')}\n"
            content += f"Description: {dashboard.get('description', 'N/A')}\n"
            content += f"Author: {dashboard.get('author_handle', 'N/A')}\n"
            content += f"Created: {dashboard.get('created_at', 'N/A')}\n"
            content += f"Modified: {dashboard.get('modified_at', 'N/A')}\n"
            content += f"URL: {dashboard.get('url', 'N/A')}\n"
            content += f"Layout Type: {dashboard.get('layout_type', 'N/A')}\n"
            content += f"Is Read-Only: {dashboard.get('is_read_only', False)}\n"

            # Template variables
            template_variables = dashboard.get("template_variables", [])
            if template_variables:
                content += "\n" + "-" * 80 + "\n"
                content += f"Template Variables ({len(template_variables)}):\n"
                content += "-" * 80 + "\n"
                for var in template_variables:
                    content += f"\nName: {var.get('name', 'N/A')}\n"
                    content += f"  Prefix: {var.get('prefix', 'N/A')}\n"
                    content += f"  Default: {var.get('default', 'N/A')}\n"
                    if var.get('available_values'):
                        content += f"  Available Values: {', '.join(var['available_values'])}\n"

            # Widgets
            widgets = dashboard.get("widgets", [])
            content += "\n" + "-" * 80 + "\n"
            content += f"Widgets ({len(widgets)}):\n"
            content += "-" * 80 + "\n"
            for i, widget in enumerate(widgets, 1):
                definition = widget.get("definition", {})
                widget_type = definition.get("type", "N/A")
                title = definition.get("title", "N/A")
                content += f"\n{i}. Type: {widget_type}\n"
                content += f"   Title: {title}\n"
                if "requests" in definition:
                    content += f"   Requests: {len(definition['requests'])}\n"

        return CallToolResult(
            content=[TextContent(type="text", text=content)],
            isError=False,
        )

    except Exception as e:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True,
        )
