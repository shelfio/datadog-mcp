"""
Get pipeline fingerprints tool
"""

from typing import Any, Dict, List

from mcp.types import CallToolRequest, CallToolResult, Tool, TextContent

from ..utils.datadog_client import fetch_ci_pipelines
from ..utils.formatters import extract_pipeline_info, format_as_table


def get_tool_definition() -> Tool:
    """Get the tool definition for get_pipeline_fingerprints."""
    return Tool(
        name="get_pipeline_fingerprints",
        description="Get unique pipeline fingerprints for specific repositories/services",
        inputSchema={
            "type": "object",
            "properties": {
                "repositories": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of repository names to get fingerprints for",
                },
                "pipeline_name": {
                    "type": "string",
                    "description": "Filter by specific pipeline name",
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
                    "description": "Maximum number of pipeline events per repository (default: 100)",
                    "default": 100,
                    "minimum": 1,
                    "maximum": 5000,
                },
                "cursor": {
                    "type": "string",
                    "description": "Pagination cursor from previous response (for getting next page)",
                    "default": "",
                },
            },
            "additionalProperties": False,
            "required": ["repositories"],
        },
    )


async def handle_call(request: CallToolRequest) -> CallToolResult:
    """Handle the get_pipeline_fingerprints tool call."""
    try:
        args = request.params.arguments or {}
        
        repositories = args.get("repositories", [])
        pipeline_name = args.get("pipeline_name")
        days_back = args.get("days_back", 90)
        limit = args.get("limit", 100)
        cursor = args.get("cursor", "")
        
        if not repositories:
            return CallToolResult(
                content=[TextContent(type="text", text="Error: repositories parameter is required")],
                isError=True,
            )
        
        all_pipelines = []
        pagination_info = {}
        
        # Fetch pipelines for each repository
        for repo in repositories:
            response = await fetch_ci_pipelines(
                repository=repo,
                pipeline_name=pipeline_name,
                days_back=days_back,
                limit=limit,
                cursor=cursor if cursor else None,
            )
            events = response.get("data", [])
            pipelines = extract_pipeline_info(events)
            all_pipelines.extend(pipelines)
            
            # Collect pagination info from last repo (for simplicity)
            if repo == repositories[-1]:
                meta = response.get("meta", {})
                page = meta.get("page", {})
                pagination_info["next_cursor"] = page.get("after")
        
        # Remove duplicates and sort
        unique_pipelines = {}
        for pipeline in all_pipelines:
            key = pipeline["fingerprint"]
            unique_pipelines[key] = pipeline
        
        result = sorted(unique_pipelines.values(), key=lambda x: (x["repository"], x["pipeline_name"]))
        
        # Format as table
        content = format_as_table(result)
        
        # Add pagination info if available
        if pagination_info.get("next_cursor"):
            content += f"\n\nNext cursor: {pagination_info['next_cursor']}"
        
        return CallToolResult(
            content=[TextContent(type="text", text=content)],
            isError=False,
        )
        
    except Exception as e:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True,
        )