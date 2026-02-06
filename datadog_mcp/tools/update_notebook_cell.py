"""Update a cell in a Datadog notebook."""

from mcp.types import Tool, TextContent
from ..utils.datadog_client import update_notebook_cell as client_update_notebook_cell


def get_tool_definition() -> Tool:
    """Return the tool definition for updating a notebook cell."""
    return Tool(
        name="update_notebook_cell",
        description="Update an existing cell in a Datadog notebook",
        inputSchema={
            "type": "object",
            "properties": {
                "notebook_id": {
                    "type": "string",
                    "description": "The notebook ID containing the cell",
                },
                "cell_id": {
                    "type": "string",
                    "description": "The cell ID to update",
                },
                "title": {
                    "type": "string",
                    "description": "New title for the cell",
                },
                "query": {
                    "type": "string",
                    "description": "New query for metric/log/APM cells",
                },
                "content": {
                    "type": "string",
                    "description": "New content for markdown cells",
                },
                "visualization": {
                    "type": "string",
                    "enum": ["line_chart", "bar", "table"],
                    "description": "New visualization type for timeseries cells",
                },
                "position": {
                    "type": "integer",
                    "description": "New position in the notebook",
                },
            },
            "required": ["notebook_id", "cell_id"],
        },
    )


async def handle_call(request):
    """Handle the tool call."""
    try:
        notebook_id = request.arguments.get("notebook_id")
        cell_id = request.arguments.get("cell_id")
        title = request.arguments.get("title")
        query = request.arguments.get("query")
        content = request.arguments.get("content")
        visualization = request.arguments.get("visualization")
        position = request.arguments.get("position")

        result = await client_update_notebook_cell(
            notebook_id=notebook_id,
            cell_id=cell_id,
            title=title,
            query=query,
            content=content,
            visualization=visualization,
            position=position,
        )

        notebook_url = f"https://app.datadoghq.com/notebook/{notebook_id}"

        formatted_result = (
            f"**Notebook Cell Updated**\n\n"
            f"- **Notebook ID**: {notebook_id}\n"
            f"- **Cell ID**: {cell_id}\n"
            f"- **Cell Title**: {title or 'N/A'}\n"
            f"- **Total Cells**: {len(result.get('attributes', {}).get('cells', []))}\n"
            f"- **URL**: [{notebook_url}]({notebook_url})\n"
        )

        return [TextContent(type="text", text=formatted_result)]

    except Exception as e:
        error_text = f"Error updating notebook cell: {str(e)}"
        return [TextContent(type="text", text=error_text)]
