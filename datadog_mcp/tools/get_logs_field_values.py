"""
Tool for discovering possible values for log fields to understand filtering options.
"""

import logging
from typing import Any, Dict, List, Optional

from mcp import types
from mcp.types import CallToolResult, TextContent, Tool

from ..utils.datadog_client import fetch_logs_filter_values

logger = logging.getLogger(__name__)


def get_tool_definition() -> Tool:
    """Get the tool definition for discovering log field values."""
    return Tool(
        name="get_logs_field_values",
        description="Get possible values for a specific log field to understand filtering options",
        inputSchema={
            "type": "object",
            "properties": {
                "field_name": {
                    "type": "string",
                    "description": "The field to get possible values for (e.g., 'service', 'env', 'status', 'host', 'source', 'environment', 'errorMessage', 'logger.name', 'region', 'lambda.arn', 'functionname', 'lambda.name', 'lambda.request_id', 'xray.TraceId', 'http.referer', 'mongodb.collectionName', 'mongodb.dbName')",
                },
                "time_range": {
                    "type": "string",
                    "enum": ["1h", "4h", "8h", "1d", "7d", "14d", "30d"],
                    "default": "1h",
                    "description": "Time range to look back",
                },
                "query": {
                    "type": "string",
                    "description": "Optional query to filter logs before discovering field values",
                },
                "limit": {
                    "type": "integer",
                    "default": 100,
                    "minimum": 1,
                    "maximum": 1000,
                    "description": "Maximum number of field values to return",
                },
                "format": {
                    "type": "string",
                    "enum": ["table", "list", "json"],
                    "default": "table",
                    "description": "Output format",
                },
            },
            "required": ["field_name"],
        },
    )


async def handle_call(request: types.CallToolRequest) -> CallToolResult:
    """Handle the get_logs_field_values tool call."""
    try:
        # Extract parameters
        field_name = request.params.arguments.get("field_name")
        time_range = request.params.arguments.get("time_range", "1h")
        query = request.params.arguments.get("query")
        limit = request.params.arguments.get("limit", 100)
        format_type = request.params.arguments.get("format", "table")
        
        # Validate required parameters
        if not field_name:
            return CallToolResult(
                content=[TextContent(type="text", text="Error: field_name is required")],
                isError=True,
            )
        
        # Fetch field values
        response = await fetch_logs_filter_values(
            field_name=field_name,
            time_range=time_range,
            query=query,
            limit=limit,
        )
        
        # Format response
        if format_type == "json":
            import json
            content = json.dumps(response, indent=2)
        elif format_type == "list":
            content = _format_as_list(response)
        else:  # table
            content = _format_as_table(response)
        
        return CallToolResult(
            content=[TextContent(type="text", text=content)],
            isError=False,
        )
    
    except Exception as e:
        logger.error(f"Error in get_logs_field_values: {e}")
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error discovering field values: {str(e)}")],
            isError=True,
        )


def _format_as_table(response: Dict[str, Any]) -> str:
    """Format field values as a table."""
    field_name = response["field"]
    time_range = response["time_range"]
    values = response["values"]
    total_values = response["total_values"]
    
    if not values:
        return f"No values found for field '{field_name}' in the last {time_range}"
    
    # Create header
    header = f"Field: {field_name} | Time Range: {time_range} | Total Values: {total_values}\n"
    header += "=" * len(header.strip()) + "\n\n"
    
    # Create table
    table = "| Value | Count |\n"
    table += "|-------|-------|\n"
    
    for item in values:
        value = str(item["value"])
        count = item["count"]
        # Truncate long values
        if len(value) > 50:
            value = value[:47] + "..."
        table += f"| {value:<50} | {count:>5} |\n"
    
    return header + table


def _format_as_list(response: Dict[str, Any]) -> str:
    """Format field values as a simple list."""
    field_name = response["field"]
    time_range = response["time_range"]
    values = response["values"]
    total_values = response["total_values"]
    
    if not values:
        return f"No values found for field '{field_name}' in the last {time_range}"
    
    result = f"Field: {field_name} | Time Range: {time_range} | Total Values: {total_values}\n\n"
    
    for item in values:
        result += f"• {item['value']} ({item['count']} occurrences)\n"
    
    return result