"""
Get service logs tool
"""

import json
import logging
from typing import Any, Dict

from mcp.types import CallToolRequest, CallToolResult, Tool, TextContent

logger = logging.getLogger(__name__)

from ..utils.datadog_client import fetch_logs
from ..utils.formatters import extract_log_info, format_logs_as_table, format_logs_as_text


def get_tool_definition() -> Tool:
    """Get the tool definition for get_logs."""
    return Tool(
        name="get_logs",
        description="Search and retrieve logs from Datadog with flexible filtering parameters. Similar to get_metrics but for log data.",
        inputSchema={
            "type": "object",
            "properties": {
                "time_range": {
                    "type": "string",
                    "description": "Time range to look back",
                    "enum": ["1h", "4h", "8h", "1d", "7d", "14d", "30d"],
                    "default": "1h",
                },
                "filters": {
                    "type": "object",
                    "description": "Filters to apply to the log search (e.g., {'service': 'web', 'env': 'prod', 'status': 'error', 'host': 'web-01'})",
                    "additionalProperties": {"type": "string"},
                    "default": {},
                },
                "query": {
                    "type": "string",
                    "description": "Free-text search query (e.g., 'error OR exception', 'timeout', 'user_id:12345')",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of log entries (default: 50)",
                    "default": 50,
                    "minimum": 1,
                    "maximum": 1000,
                },
                "cursor": {
                    "type": "string",
                    "description": "Pagination cursor from previous response (for getting next page)",
                    "default": "",
                },
                "format": {
                    "type": "string",
                    "description": "Output format",
                    "enum": ["table", "text", "json"],
                    "default": "table",
                },
            },
            "additionalProperties": False,
            "required": [],
        },
    )


async def handle_call(request: CallToolRequest) -> CallToolResult:
    """Handle the get_logs tool call."""
    try:
        args = request.params.arguments or {}
        
        time_range = args.get("time_range", "1h")
        filters = args.get("filters", {})
        query = args.get("query")
        limit = args.get("limit", 50)
        cursor = args.get("cursor", "")
        format_type = args.get("format", "table")
        
        # Fetch log events using the new flexible API
        response = await fetch_logs(
            time_range=time_range,
            filters=filters,
            query=query,
            limit=limit,
            cursor=cursor if cursor else None,
        )
        
        log_events = response.get("data", [])
        
        # Extract log info
        logs = extract_log_info(log_events)
        
        # Get pagination info
        meta = response.get("meta", {})
        page = meta.get("page", {})
        next_cursor = page.get("after")
        
        # Check if we got zero results with a custom query
        if len(logs) == 0 and query and ":" in query:
            suggestion_msg = f"No logs found with query: '{query}'\n\n"
            suggestion_msg += "Try adjusting your query or checking if the field names are correct.\n"
            suggestion_msg += "Common log fields include: service, env, status, host, container, source"
            
            return CallToolResult(
                content=[TextContent(type="text", text=suggestion_msg)],
                isError=False,
            )
        
        # Format output
        if format_type == "json":
            # Include pagination info in JSON response
            output = {
                "logs": logs,
                "pagination": {
                    "next_cursor": next_cursor,
                    "has_more": bool(next_cursor)
                }
            }
            content = json.dumps(output, indent=2)
        elif format_type == "text":
            content = format_logs_as_text(logs)
            if next_cursor:
                content += f"\n\nNext cursor: {next_cursor}"
        else:  # table
            content = format_logs_as_table(logs)
            if next_cursor:
                content += f"\n\nNext cursor: {next_cursor}"
        
        # Add summary header (not for JSON format which includes pagination separately)
        if format_type != "json":
            summary = f"Time Range: {time_range} | Found: {len(logs)} logs"
            if cursor:
                summary += f" (cursor pagination)"
            if filters:
                filter_strs = [f"{k}={v}" for k, v in filters.items()]
                summary += f" | Filters: {', '.join(filter_strs)}"
            if query:
                summary += f" | Query: {query}"
            
            final_content = f"{summary}\n{'=' * len(summary)}\n\n{content}"
        else:
            final_content = content
        
        return CallToolResult(
            content=[TextContent(type="text", text=final_content)],
            isError=False,
        )
        
    except Exception as e:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True,
        )