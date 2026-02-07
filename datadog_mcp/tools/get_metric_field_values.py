"""
Get metric field values tool
"""

import json
import logging
from typing import Any, Dict

from mcp.types import CallToolRequest, CallToolResult, Tool, TextContent

logger = logging.getLogger(__name__)

from ..utils.datadog_client import fetch_metric_field_values


def get_tool_definition() -> Tool:
    """Get the tool definition for get_metric_field_values."""
    return Tool(
        name="get_metric_field_values",
        description="Get all possible values for a specific field of a metric from Datadog to discover available dimensions",
        inputSchema={
            "type": "object",
            "properties": {
                "metric_name": {
                    "type": "string",
                    "description": "Datadog metric name to get field values for (e.g., 'aws.apigateway.count', 'system.cpu.user')",
                },
                "field_name": {
                    "type": "string", 
                    "description": "Field name to get all possible values for (e.g., 'service', 'region', 'account', 'environment')",
                },
                "format": {
                    "type": "string",
                    "description": "Output format",
                    "enum": ["list", "json"],
                    "default": "list",
                },
            },
            "additionalProperties": False,
            "required": ["metric_name", "field_name"],
        },
    )


async def handle_call(request: CallToolRequest) -> CallToolResult:
    """Handle the get_metric_field_values tool call."""
    try:
        args = request.params.arguments or {}
        
        metric_name = args.get("metric_name")
        field_name = args.get("field_name")
        format_type = args.get("format", "list")
        
        if not metric_name:
            return CallToolResult(
                content=[TextContent(type="text", text="Error: metric_name parameter is required")],
                isError=True,
            )
            
        if not field_name:
            return CallToolResult(
                content=[TextContent(type="text", text="Error: field_name parameter is required")],
                isError=True,
            )
        
        # Fetch field values
        field_values = await fetch_metric_field_values(
            metric_name=metric_name,
            field_name=field_name,
        )
        
        # Format output
        if format_type == "json":
            content = json.dumps({
                "metric_name": metric_name,
                "field_name": field_name,
                "field_values": field_values
            }, indent=2)
        else:  # list format
            # Add summary header
            summary = f"Values for field '{field_name}' in metric '{metric_name}'"
            
            content = f"{summary}\n{'=' * len(summary)}\n\n"
            
            if field_values:
                content += f"Found {len(field_values)} unique values for field '{field_name}':\n\n"
                content += "\n".join([f"  • {value}" for value in field_values])
                content += f"\n\nUsage examples:\n"
                content += f"• Filter by specific value: add filter {field_name}:<value> to your query\n"
                content += f"• Group by this field: aggregation_by: [\"{field_name}\"]\n"
                content += f"• Combine with other fields: aggregation_by: [\"{field_name}\", \"env\"]\n"
                if field_values:
                    sample_value = field_values[0]
                    content += f"• Query for specific {field_name}: add filter {field_name}:{sample_value} to your query"
            else:
                content += f"No values found for field '{field_name}'.\n\n"
                content += "This could mean:\n"
                content += f"• The field '{field_name}' doesn't exist for this metric\n"
                content += f"• The metric '{metric_name}' doesn't exist\n\n"
                content += "Try:\n"
                content += "• Using get_metric_fields tool to see available fields\n"
                content += "• Checking the metric name"
        
        return CallToolResult(
            content=[TextContent(type="text", text=content)],
            isError=False,
        )
        
    except Exception as e:
        logger.error(f"Error in get_metric_field_values: {e}")
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True,
        )