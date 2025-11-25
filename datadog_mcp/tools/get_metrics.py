"""
Get metrics tool - execute metric queries on Datadog
"""

import json
import logging
from typing import Any, Dict

from mcp.types import CallToolRequest, CallToolResult, Tool, TextContent

logger = logging.getLogger(__name__)

from ..utils.datadog_client import fetch_metrics
from ..utils.formatters import (
    format_metrics_summary,
    format_metrics_table,
    format_metrics_timeseries,
)


def get_tool_definition() -> Tool:
    """Get the tool definition for get_metrics."""
    return Tool(
        name="get_metrics",
        description="Execute metric queries on Datadog. Specify the metric name and optional filters/aggregations to build and execute the query.",
        inputSchema={
            "type": "object",
            "properties": {
                "metric_name": {
                    "type": "string",
                    "description": "The metric name to query (e.g., 'aws.apigateway.count', 'system.cpu.user', 'trace.servlet.request.hits')",
                },
                "time_range": {
                    "type": "string",
                    "description": "Time range to look back",
                    "enum": ["1h", "4h", "8h", "1d", "7d", "14d", "30d"],
                    "default": "1h",
                },
                "aggregation": {
                    "type": "string",
                    "description": "Metric aggregation method",
                    "enum": ["avg", "sum", "min", "max", "count"],
                    "default": "avg",
                },
                "filters": {
                    "type": "object",
                    "description": "Filters to apply to the metric query (e.g., {'service': 'web', 'env': 'prod', 'region': 'us-east-1'})",
                    "additionalProperties": {"type": "string"},
                    "default": {},
                },
                "aggregation_by": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Fields to group/aggregate the metric by (e.g., ['service'], ['region', 'env'], ['aws_account']). Use get_metric_fields tool to see available fields.",
                    "default": [],
                },
                "as_count": {
                    "type": "boolean",
                    "description": "If true, applies .as_count() to convert rate metrics to totals. Use for count/rate metrics (e.g., 'request.hits', 'error.count'). Do NOT use for gauge metrics (e.g., 'cpu.percent', 'memory.usage'). Default: false",
                    "default": False,
                },
                "format": {
                    "type": "string",
                    "description": "Output format",
                    "enum": ["table", "summary", "timeseries", "json"],
                    "default": "table",
                },
            },
            "additionalProperties": False,
            "required": ["metric_name"],
        },
    )


async def handle_call(request: CallToolRequest) -> CallToolResult:
    """Handle the get_metrics tool call."""
    try:
        args = request.arguments or {}
        
        metric_name = args.get("metric_name")
        time_range = args.get("time_range", "1h")
        aggregation = args.get("aggregation", "avg")
        filters = args.get("filters", {})
        aggregation_by = args.get("aggregation_by", [])
        as_count = args.get("as_count", False)
        format_type = args.get("format", "table")

        # Handle legacy single aggregation_by string
        if isinstance(aggregation_by, str):
            aggregation_by = [aggregation_by]

        if not metric_name:
            return CallToolResult(
                content=[TextContent(type="text", text="Error: metric_name parameter is required")],
                isError=True,
            )

        # Fetch metrics data
        metric_result = await fetch_metrics(
            metric_name=metric_name,
            time_range=time_range,
            aggregation=aggregation,
            filters=filters,
            aggregation_by=aggregation_by,
            as_count=as_count,
        )
        
        # Wrap single result in dict for consistent formatting
        metrics_data = {metric_name: metric_result}
        
        # Check if we got zero results and suggest available fields
        has_data = False
        if not isinstance(metric_result, dict) or "error" not in metric_result:
            if "series" in metric_result and metric_result["series"]:
                has_data = True
        
        # If no data and using aggregation_by, suggest using get_metric_fields tool
        if not has_data and aggregation_by:
            suggestion_msg = f"No data found for aggregation fields: {', '.join(aggregation_by)}\n\n"
            suggestion_msg += f"To see available fields for metric '{metric_name}', use the get_metric_fields tool:\n"
            suggestion_msg += f"• Metric: {metric_name}\n"
            suggestion_msg += f"• Time Range: {time_range}\n"
            suggestion_msg += "\nThis will show all available fields you can use for aggregation_by."
            
            return CallToolResult(
                content=[TextContent(type="text", text=suggestion_msg)],
                isError=False,
            )
        
        # Format output
        if format_type == "json":
            content = json.dumps(metrics_data, indent=2)
        elif format_type == "summary":
            content = format_metrics_summary(metrics_data)
        elif format_type == "timeseries":
            content = format_metrics_timeseries(metrics_data)
        else:  # table
            content = format_metrics_table(metrics_data)
        
        # Add summary header
        summary = f"Metric: {metric_name} | Time Range: {time_range} | Aggregation: {aggregation}"
        if aggregation_by:
            summary += f" | Aggregation By: {', '.join(aggregation_by)}"
        if filters:
            summary += f" | Filters: {', '.join([f'{k}={v}' for k, v in filters.items()])}"
        
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