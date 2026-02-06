"""
Check deployment tool - verify if a version is deployed to a service
"""

import json
import logging
from typing import Any, Dict

from mcp.types import CallToolRequest, CallToolResult, Tool, TextContent

logger = logging.getLogger(__name__)

from ..utils.datadog_client import fetch_logs


def get_tool_definition() -> Tool:
    """Get the tool definition for check_deployment."""
    return Tool(
        name="check_deployment",
        description="Verify if a specific version is deployed to a service by querying logs for version tags.",
        inputSchema={
            "type": "object",
            "properties": {
                "service": {
                    "type": "string",
                    "description": "Service name to check (e.g., 'web', 'api', 'detection-service')",
                },
                "version_field": {
                    "type": "string",
                    "description": "Field name containing version info (e.g., 'git.commit.sha', 'version', 'dd.version', 'deployment.id'). Use get_logs_field_values to discover available fields.",
                },
                "version_value": {
                    "type": "string",
                    "description": "Version value to search for (e.g., 'abc123def456', 'v1.2.3', 'd1a2b3c4')",
                },
                "environment": {
                    "type": "string",
                    "description": "Optional environment filter (e.g., 'prod', 'staging', 'integrations', 'test-customer')",
                },
                "time_range": {
                    "type": "string",
                    "description": "Time range to search for deployment logs",
                    "enum": ["1h", "4h", "8h", "1d", "7d", "14d", "30d"],
                    "default": "1h",
                },
                "format": {
                    "type": "string",
                    "description": "Output format",
                    "enum": ["summary", "detailed", "json"],
                    "default": "summary",
                },
            },
            "additionalProperties": False,
            "required": ["service", "version_field", "version_value"],
        },
    )


async def handle_call(request: CallToolRequest) -> CallToolResult:
    """Handle the check_deployment tool call."""
    try:
        args = request.arguments or {}

        service = args.get("service")
        version_field = args.get("version_field")
        version_value = args.get("version_value")
        environment = args.get("environment")
        time_range = args.get("time_range", "1h")
        format_type = args.get("format", "summary")

        if not service:
            return CallToolResult(
                content=[TextContent(type="text", text="Error: service parameter is required")],
                isError=True,
            )

        if not version_field:
            return CallToolResult(
                content=[TextContent(type="text", text="Error: version_field parameter is required")],
                isError=True,
            )

        if not version_value:
            return CallToolResult(
                content=[TextContent(type="text", text="Error: version_value parameter is required")],
                isError=True,
            )

        # Check deployment status
        # Build filters for log query
        filters = {
            "service": service,
            version_field: version_value,
        }

        if environment:
            filters["env"] = environment

        # Check deployment by querying logs for the version
        logs = await fetch_logs(
            time_range=time_range,
            filters=filters,
        )

        log_entries = logs.get("data", [])
        found = len(log_entries) > 0

        # Format output
        if format_type == "json":
            result = {
                "service": service,
                "version_field": version_field,
                "version_value": version_value,
                "environment": environment or "all",
                "time_range": time_range,
                "deployed": found,
                "log_count": len(log_entries),
                "logs": log_entries[:10],
            }
            content = json.dumps(result, indent=2)
        else:
            status_text = "✅ DEPLOYED" if found else "❌ NOT FOUND"
            content = (
                f"{status_text}\n\n"
                f"Service: {service}\n"
                f"Version Field: {version_field}\n"
                f"Version Value: {version_value}\n"
                f"Environment: {environment or 'all'}\n"
                f"Time Range: {time_range}\n"
                f"Matching Logs: {len(log_entries)}\n"
            )

            if found and format_type == "detailed":
                content += "\nRecent Logs:\n"
                for i, log in enumerate(log_entries[:5], 1):
                    attrs = log.get("attributes", {})
                    msg = attrs.get("message", "N/A")
                    ts = attrs.get("timestamp", "N/A")
                    content += f"{i}. [{ts}] {msg}\n"

        return CallToolResult(
            content=[TextContent(type="text", text=content)],
            isError=False,
        )

    except Exception as e:
        error_msg = f"Error checking deployment: {str(e)}\n\n"
        error_msg += "Common issues:\n"
        error_msg += "• Invalid service name - use get_logs to discover available services\n"
        error_msg += "• Invalid version_field - use get_logs_field_values to discover available fields\n"
        error_msg += "• Version not found - check if version_value is correct and expand time_range\n"
        error_msg += "• No logs for service - ensure service has logs in Datadog"

        return CallToolResult(
            content=[TextContent(type="text", text=error_msg)],
            isError=True,
        )
