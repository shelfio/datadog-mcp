"""List notebooks tool"""

import json
import logging
from typing import Any, Dict

from mcp.types import CallToolRequest, CallToolResult, Tool, TextContent

logger = logging.getLogger(__name__)

from ..utils.datadog_client import list_notebooks as client_list_notebooks, get_cookie, get_auth_mode


def get_tool_definition() -> Tool:
    """Get the tool definition for list_notebooks."""
    return Tool(
        name="list_notebooks",
        description="List all Datadog notebooks with pagination support",
        inputSchema={
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of notebooks to return (default: 20, max: 100)",
                    "default": 20,
                    "minimum": 1,
                    "maximum": 100,
                },
                "offset": {
                    "type": "integer",
                    "description": "Offset for pagination (default: 0)",
                    "default": 0,
                    "minimum": 0,
                },
                "format": {
                    "type": "string",
                    "description": "Output format",
                    "enum": ["table", "json", "summary"],
                    "default": "table",
                },
            },
            "additionalProperties": False,
            "required": [],
        },
    )


async def handle_call(request: CallToolRequest) -> CallToolResult:
    """Handle the list_notebooks tool call."""
    try:
        args = request.params.arguments or {}

        limit = args.get("limit", 20)
        offset = args.get("offset", 0)
        format_type = args.get("format", "table")

        # Fetch notebooks list
        result = await client_list_notebooks(limit=limit, offset=offset)

        notebooks = result.get("notebooks", [])
        total_count = result.get("page_count", 0)

        # Get auth metadata for debugging/transparency
        use_cookie, api_url = get_auth_mode()
        auth_method = "Cookie (internal UI)" if use_cookie else "Token (public API)"
        api_version = "v1"
        auth_info = f"\n🔐 Auth: {auth_method} | API: {api_url}/api/{api_version}/notebooks"

        if not notebooks:
            return CallToolResult(
                content=[TextContent(type="text", text=f"No notebooks found{auth_info}")],
                isError=False,
            )

        # Format output
        if format_type == "json":
            content = json.dumps({
                "authentication": {
                    "method": auth_method,
                    "api_url": api_url,
                    "api_version": api_version,
                    "endpoint": f"/api/{api_version}/notebooks",
                },
                "notebooks": notebooks,
                "pagination": {
                    "limit": limit,
                    "offset": offset,
                    "returned": len(notebooks),
                    "total_available": total_count,
                },
            }, indent=2)
        elif format_type == "summary":
            content = f"Found {len(notebooks)} notebooks (total available: {total_count}){auth_info}"
            if limit < total_count:
                content += f"\nShowing {offset + 1}-{offset + len(notebooks)} of {total_count}"
            if limit < total_count and offset + limit < total_count:
                content += f"\nNext: offset={offset + limit}, limit={limit}"

        else:  # table format
            content = f"Datadog Notebooks{auth_info}\n"
            content += f"Showing: {len(notebooks)} notebooks (total: {total_count})\n"
            if offset > 0:
                content += f"Offset: {offset}\n"
            content += "=" * 80 + "\n\n"

            for i, notebook in enumerate(notebooks, 1):
                notebook_id = notebook.get("id", "unknown")
                notebook_name = notebook.get("attributes", {}).get("name", "Unnamed")
                notebook_desc = notebook.get("attributes", {}).get("description", "")
                notebook_author = notebook.get("attributes", {}).get("author", {}).get("name", "Unknown")
                notebook_created = notebook.get("attributes", {}).get("created", "N/A")
                notebook_cells = len(notebook.get("attributes", {}).get("cells", []))

                content += f"{i:3d}. {notebook_name}\n"
                content += f"     ID: {notebook_id} | Cells: {notebook_cells} | Author: {notebook_author}\n"
                if notebook_desc:
                    content += f"     Description: {notebook_desc[:60]}{'...' if len(notebook_desc) > 60 else ''}\n"
                content += f"     Created: {notebook_created}\n\n"

        return CallToolResult(
            content=[TextContent(type="text", text=content)],
            isError=False,
        )

    except Exception as e:
        logger.error(f"Error in list_notebooks: {e}")
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True,
        )
