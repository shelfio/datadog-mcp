"""
Update monitor tool
"""

import httpx
import json
import logging
from typing import Any, Dict, Optional

from mcp.types import CallToolRequest, CallToolResult, Tool, TextContent

logger = logging.getLogger(__name__)

from ..utils.datadog_client import update_monitor


def _format_error_message(error: Exception) -> str:
    """Format error message with detailed information from Datadog API responses."""
    if isinstance(error, httpx.HTTPStatusError):
        try:
            response_data = error.response.json()
            error_msg = f"Error: Datadog API returned {error.response.status_code}\n\n"

            if "error" in response_data:
                error_msg += f"Message: {response_data['error']}\n"

            if "errors" in response_data:
                error_msg += "Details:\n"
                errors = response_data['errors']
                if isinstance(errors, list):
                    for err in errors:
                        error_msg += f"  - {err}\n"
                else:
                    error_msg += f"  - {errors}\n"

            if "details" in response_data:
                error_msg += f"\nAdditional Info: {response_data['details']}\n"

            if error.response.status_code == 400:
                error_msg += "\n** Common causes of 400 errors:\n"
                error_msg += "  - Invalid query syntax\n"
                error_msg += "  - Incompatible field for monitor type\n"
                error_msg += "  - Malformed threshold values\n"
            elif error.response.status_code == 401:
                error_msg += "\nAuthentication failed. Check DD_API_KEY and DD_APP_KEY.\n"
            elif error.response.status_code == 403:
                error_msg += "\nPermission denied. Your API key may lack required permissions.\n"
            elif error.response.status_code == 404:
                error_msg += "\nMonitor not found. Verify the monitor_id is correct.\n"

            return error_msg.rstrip()
        except (json.JSONDecodeError, AttributeError):
            pass

    error_str = str(error)
    if not error_str:
        error_str = type(error).__name__

    return f"Error updating monitor: {error_str}\n\nCheck that:\n" \
           "  - monitor_id is valid and exists\n" \
           "  - query syntax is correct for the monitor type\n" \
           "  - Datadog API credentials are valid (DD_API_KEY, DD_APP_KEY)"


def get_tool_definition() -> Tool:
    """Get the tool definition for update_monitor."""
    return Tool(
        name="update_monitor",
        description="Update an existing monitor in Datadog.",
        inputSchema={
            "type": "object",
            "properties": {
                "monitor_id": {
                    "type": "string",
                    "description": "The ID of the monitor to update (numeric ID from list_monitors)",
                },
                "name": {
                    "type": "string",
                    "description": "The new name for the monitor",
                },
                "query": {
                    "type": "string",
                    "description": "The new query for the monitor. "
                                   "For metric alerts: 'avg:metric.name{*} > threshold'. "
                                   "For log alerts: 'logs(\"filter\").rollup(\"count\").last(\"5m\") > threshold'",
                },
                "message": {
                    "type": "string",
                    "description": "The new message to send when the monitor alerts. "
                                   "Supports template variables: {{threshold}}, {{value}}, {{tags}}, {{name}}",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "New tags to apply to the monitor (e.g., ['env:prod', 'team:backend'])",
                },
                "thresholds": {
                    "type": "object",
                    "description": "New alert thresholds. "
                                   "For metric alerts: {'critical': value, 'warning': value}. "
                                   "For log alerts: {'critical': count}",
                },
            },
            "additionalProperties": False,
            "required": ["monitor_id"],
        },
    )


async def handle_call(request: CallToolRequest) -> CallToolResult:
    """Handle the update_monitor tool call."""
    try:
        args = request.params.arguments or {}
        monitor_id = args.get("monitor_id")

        if not monitor_id:
            return CallToolResult(
                content=[TextContent(type="text", text="Error: monitor_id is required")],
                isError=True,
            )

        # Convert monitor_id to int if it's a string
        try:
            monitor_id = int(monitor_id)
        except (ValueError, TypeError):
            return CallToolResult(
                content=[TextContent(type="text", text="Error: monitor_id must be a valid integer")],
                isError=True,
            )

        # Prepare update parameters
        name = args.get("name")
        query = args.get("query")
        message = args.get("message")
        tags = args.get("tags")
        thresholds = args.get("thresholds")

        # Update monitor
        result = await update_monitor(
            monitor_id=monitor_id,
            name=name,
            query=query,
            message=message,
            tags=tags,
            thresholds=thresholds,
        )

        # Format response
        content = f"Monitor {monitor_id} updated successfully!\n\n"
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
        logger.error(f"Error in update_monitor: {e}", exc_info=True)
        error_message = _format_error_message(e)
        return CallToolResult(
            content=[TextContent(type="text", text=error_message)],
            isError=True,
        )
