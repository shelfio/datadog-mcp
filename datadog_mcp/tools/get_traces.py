"""
Get APM traces tool
"""

import json
import logging
from typing import Any, Dict

from mcp.types import CallToolRequest, CallToolResult, Tool, TextContent

logger = logging.getLogger(__name__)

from ..utils.datadog_client import fetch_traces
from ..utils.formatters import format_logs_as_table, format_logs_as_text


def get_tool_definition() -> Tool:
    """Get the tool definition for get_traces."""
    return Tool(
        name="get_traces",
        description="Search and retrieve APM traces from Datadog. Search for slow traces, errors, or specific service calls.",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Trace query string (e.g., '@duration:>5000000000' for traces >5s, 'service:web', 'status:error')",
                    "default": "*",
                },
                "time_range": {
                    "type": "string",
                    "description": "Time range to look back",
                    "enum": ["1h", "4h", "8h", "1d", "7d", "14d", "30d"],
                    "default": "1h",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of traces to return (default: 10)",
                    "default": 10,
                    "minimum": 1,
                    "maximum": 100,
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
    """Handle the get_traces tool call."""
    try:
        args = request.params.arguments or {}

        query = args.get("query", "*")
        time_range = args.get("time_range", "1h")
        limit = args.get("limit", 10)
        cursor = args.get("cursor", "")
        format_type = args.get("format", "table")

        # Fetch traces using the API
        response = await fetch_traces(
            query=query,
            time_range=time_range,
            limit=limit,
            cursor=cursor if cursor else None,
        )

        traces = response.get("data", [])

        # Get pagination info
        meta = response.get("meta", {})
        page = meta.get("page", {})
        next_cursor = page.get("after")

        # Check if we got zero results
        if len(traces) == 0:
            suggestion_msg = f"No traces found with query: '{query}'\n\n"
            suggestion_msg += "Try adjusting your query. Common examples:\n"
            suggestion_msg += "- @duration:>5000000000 (traces longer than 5 seconds)\n"
            suggestion_msg += "- service:web (specific service)\n"
            suggestion_msg += "- status:error (error traces)\n"
            suggestion_msg += "- @http.status_code:500 (HTTP 500 errors)"

            return CallToolResult(
                content=[TextContent(type="text", text=suggestion_msg)],
                isError=False,
            )

        # Format output
        if format_type == "json":
            # Include pagination info in JSON response
            output = {
                "traces": traces,
                "pagination": {"next_cursor": next_cursor, "has_more": bool(next_cursor)},
            }
            content = json.dumps(output, indent=2)
        elif format_type == "text":
            # Format as readable text
            lines = []
            for i, trace in enumerate(traces, 1):
                lines.append(f"Trace {i}:")
                if "attributes" in trace:
                    attrs = trace["attributes"]
                    lines.append(f"  Resource: {attrs.get('resource.name', 'N/A')}")
                    lines.append(f"  Service: {attrs.get('service.name', 'N/A')}")
                    lines.append(f"  Duration: {attrs.get('duration', 'N/A')}ms")
                    lines.append(f"  Status: {attrs.get('http.status_code', attrs.get('status', 'N/A'))}")
                lines.append("")

            content = "\n".join(lines)
            if next_cursor:
                content += f"\nNext cursor: {next_cursor}"
        else:  # table
            # Format as table - convert trace data to table-like format
            lines = []
            lines.append("Resource\t\tService\t\tDuration\tStatus")
            lines.append("-" * 80)

            for trace in traces:
                if "attributes" in trace:
                    attrs = trace["attributes"]
                    resource = attrs.get("resource.name", "N/A")[:30]
                    service = attrs.get("service.name", "N/A")[:20]
                    duration = str(attrs.get("duration", "N/A"))[:10]
                    status = str(attrs.get("http.status_code", attrs.get("status", "N/A")))[:10]
                    lines.append(f"{resource}\t{service}\t{duration}\t{status}")

            content = "\n".join(lines)
            if next_cursor:
                content += f"\n\nNext cursor: {next_cursor}"

        # Add summary header
        summary = f"Time Range: {time_range} | Found: {len(traces)} traces"
        if cursor:
            summary += f" (cursor pagination)"
        if query != "*":
            summary += f" | Query: {query}"

        final_content = f"{summary}\n{'=' * len(summary)}\n\n{content}"

        return CallToolResult(
            content=[TextContent(type="text", text=final_content)],
            isError=False,
        )

    except Exception as e:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True,
        )
