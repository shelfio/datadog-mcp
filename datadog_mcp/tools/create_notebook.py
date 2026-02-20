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

        result = await client_create_notebook(
            title=title,
            description=description,
            tags=tags,
        )

        notebook_id = result.get("id")
        notebook_url = f"https://app.datadoghq.com/notebook/{notebook_id}" if notebook_id else ""

        attrs = result.get('attributes', {})
        tags = attrs.get('tags') or []

        formatted_result = (
            f"**Notebook Created**\n\n"
            f"- **ID**: {notebook_id}\n"
            f"- **Title**: {attrs.get('name', 'N/A')}\n"
            f"- **Description**: {attrs.get('description', 'N/A')}\n"
            f"- **Tags**: {', '.join(tags) if tags else 'None'}\n"
            f"- **URL**: [{notebook_url}]({notebook_url})\n\n"
            f"**To add cells**, use `add_notebook_cell` with notebook ID: `{notebook_id}`"
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
