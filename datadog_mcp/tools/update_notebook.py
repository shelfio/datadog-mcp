"""Update a Datadog notebook."""

from mcp.types import Tool, TextContent
from ..utils.datadog_client import update_notebook as client_update_notebook


def get_tool_definition() -> Tool:
    """Return the tool definition for updating a notebook."""
    return Tool(
        name="update_notebook",
        description="Update an existing Datadog notebook's metadata (title, description, tags)",
        inputSchema={
            "type": "object",
            "properties": {
                "notebook_id": {
                    "type": "string",
                    "description": "The notebook ID to update (e.g., 'notebook-xyz789')",
                },
                "title": {
                    "type": "string",
                    "description": "New title for the notebook",
                },
                "description": {
                    "type": "string",
                    "description": "New description for the notebook",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "New tags for the notebook",
                },
            },
            "required": ["notebook_id"],
        },
    )


async def handle_call(request):
    """Handle the tool call."""
    try:
        notebook_id = request.arguments.get("notebook_id")
        title = request.arguments.get("title")
        description = request.arguments.get("description")
        tags = request.arguments.get("tags")

        result = await client_update_notebook(
            notebook_id=notebook_id,
            title=title,
            description=description,
            tags=tags,
        )

        notebook_url = f"https://app.datadoghq.com/notebook/{notebook_id}"

        formatted_result = (
            f"**Notebook Updated**\n\n"
            f"- **ID**: {result.get('id')}\n"
            f"- **Title**: {result.get('attributes', {}).get('name', 'N/A')}\n"
            f"- **Description**: {result.get('attributes', {}).get('description', 'N/A')}\n"
            f"- **Tags**: {', '.join(result.get('attributes', {}).get('tags', []))}\n"
            f"- **URL**: [{notebook_url}]({notebook_url})\n"
        )

        return [TextContent(type="text", text=formatted_result)]

    except Exception as e:
        error_text = f"Error updating notebook: {str(e)}"
        return [TextContent(type="text", text=error_text)]
