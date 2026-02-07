"""
Query metric formula tool - execute metric formulas using Datadog V2 API
"""

import json
import logging
from typing import Any, Dict

from mcp.types import CallToolRequest, CallToolResult, Tool, TextContent

logger = logging.getLogger(__name__)

from ..utils.datadog_client import fetch_metric_formula
from ..utils.formatters import (
    format_formula_result_summary,
    format_formula_result_timeseries,
)


def get_tool_definition() -> Tool:
    """Get the tool definition for query_metric_formula."""
    return Tool(
        name="query_metric_formula",
        description="Execute metric formulas using Datadog V2 API (e.g., 'a / b * 100'). Compare/calculate multiple metrics using arithmetic operations.",
        inputSchema={
            "type": "object",
            "properties": {
                "formula": {
                    "type": "string",
                    "description": "Formula string using query variables (e.g., 'a / b * 100', 'a - b', '(a + b) / c'). Supports: +, -, *, /, parentheses",
                },
                "queries": {
                    "type": "object",
                    "description": "Dict of query definitions. Keys are variable names used in formula (a, b, c, etc.), values are query definitions with metric_name and aggregation",
                    "additionalProperties": {
                        "type": "object",
                        "properties": {
                            "metric_name": {
                                "type": "string",
                                "description": "The metric name (e.g., 'errors', 'requests', 'system.cpu.user')",
                            },
                            "aggregation": {
                                "type": "string",
                                "description": "Aggregation method",
                                "enum": ["avg", "sum", "min", "max", "count"],
                                "default": "avg",
                            },
                        },
                        "required": ["metric_name"],
                    },
                },
                "time_range": {
                    "type": "string",
                    "description": "Time range to look back",
                    "enum": ["1h", "4h", "8h", "1d", "7d", "14d", "30d"],
                    "default": "1h",
                },
                "filters": {
                    "type": "object",
                    "description": "Filters to apply to all queries (e.g., {'service': 'web', 'env': 'prod'})",
                    "additionalProperties": {"type": "string"},
                    "default": {},
                },
                "format": {
                    "type": "string",
                    "description": "Output format",
                    "enum": ["summary", "timeseries", "json"],
                    "default": "summary",
                },
            },
            "additionalProperties": False,
            "required": ["formula", "queries"],
        },
    )


async def handle_call(request: CallToolRequest) -> CallToolResult:
    """Handle the query_metric_formula tool call."""
    try:
        args = request.params.arguments or {}

        formula = args.get("formula")
        queries = args.get("queries", {})
        time_range = args.get("time_range", "1h")
        filters = args.get("filters", {})
        format_type = args.get("format", "summary")

        if not formula:
            return CallToolResult(
                content=[TextContent(type="text", text="Error: formula parameter is required")],
                isError=True,
            )

        if not queries:
            return CallToolResult(
                content=[TextContent(type="text", text="Error: queries parameter is required with at least one query")],
                isError=True,
            )

        # Validate that all variables in formula are defined in queries
        import re
        formula_vars = set(re.findall(r'[a-z]', formula.lower()))
        query_vars = set(queries.keys())

        missing_vars = formula_vars - query_vars
        if missing_vars:
            error_msg = f"Error: Formula uses undefined variables: {', '.join(sorted(missing_vars))}\n"
            error_msg += f"Defined query variables: {', '.join(sorted(query_vars))}\n"
            error_msg += f"Example: formula='a / b * 100', queries={{'a': {{'metric_name': 'errors', 'aggregation': 'sum'}}, 'b': {{'metric_name': 'requests', 'aggregation': 'sum'}}}}"
            return CallToolResult(
                content=[TextContent(type="text", text=error_msg)],
                isError=True,
            )

        # Fetch formula result
        result = await fetch_metric_formula(
            formula=formula,
            queries=queries,
            time_range=time_range,
            filters=filters,
        )

        # Format output
        if format_type == "json":
            content = json.dumps(result, indent=2)
        elif format_type == "timeseries":
            content = format_formula_result_timeseries(result)
        else:  # summary
            content = format_formula_result_summary(result)

        # Add header
        summary = f"Formula: {formula} | Time Range: {time_range}"
        if filters:
            summary += f" | Filters: {', '.join([f'{k}={v}' for k, v in filters.items()])}"

        final_content = f"{summary}\n{'=' * len(summary)}\n\n{content}"

        return CallToolResult(
            content=[TextContent(type="text", text=final_content)],
            isError=False,
        )

    except Exception as e:
        error_msg = f"Error executing formula: {str(e)}\n\n"
        error_msg += "Common issues:\n"
        error_msg += "• Invalid formula syntax - use +, -, *, / and parentheses\n"
        error_msg += "• Query name mismatch - ensure query keys match formula variables\n"
        error_msg += "• Invalid metric name - check metric name is correct\n"
        error_msg += "• No data - metric may not have data in the time range"

        return CallToolResult(
            content=[TextContent(type="text", text=error_msg)],
            isError=True,
        )
