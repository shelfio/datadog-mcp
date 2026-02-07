"""
Get metric fields tool
"""

import json
import logging
from typing import Any, Dict

from mcp.types import CallToolRequest, CallToolResult, Tool, TextContent

logger = logging.getLogger(__name__)

from ..utils.datadog_client import fetch_metric_available_fields


def get_tool_definition() -> Tool:
    """Get the tool definition for get_metric_fields."""
    return Tool(
        name="get_metric_fields",
        description="Get available fields/tags for a specific metric from Datadog to help with aggregation queries",
        inputSchema={
            "type": "object",
            "properties": {
                "metric_name": {
                    "type": "string",
                    "description": "Datadog metric name to get available fields for",
                },
                "time_range": {
                    "type": "string",
                    "description": "Time range to look back for field discovery (currently not used by the API but kept for consistency)",
                    "enum": ["1h", "4h", "8h", "1d", "7d", "14d", "30d"],
                    "default": "1h",
                },
                "format": {
                    "type": "string",
                    "description": "Output format",
                    "enum": ["list", "json"],
                    "default": "list",
                },
            },
            "additionalProperties": False,
            "required": ["metric_name"],
        },
    )


async def handle_call(request: CallToolRequest) -> CallToolResult:
    """Handle the get_metric_fields tool call."""
    try:
        args = request.params.arguments or {}
        
        metric_name = args.get("metric_name")
        time_range = args.get("time_range", "1h")
        format_type = args.get("format", "list")
        
        if not metric_name:
            return CallToolResult(
                content=[TextContent(type="text", text="Error: metric_name parameter is required")],
                isError=True,
            )
        
        # Fetch available fields
        available_fields = await fetch_metric_available_fields(
            metric_name=metric_name,
            time_range=time_range,
        )
        
        # Format output
        if format_type == "json":
            content = json.dumps({
                "metric_name": metric_name,
                "time_range": time_range,
                "available_fields": available_fields
            }, indent=2)
        else:  # list format
            # Add summary header
            summary = f"Available fields for metric '{metric_name}'"
            
            content = f"{summary}\n{'=' * len(summary)}\n\n"
            
            if available_fields:
                content += "Available aggregation fields:\n"
                content += "\n".join([f"  • {field}" for field in available_fields])
                content += f"\n\nUsage example: aggregation_by: [\"{available_fields[0]}\"]"
                if len(available_fields) > 1:
                    content += f" or [\"{available_fields[0]}\", \"{available_fields[1]}\"]"
            else:
                content += "No fields found for this metric."
        
        return CallToolResult(
            content=[TextContent(type="text", text=content)],
            isError=False,
        )
        
    except Exception as e:
        logger.error(f"Error in get_metric_fields: {e}")
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True,
        )