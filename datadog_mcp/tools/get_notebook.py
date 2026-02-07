"""Get a Datadog notebook by ID."""

from mcp.types import CallToolRequest, CallToolResult, Tool, TextContent
from ..utils.datadog_client import get_notebook as client_get_notebook


def get_tool_definition() -> Tool:
    """Return the tool definition for getting a notebook."""
    return Tool(
        name="get_notebook",
        description="Retrieve a specific notebook by ID, including all cells and metadata",
        inputSchema={
            "type": "object",
            "properties": {
                "notebook_id": {
                    "type": "string",
                    "description": "The notebook ID (e.g., 'notebook-xyz789')",
                },
            },
            "required": ["notebook_id"],
        },
    )


async def handle_call(request: CallToolRequest) -> CallToolResult:
    """Handle the tool call."""
    try:
        notebook_id = request.params.arguments.get("notebook_id")

        result = await client_get_notebook(notebook_id)

        notebook_url = f"https://app.datadoghq.com/notebook/{notebook_id}"

        # Format cells
        cells_text = ""
        if "attributes" in result and "cells" in result["attributes"]:
            for i, cell in enumerate(result["attributes"]["cells"], 1):
                cell_id = cell.get("id", f"cell-{i}")
                cell_type = cell.get("type", "unknown")
                cell_title = cell.get("title", "Untitled")
                cells_text += f"\n{i}. **[{cell_type}]** {cell_title} (ID: {cell_id})"

        formatted_result = (
            f"**Notebook Details**\n\n"
            f"- **ID**: {result.get('id')}\n"
            f"- **Title**: {result.get('attributes', {}).get('name', 'N/A')}\n"
            f"- **Description**: {result.get('attributes', {}).get('description', 'N/A')}\n"
            f"- **Tags**: {', '.join(result.get('attributes', {}).get('tags', []))}\n"
            f"- **Author**: {result.get('attributes', {}).get('author', 'N/A')}\n"
            f"- **Created**: {result.get('attributes', {}).get('created', 'N/A')}\n"
            f"- **Updated**: {result.get('attributes', {}).get('updated', 'N/A')}\n"
            f"- **Cells**: {len(result.get('attributes', {}).get('cells', []))}{cells_text}\n"
            f"- **URL**: [{notebook_url}]({notebook_url})\n"
        )

        return CallToolResult(
            content=[TextContent(type="text", text=formatted_result)],
            isError=False,
        )

    except Exception as e:
        error_text = f"Error fetching notebook: {str(e)}"
        return CallToolResult(
            content=[TextContent(type="text", text=error_text)],
            isError=True,
        )
