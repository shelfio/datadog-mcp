"""
Aggregate traces tool
"""

import json
import logging
from typing import Any, Dict

from mcp.types import CallToolRequest, CallToolResult, Tool, TextContent

logger = logging.getLogger(__name__)

from ..utils.datadog_client import aggregate_traces


def get_tool_definition() -> Tool:
    """Get the tool definition for aggregate_traces."""
    return Tool(
        name="aggregate_traces",
        description="Aggregate APM trace counts with grouping. Use this to get total counts of traces grouped by fields like env, service, status, etc. Useful for analyzing trace volume and distributions.",
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
                    "description": "Filters to apply (e.g., {'service': 'django', 'resource_name': 'POST /graphql'})",
                    "additionalProperties": {"type": "string"},
                    "default": {},
                },
                "query": {
                    "type": "string",
                    "description": "Free-text search query (e.g., '@duration:>8000000000', 'status:error', 'service:web AND env:prod')",
                },
                "group_by": {
                    "type": "array",
                    "description": "Fields to group by for aggregation (e.g., ['env'], ['env', 'service'], ['status'])",
                    "items": {"type": "string"},
                    "default": [],
                },
                "format": {
                    "type": "string",
                    "description": "Output format",
                    "enum": ["table", "json", "summary"],
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
        args = request.arguments or {}

        time_range = args.get("time_range", "1h")
        filters = args.get("filters", {})
        query = args.get("query")
        group_by = args.get("group_by", [])
        format_type = args.get("format", "table")

        # Fetch aggregated data
        response = await aggregate_traces(
            time_range=time_range,
            filters=filters,
            query=query,
            group_by=group_by if group_by else None,
        )

        # Extract data - API returns data as a list of buckets
        buckets = response.get("data", [])

        # Format output
        if format_type == "json":
            content = json.dumps(response, indent=2)
        elif format_type == "summary":
            total = sum(bucket.get("attributes", {}).get("compute", {}).get("c0", 0) for bucket in buckets)
            content = f"Total traces: {total:,}\n"
            if group_by:
                content += f"Grouped by: {', '.join(group_by)}\n"
                content += f"Groups: {len(buckets)}\n"
            if query:
                content += f"Query: {query}\n"
            if filters:
                filter_strs = [f"{k}={v}" for k, v in filters.items()]
                content += f"Filters: {', '.join(filter_strs)}\n"
        else:  # table
            # Build header
            if group_by:
                header = " | ".join(group_by) + " | COUNT"
                content = f"Time Range: {time_range}"
                if query:
                    content += f" | Query: {query}"
                if filters:
                    filter_strs = [f"{k}={v}" for k, v in filters.items()]
                    content += f" | Filters: {', '.join(filter_strs)}"
                content += f"\n{'=' * len(header)}\n\n{header}\n"
                content += "-" * len(header) + "\n"

                # Add rows
                total = 0
                for bucket in buckets:
                    count = bucket.get("attributes", {}).get("compute", {}).get("c0", 0)
                    total += count

                    # Extract group values
                    by_values = bucket.get("attributes", {}).get("by", {})
                    row_values = [str(by_values.get(field, "")) for field in group_by]
                    row_values.append(f"{count:,}")

                    content += " | ".join(row_values) + "\n"

                content += "-" * len(header) + "\n"
                content += f"TOTAL: {total:,} traces"
            else:
                # No grouping - just total count
                total = sum(bucket.get("attributes", {}).get("compute", {}).get("c0", 0) for bucket in buckets)
                content = f"Time Range: {time_range}"
                if query:
                    content += f" | Query: {query}"
                if filters:
                    filter_strs = [f"{k}={v}" for k, v in filters.items()]
                    content += f" | Filters: {', '.join(filter_strs)}"
                content += f"\n{'=' * 50}\n\n"
                content += f"Total trace count: {total:,}"

        return CallToolResult(
            content=[TextContent(type="text", text=content)],
            isError=False,
        )

    except Exception as e:
        logger.error(f"Error in aggregate_traces handler: {str(e)}", exc_info=True)
        error_msg = f"Error aggregating traces: {str(e)}"

        # Add context about the query that failed
        if 'args' in locals():
            error_msg += f"\n\nQuery parameters:"
            if args.get("query"):
                error_msg += f"\n  - Query: {args.get('query')}"
            if args.get("filters"):
                error_msg += f"\n  - Filters: {args.get('filters')}"
            if args.get("group_by"):
                error_msg += f"\n  - Group by: {args.get('group_by')}"
            if args.get("time_range"):
                error_msg += f"\n  - Time range: {args.get('time_range')}"

        return CallToolResult(
            content=[TextContent(type="text", text=error_msg)],
            isError=True,
        )
