"""Delete a cell from a Datadog notebook."""

from mcp.types import CallToolRequest, CallToolResult, Tool, TextContent
from ..utils.datadog_client import delete_notebook_cell as client_delete_notebook_cell


def get_tool_definition() -> Tool:
    """Return the tool definition for deleting a notebook cell."""
    return Tool(
        name="delete_notebook_cell",
        description="Delete a cell from a Datadog notebook",
        inputSchema={
            "type": "object",
            "properties": {
                "notebook_id": {
                    "type": "string",
                    "description": "The notebook ID containing the cell",
                },
                "cell_id": {
                    "type": "string",
                    "description": "The cell ID to delete",
                },
            },
            "required": ["notebook_id", "cell_id"],
        },
    )


async def handle_call(request: CallToolRequest) -> CallToolResult:
    """Handle the tool call."""
    try:
        notebook_id = request.params.arguments.get("notebook_id")
        cell_id = request.params.arguments.get("cell_id")

        result = await client_delete_notebook_cell(
            notebook_id=notebook_id,
            cell_id=cell_id,
        )

        notebook_url = f"https://app.datadoghq.com/notebook/{notebook_id}"

        formatted_result = (
            f"**Cell Deleted from Notebook**\n\n"
            f"- **Notebook ID**: {notebook_id}\n"
            f"- **Deleted Cell ID**: {cell_id}\n"
            f"- **Remaining Cells**: {len(result.get('attributes', {}).get('cells', []))}\n"
            f"- **URL**: [{notebook_url}]({notebook_url})\n"
        )

        return CallToolResult(
            content=[TextContent(type="text", text=formatted_result)],
            isError=False,
        )

    except Exception as e:
        error_text = f"Error deleting notebook cell: {str(e)}"
        return CallToolResult(
            content=[TextContent(type="text", text=error_text)],
            isError=True,
        )
