"""
Create monitor tool
"""

import httpx
import json
import logging
from typing import Any, Dict, Optional

from mcp.types import CallToolRequest, CallToolResult, Tool, TextContent

logger = logging.getLogger(__name__)

from ..utils.datadog_client import create_monitor


def _format_error_message(error: Exception) -> str:
    """Format error message with detailed information from Datadog API responses.

    Extracts error details from HTTP responses to provide actionable debugging information.
    """
    if isinstance(error, httpx.HTTPStatusError):
        try:
            # Try to parse JSON error response from Datadog
            response_data = error.response.json()

            # Build detailed error message
            error_msg = f"Error: Datadog API returned {error.response.status_code}\n\n"

            # Include top-level error message if present
            if "error" in response_data:
                error_msg += f"Message: {response_data['error']}\n"

            # Include errors array if present
            if "errors" in response_data:
                error_msg += "Details:\n"
                errors = response_data['errors']
                if isinstance(errors, list):
                    for err in errors:
                        error_msg += f"  - {err}\n"
                else:
                    error_msg += f"  - {errors}\n"

            # Include details field if present
            if "details" in response_data:
                error_msg += f"\nAdditional Info: {response_data['details']}\n"

            # Include error_code if present
            if "error_code" in response_data:
                error_msg += f"Error Code: {response_data['error_code']}\n"

            # Provide helpful context based on status code
            if error.response.status_code == 400:
                error_msg += "\n** Common causes of 400 errors:\n"
                error_msg += "  - Invalid query syntax (missing parentheses, quotes)\n"
                error_msg += "  - Missing required fields (thresholds for log alerts)\n"
                error_msg += "  - Incompatible field for monitor type\n"
                error_msg += "  - Malformed threshold values\n"
            elif error.response.status_code == 401:
                error_msg += "\nAuthentication failed. Check DD_API_KEY and DD_APP_KEY.\n"
            elif error.response.status_code == 403:
                error_msg += "\nPermission denied. Your API key may lack required permissions.\n"

            return error_msg.rstrip()
        except (json.JSONDecodeError, AttributeError):
            # If we can't parse JSON, fall back to text response
            pass

    # Fallback for non-HTTP errors or if JSON parsing fails
    error_str = str(error)
    if not error_str:
        error_str = type(error).__name__

    return f"Error creating monitor: {error_str}\n\nCheck that:\n" \
           "  - name, type, and query are provided\n" \
           "  - query syntax is correct for the monitor type\n" \
           "  - required thresholds are included\n" \
           "  - Datadog API credentials are valid (DD_API_KEY, DD_APP_KEY)"


def get_tool_definition() -> Tool:
    """Get the tool definition for create_monitor."""
    return Tool(
        name="create_monitor",
        description="Create a new monitor in Datadog.",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The name of the monitor",
                },
                "type": {
                    "type": "string",
                    "description": "The monitor type: 'metric alert' or 'log alert'. "
                                   "Metric alerts: query format 'avg:metric.name{filters}'. "
                                   "Log alerts: query format 'logs(\"filter\").rollup(\"count\").last(\"5m\") > threshold'",
                },
                "query": {
                    "type": "string",
                    "description": "The monitor query. "
                                   "For metric alerts: 'avg:system.cpu{*} > 0.8' "
                                   "For log alerts: 'logs(\"service:test status:error\").rollup(\"count\").last(\"5m\") > 5'",
                },
                "message": {
                    "type": "string",
                    "description": "The message to send when the monitor alerts. "
                                   "Supports template variables: {{threshold}}, {{value}}, {{tags}}, {{name}}",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tags to apply to the monitor (e.g., ['env:prod', 'team:backend'])",
                },
                "thresholds": {
                    "type": "object",
                    "description": "Alert thresholds configuration. "
                                   "For metric alerts: {'critical': value, 'warning': value} "
                                   "For log alerts: {'critical': count} (count comparison in query)",
                },
            },
            "additionalProperties": False,
            "required": ["name", "type", "query"],
        },
    )


async def handle_call(request: CallToolRequest) -> CallToolResult:
    """Handle the create_monitor tool call."""
    try:
        args = request.params.arguments or {}
        name = args.get("name")
        monitor_type = args.get("type")
        query = args.get("query")
        message = args.get("message")
        tags = args.get("tags")
        thresholds = args.get("thresholds")

        # Validate required parameters
        if not name or not monitor_type or not query:
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text="Error: name, type, and query are required\n\n"
                             "Monitor type must be 'metric alert' or 'log alert'.\n"
                             "Query examples:\n"
                             "  - Metric: 'avg:system.cpu{*} > 0.8'\n"
                             "  - Log: 'logs(\"service:test\").rollup(\"count\").last(\"5m\") > 5'",
                    )
                ],
                isError=True,
            )

        # Validate monitor type
        valid_types = ["metric alert", "log alert"]
        if monitor_type not in valid_types:
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"Error: Invalid monitor type '{monitor_type}'\n\n"
                             f"Supported types: {', '.join(valid_types)}\n\n"
                             "Monitor type-specific requirements:\n"
                             "  - metric alert: query like 'avg:metric.name{*} > threshold'\n"
                             "  - log alert: query like 'logs(\"filter\").rollup(\"count\").last(\"5m\") > threshold'",
                    )
                ],
                isError=True,
            )

        # Create monitor
        result = await create_monitor(
            name=name,
            type=monitor_type,
            query=query,
            message=message,
            tags=tags,
            thresholds=thresholds,
        )

        # Format response
        content = f"Monitor created successfully!\n\n"
        content += f"Monitor ID: {result.get('id', 'N/A')}\n"
        content += f"Name: {result.get('name', 'N/A')}\n"
        content += f"Type: {result.get('type', 'N/A')}\n"
        content += f"State: {result.get('overall_state', 'N/A')}\n"

        if result.get('tags'):
            content += f"Tags: {', '.join(result.get('tags', []))}\n"

        return CallToolResult(
            content=[TextContent(type="text", text=content)],
            isError=False,
        )

    except Exception as e:
        logger.error(f"Error in create_monitor: {e}", exc_info=True)
        error_message = _format_error_message(e)
        return CallToolResult(
            content=[TextContent(type="text", text=error_message)],
            isError=True,
        )
