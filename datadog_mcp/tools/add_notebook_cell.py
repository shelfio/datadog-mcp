"""Add a cell to a Datadog notebook."""

from mcp.types import Tool, TextContent
from ..utils.datadog_client import add_notebook_cell as client_add_notebook_cell


def get_tool_definition() -> Tool:
    """Return the tool definition for adding a notebook cell."""
    return Tool(
        name="add_notebook_cell",
        description="Add a new cell to a Datadog notebook",
        inputSchema={
            "type": "object",
            "properties": {
                "notebook_id": {
                    "type": "string",
                    "description": "The notebook ID to add a cell to",
                },
                "cell_type": {
                    "type": "string",
                    "enum": ["markdown", "timeseries", "log_stream", "trace_list", "query_value"],
                    "description": "Type of cell to add",
                },
                "position": {
                    "type": "integer",
                    "description": "Position in the notebook where the cell should be inserted (0 = beginning)",
                },
                "title": {
                    "type": "string",
                    "description": "Title for the cell (required for metric/log cells)",
                },
                "query": {
                    "type": "string",
                    "description": "Query for metric/log/APM cells (e.g., 'avg:system.cpu{host:*}')",
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
            "required": ["notebook_id", "cell_type", "position"],
        },
    )


async def handle_call(request):
    """Handle the tool call."""
    try:
        notebook_id = request.arguments.get("notebook_id")
        cell_type = request.arguments.get("cell_type")
        position = request.arguments.get("position")
        title = request.arguments.get("title")
        query = request.arguments.get("query")
        content = request.arguments.get("content")
        visualization = request.arguments.get("visualization")

        result = await client_add_notebook_cell(
            notebook_id=notebook_id,
            cell_type=cell_type,
            position=position,
            title=title,
            query=query,
            content=content,
            visualization=visualization,
        )

        notebook_url = f"https://app.datadoghq.com/notebook/{notebook_id}"

        formatted_result = (
            f"**Cell Added to Notebook**\n\n"
            f"- **Notebook ID**: {notebook_id}\n"
            f"- **Cell Type**: {cell_type}\n"
            f"- **Position**: {position}\n"
            f"- **Cell Title**: {title or 'N/A'}\n"
            f"- **Total Cells**: {len(result.get('attributes', {}).get('cells', []))}\n"
            f"- **URL**: [{notebook_url}]({notebook_url})\n"
        )

        return [TextContent(type="text", text=formatted_result)]

    except Exception as e:
        error_text = f"Error adding cell to notebook: {str(e)}"
        return [TextContent(type="text", text=error_text)]
