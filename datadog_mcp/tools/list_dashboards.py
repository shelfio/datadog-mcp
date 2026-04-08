"""
List dashboards tool - fetch all dashboards from Datadog
"""

import json
import logging
from typing import Any, Dict

from mcp.types import CallToolRequest, CallToolResult, Tool, TextContent

logger = logging.getLogger(__name__)

from ..utils.datadog_client import fetch_dashboards


def get_tool_definition() -> Tool:
    """Get the tool definition for list_dashboards."""
    return Tool(
        name="list_dashboards",
        description="List all dashboards from Datadog. Dashboards are customizable visual interfaces that display metrics, logs, and other data.",
        inputSchema={
            "type": "object",
            "properties": {
                "filter_shared": {
                    "type": "boolean",
                    "description": "Optional filter for shared dashboards. True returns only shared dashboards, False returns only private dashboards.",
                },
                "filter_deleted": {
                    "type": "boolean",
                    "description": "Optional filter for deleted dashboards. True returns only deleted dashboards.",
                },
                "format": {
                    "type": "string",
                    "description": "Output format",
                    "enum": ["table", "json", "summary"],
                    "default": "table",
                },
            },
            "additionalProperties": False,
        },
    )


async def handle_call(request: CallToolRequest) -> CallToolResult:
    """Handle the list_dashboards tool call."""
    try:
        args = request.arguments or {}

        filter_shared = args.get("filter_shared")
        filter_deleted = args.get("filter_deleted")
        format_type = args.get("format", "table")

        # Fetch dashboards data
        data = await fetch_dashboards(
            filter_shared=filter_shared,
            filter_deleted=filter_deleted,
        )

        dashboards = data.get("dashboards", [])

        # Format output
        if format_type == "json":
            content = json.dumps(dashboards, indent=2)
        elif format_type == "summary":
            content = f"Total dashboards: {len(dashboards)}\n\n"
            # Count by type
            types = {}
            for dashboard in dashboards:
                dash_type = dashboard.get("is_read_only", False)
                type_label = "Read-only" if dash_type else "Editable"
                types[type_label] = types.get(type_label, 0) + 1

            content += "By type:\n"
            for type_label, count in types.items():
                content += f"  {type_label}: {count}\n"
        else:  # table
            if not dashboards:
                content = "No dashboards found."
            else:
                # Create table
                headers = ["ID", "Title", "Author", "Created", "Modified", "URL"]
                rows = []
                for dashboard in dashboards:
                    rows.append([
                        dashboard.get("id", "N/A"),
                        dashboard.get("title", "N/A")[:50],  # Truncate long titles
                        dashboard.get("author_handle", "N/A"),
                        dashboard.get("created_at", "N/A"),
                        dashboard.get("modified_at", "N/A"),
                        dashboard.get("url", "N/A"),
                    ])

                # Format as table
                col_widths = [max(len(str(row[i])) for row in [headers] + rows) for i in range(len(headers))]
                separator = "+" + "+".join("-" * (w + 2) for w in col_widths) + "+"

                content = separator + "\n"
                content += "| " + " | ".join(headers[i].ljust(col_widths[i]) for i in range(len(headers))) + " |\n"
                content += separator + "\n"
                for row in rows:
                    content += "| " + " | ".join(str(row[i]).ljust(col_widths[i]) for i in range(len(row))) + " |\n"
                content += separator

        return CallToolResult(
            content=[TextContent(type="text", text=content)],
            isError=False,
        )

    except Exception as e:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True,
        )
