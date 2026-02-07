"""Create a Datadog notebook."""

from mcp.types import CallToolRequest, CallToolResult, Tool, TextContent
from ..utils.datadog_client import create_notebook as client_create_notebook


def get_tool_definition() -> Tool:
    """Return the tool definition for creating a notebook."""
    return Tool(
        name="create_notebook",
        description="Create a new Datadog notebook for organizing analysis, investigation, or RCA documentation",
        inputSchema={
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Title of the notebook (e.g., 'Gun Detection RCA - 2026-02-05')",
                },
                "description": {
                    "type": "string",
                    "description": "Optional description of the notebook's purpose",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional tags for organizing notebooks (e.g., ['rca:gun_detection', 'incident:p0'])",
                },
                "cells": {
                    "type": "array",
                    "description": "Optional initial cells. Each cell is an object with type and content",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {
                                "type": "string",
                                "enum": ["markdown", "timeseries", "log_stream", "trace_list", "query_value"],
                                "description": "Type of cell",
                            },
                            "title": {
                                "type": "string",
                                "description": "Title for the cell (for metric/log cells)",
                            },
                            "query": {
                                "type": "string",
                                "description": "Query for metric/log/APM cells",
                            },
                            "content": {
                                "type": "string",
                                "description": "Content for markdown cells",
                            },
                            "visualization": {
                                "type": "string",
                                "enum": ["line_chart", "bar", "table"],
                                "description": "Visualization type for timeseries cells",
                            },
                        },
                    },
                },
            },
            "required": ["title"],
        },
    )


async def handle_call(request: CallToolRequest) -> CallToolResult:
    """Handle the tool call."""
    try:
        title = request.params.arguments.get("title")
        description = request.params.arguments.get("description")
        tags = request.params.arguments.get("tags")
        cells = request.params.arguments.get("cells")

        result = await client_create_notebook(
            title=title,
            description=description,
            tags=tags,
            cells=cells,
        )

        notebook_id = result.get("id")
        notebook_url = f"https://app.datadoghq.com/notebook/{notebook_id}" if notebook_id else ""

        formatted_result = (
            f"**Notebook Created**\n\n"
            f"- **ID**: {notebook_id}\n"
            f"- **Title**: {result.get('attributes', {}).get('name', 'N/A')}\n"
            f"- **Description**: {result.get('attributes', {}).get('description', 'N/A')}\n"
            f"- **Tags**: {', '.join(result.get('attributes', {}).get('tags', []))}\n"
            f"- **Cells**: {len(result.get('attributes', {}).get('cells', []))}\n"
            f"- **URL**: [{notebook_url}]({notebook_url})\n"
        )

        return CallToolResult(
            content=[TextContent(type="text", text=formatted_result)],
            isError=False,
        )

    except Exception as e:
        import traceback
        error_text = f"Error creating notebook: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"
        return CallToolResult(
            content=[TextContent(type="text", text=error_text)],
            isError=True,
        )
