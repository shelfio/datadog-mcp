"""
Get aggregated APM traces tool
"""

import json
import logging
from typing import Any, Dict, Optional

from mcp.types import CallToolRequest, CallToolResult, Tool, TextContent

logger = logging.getLogger(__name__)

from ..utils.datadog_client import aggregate_traces


def get_tool_definition() -> Tool:
    """Get the tool definition for aggregate_traces."""
    return Tool(
        name="aggregate_traces",
        description="Aggregate APM traces from Datadog by grouping by specified dimensions (e.g., service, status). Returns statistics like count, duration averages, percentiles, etc.",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Trace query string (e.g., 'service:web', 'status:error', '@duration:>5000000000')",
                    "default": "*",
                },
                "group_by": {
                    "type": "array",
                    "description": "Fields to group aggregation by (e.g., ['service.name'], ['service.name', 'http.status_code'])",
                    "items": {"type": "string"},
                    "default": [],
                },
                "aggregation": {
                    "type": "string",
                    "description": "Aggregation function to apply (count, avg, min, max, sum, percentile)",
                    "enum": ["count", "avg", "min", "max", "sum", "percentile"],
                    "default": "count",
                },
                "time_range": {
                    "type": "string",
                    "description": "Time range to look back",
                    "enum": ["1h", "4h", "8h", "1d", "7d", "14d", "30d"],
                    "default": "1h",
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
    """Handle the aggregate_traces tool call."""
    try:
        args = request.params.arguments or {}

        query = args.get("query", "*")
        group_by = args.get("group_by", [])
        aggregation = args.get("aggregation", "count")
        time_range = args.get("time_range", "1h")
        format_type = args.get("format", "table")

        # Fetch aggregated traces using the API
        response = await aggregate_traces(
            query=query,
            group_by=group_by if group_by else None,
            time_range=time_range,
        )

        traces = response.get("data", [])

        # Check if we got zero results
        if len(traces) == 0:
            suggestion_msg = f"No aggregated trace results found with query: '{query}'\n\n"
            suggestion_msg += "Try adjusting your query or group_by fields. Common examples:\n"
            suggestion_msg += "- group_by: ['service.name'] (aggregate by service)\n"
            suggestion_msg += "- group_by: ['http.status_code'] (aggregate by HTTP status)\n"
            suggestion_msg += "- group_by: ['service.name', 'http.status_code'] (aggregate by service and status)\n"
            suggestion_msg += "- query: 'status:error' (filter to errors only)\n"
            suggestion_msg += "- aggregation: 'avg' or 'max' (change aggregation type)"

            return CallToolResult(
                content=[TextContent(type="text", text=suggestion_msg)],
                isError=False,
            )

        # Format output
        if format_type == "json":
            # Include aggregation info in JSON response
            output = {
                "aggregation": aggregation,
                "group_by": group_by,
                "query": query,
                "data": traces,
            }
            content = json.dumps(output, indent=2)
        elif format_type == "text":
            # Format as readable text
            lines = []
            lines.append(f"Aggregation: {aggregation}")
            lines.append(f"Grouped by: {', '.join(group_by) if group_by else 'none'}")
            lines.append("")

            for i, trace in enumerate(traces, 1):
                lines.append(f"Result {i}:")
                if "attributes" in trace:
                    attrs = trace["attributes"]
                    for key, value in attrs.items():
                        lines.append(f"  {key}: {value}")
                lines.append("")

            content = "\n".join(lines)
        else:  # table
            # Format as table
            lines = []

            # Get unique attribute keys across all results
            all_keys = set()
            for trace in traces:
                if "attributes" in trace:
                    all_keys.update(trace["attributes"].keys())

            if all_keys:
                # Sort keys for consistent ordering
                sorted_keys = sorted(list(all_keys))

                # Create header
                header = "\t".join(k[:20] for k in sorted_keys)
                lines.append(header)
                lines.append("-" * 80)

                # Add rows
                for trace in traces:
                    if "attributes" in trace:
                        attrs = trace["attributes"]
                        row = []
                        for key in sorted_keys:
                            value = str(attrs.get(key, "N/A"))[:20]
                            row.append(value)
                        lines.append("\t".join(row))

            content = "\n".join(lines) if lines else "No data to display"

        # Add summary header
        summary = f"Time Range: {time_range} | Aggregation: {aggregation} | Results: {len(traces)}"
        if group_by:
            summary += f" | Grouped by: {', '.join(group_by)}"
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
