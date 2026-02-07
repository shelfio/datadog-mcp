"""Delete a Datadog notebook."""

from mcp.types import CallToolRequest, CallToolResult, Tool, TextContent
from ..utils.datadog_client import delete_notebook as client_delete_notebook


def get_tool_definition() -> Tool:
    """Return the tool definition for deleting a notebook."""
    return Tool(
        name="delete_notebook",
        description="Delete a Datadog notebook by ID",
        inputSchema={
            "type": "object",
            "properties": {
                "notebook_id": {
                    "type": "string",
                    "description": "The notebook ID to delete (e.g., 'notebook-xyz789')",
                },
            },
            "required": ["notebook_id"],
        },
    )


async def handle_call(request: CallToolRequest) -> CallToolResult:
    """Handle the tool call."""
    try:
        notebook_id = request.params.arguments.get("notebook_id")

        await client_delete_notebook(notebook_id=notebook_id)

        formatted_result = (
            f"**Notebook Deleted**\n\n"
            f"- **ID**: {notebook_id}\n"
            f"- **Status**: Successfully deleted\n"
        )

        return CallToolResult(
            content=[TextContent(type="text", text=formatted_result)],
            isError=False,
        )

    except Exception as e:
        error_text = f"Error deleting notebook: {str(e)}"
        return CallToolResult(
            content=[TextContent(type="text", text=error_text)],
            isError=True,
        )
