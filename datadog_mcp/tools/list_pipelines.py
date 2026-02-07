"""
List CI pipelines tool
"""

import json
from typing import Any, Dict

from mcp.types import CallToolRequest, CallToolResult, Tool, TextContent

from ..utils.datadog_client import fetch_ci_pipelines
from ..utils.formatters import extract_pipeline_info, format_as_table


def get_tool_definition() -> Tool:
    """Get the tool definition for list_ci_pipelines."""
    return Tool(
        name="list_ci_pipelines",
        description="List CI pipelines from Datadog CI Visibility with optional filtering",
        inputSchema={
            "type": "object",
            "properties": {
                "repository": {
                    "type": "string",
                    "description": "Filter by repository name (e.g., 'shelfio/shelf-api-content')",
                },
                "pipeline_name": {
                    "type": "string",
                    "description": "Filter by pipeline name (e.g., 'build_deploy', 'run-sast-tooling')",
                },
                "days_back": {
                    "type": "integer",
                    "description": "Number of days to look back (default: 90)",
                    "default": 90,
                    "minimum": 1,
                    "maximum": 365,
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results (default: 100)",
                    "default": 100,
                    "minimum": 1,
                    "maximum": 5000,
                },
                "cursor": {
                    "type": "string",
                    "description": "Pagination cursor from previous response (for getting next page)",
                    "default": "",
                },
                "format": {
                    "type": "string",
                    "description": "Output format",
                    "enum": ["table", "json"],
                    "default": "table",
                },
            },
            "additionalProperties": False,
        },
    )


async def handle_call(request: CallToolRequest) -> CallToolResult:
    """Handle the list_ci_pipelines tool call."""
    try:
        args = request.params.arguments or {}
        
        repository = args.get("repository")
        pipeline_name = args.get("pipeline_name")
        days_back = args.get("days_back", 90)
        limit = args.get("limit", 100)
        cursor = args.get("cursor", "")
        format_type = args.get("format", "table")
        
        # Fetch pipeline events
        response = await fetch_ci_pipelines(
            repository=repository,
            pipeline_name=pipeline_name,
            days_back=days_back,
            limit=limit,
            cursor=cursor if cursor else None,
        )
        
        events = response.get("data", [])
        
        # Extract unique pipeline info
        pipelines = extract_pipeline_info(events)
        
        # Get pagination info
        meta = response.get("meta", {})
        page = meta.get("page", {})
        next_cursor = page.get("after")
        
        # Format output
        if format_type == "json":
            # Include pagination info in JSON response
            output = {
                "pipelines": pipelines,
                "pagination": {
                    "next_cursor": next_cursor,
                    "has_more": bool(next_cursor)
                }
            }
            content = json.dumps(output, indent=2)
        else:
            content = format_as_table(pipelines)
            if next_cursor:
                content += f"\n\nNext cursor: {next_cursor}"
        
        return CallToolResult(
            content=[TextContent(type="text", text=content)],
            isError=False,
        )
        
    except Exception as e:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True,
        )