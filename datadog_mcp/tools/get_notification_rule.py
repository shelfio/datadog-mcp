"""
Get notification rule tool
"""

import json
import logging

from mcp.types import CallToolRequest, CallToolResult, Tool, TextContent
import httpx

logger = logging.getLogger(__name__)

from ..utils.datadog_client import fetch_notification_rule


def get_tool_definition() -> Tool:
    """Get the tool definition for get_notification_rule."""
    return Tool(
        name="get_notification_rule",
        description="Get details for a specific Datadog monitor notification rule by ID.",
        inputSchema={
            "type": "object",
            "properties": {
                "rule_id": {
                    "type": "string",
                    "description": "The ID of the notification rule to fetch.",
                },
                "format": {
                    "type": "string",
                    "description": "Output format",
                    "enum": ["table", "json", "summary"],
                    "default": "table",
                },
            },
            "additionalProperties": False,
            "required": ["rule_id"],
        },
    )


async def handle_call(request: CallToolRequest) -> CallToolResult:
    """Handle the get_notification_rule tool call."""
    try:
        args = request.arguments or {}

        rule_id = args.get("rule_id")
        format_type = args.get("format", "table")

        if rule_id is None:
            return CallToolResult(
                content=[TextContent(type="text", text="Error: rule_id is required")],
                isError=True,
            )

        rule = await fetch_notification_rule(rule_id)

        attrs = rule.get("attributes", {})
        rule_name = attrs.get("name", "Unnamed")
        filter_obj = attrs.get("filter", {})
        scope = filter_obj.get("scope", "")
        filter_tags = filter_obj.get("tags", [])
        recipients = attrs.get("recipients", [])
        conditional = attrs.get("conditional_recipients", {})

        if format_type == "json":
            content = json.dumps(rule, indent=2)
        elif format_type == "summary":
            content = f"Notification Rule: {rule_name}\n"
            content += f"ID: {rule_id}\n"
            content += f"Scope: {scope}\n"
            content += f"Tags: {len(filter_tags)}\n"
            content += f"Recipients: {len(recipients)}\n"
            if conditional and conditional.get("conditions"):
                content += f"Conditional Recipients: {len(conditional.get('conditions', []))} conditions"
        else:
            content = "Notification Rule Details\n"
            content += "=" * 25 + "\n\n"
            content += f"ID:       {rule_id}\n"
            content += f"Name:     {rule_name}\n"
            content += f"Scope:    {scope}\n"

            if filter_tags:
                tags_str = ", ".join(filter_tags[:5])
                if len(filter_tags) > 5:
                    tags_str += f" (+{len(filter_tags) - 5} more)"
                content += f"Tags:     {tags_str}\n"
            else:
                content += "Tags:     None\n"

            if recipients:
                recipients_str = ", ".join(recipients[:5])
                if len(recipients) > 5:
                    recipients_str += f" (+{len(recipients) - 5} more)"
                content += f"Recipients: {recipients_str}\n"
            else:
                content += "Recipients: None\n"

            if conditional:
                conditions = conditional.get("conditions", [])
                fallback = conditional.get("fallback_recipients", [])

                if conditions:
                    content += "\nConditional Recipients:\n"
                    for cond in conditions:
                        cond_scope = cond.get("scope", "")
                        cond_recipients = cond.get("recipients", [])
                        cond_recipients_str = ", ".join(cond_recipients[:3])
                        if len(cond_recipients) > 3:
                            cond_recipients_str += f" (+{len(cond_recipients) - 3})"
                        content += f"  - {cond_scope}: {cond_recipients_str}\n"

                if fallback:
                    fallback_str = ", ".join(fallback[:3])
                    if len(fallback) > 3:
                        fallback_str += f" (+{len(fallback) - 3})"
                    content += f"  Fallback: {fallback_str}\n"

        return CallToolResult(
            content=[TextContent(type="text", text=content)],
            isError=False,
        )

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return CallToolResult(
                content=[TextContent(type="text", text="Notification rule not found")],
                isError=True,
            )
        logger.error(f"Error in get_notification_rule: {e}")
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True,
        )
    except Exception as e:
        logger.error(f"Error in get_notification_rule: {e}")
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True,
        )
