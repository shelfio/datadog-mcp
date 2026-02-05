"""
List notification rules tool
"""

import json
import logging
from typing import Any, Dict

from mcp.types import CallToolRequest, CallToolResult, Tool, TextContent

logger = logging.getLogger(__name__)

from ..utils.datadog_client import fetch_notification_rules


def get_tool_definition() -> Tool:
    """Get the tool definition for list_notification_rules."""
    return Tool(
        name="list_notification_rules",
        description="List monitor notification rules from Datadog. Notification rules automate routing of monitor alerts to recipients based on tag-based scope rules.",
        inputSchema={
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Free-text search on name, tags, recipients. Leave empty to list all rules.",
                    "default": "",
                },
                "tags": {
                    "type": "string",
                    "description": "Filter rules by tags (comma-separated, e.g., 'team:platform,env:prod'). Leave empty to include all rules.",
                    "default": "",
                },
                "recipients": {
                    "type": "string",
                    "description": "Filter rules by recipients (comma-separated, e.g., '@slack-alerts,@pagerduty'). Leave empty to include all rules.",
                    "default": "",
                },
                "format": {
                    "type": "string",
                    "description": "Output format",
                    "enum": ["table", "json", "summary"],
                    "default": "table",
                },
                "page_size": {
                    "type": "integer",
                    "description": "Number of rules per page (default: 50)",
                    "default": 50,
                    "minimum": 1,
                },
                "page": {
                    "type": "integer",
                    "description": "Page offset (0-indexed, default: 0)",
                    "default": 0,
                    "minimum": 0,
                },
            },
            "additionalProperties": False,
            "required": [],
        },
    )


async def handle_call(request: CallToolRequest) -> CallToolResult:
    """Handle the list_notification_rules tool call."""
    try:
        args = request.arguments or {}

        text = args.get("text", "")
        tags = args.get("tags", "")
        recipients = args.get("recipients", "")
        format_type = args.get("format", "table")
        page_size = args.get("page_size", 50)
        page = args.get("page", 0)

        rules = await fetch_notification_rules(
            text=text,
            tags=tags,
            recipients=recipients,
            page_size=page_size,
            page=page,
        )

        if not rules:
            return CallToolResult(
                content=[TextContent(type="text", text="No notification rules found")],
                isError=False,
            )

        if format_type == "json":
            content = json.dumps(rules, indent=2)
        elif format_type == "summary":
            content = f"Found {len(rules)} notification rules"
            if page_size < 1000:
                content += f" (page {page + 1}, showing up to {page_size} per page)"
            if text or tags or recipients:
                filters = []
                if text:
                    filters.append(f"text: '{text}'")
                if tags:
                    filters.append(f"tags: '{tags}'")
                if recipients:
                    filters.append(f"recipients: '{recipients}'")
                content += f" matching filters: {', '.join(filters)}"
        else:
            content = "Datadog Notification Rules"
            filters = []
            if text:
                filters.append(f"text: '{text}'")
            if tags:
                filters.append(f"tags: '{tags}'")
            if recipients:
                filters.append(f"recipients: '{recipients}'")

            if filters:
                content += f" (filtered by: {', '.join(filters)})"
            content += f" | Total: {len(rules)}"
            if page_size < 1000:
                content += f" (page {page + 1}, up to {page_size} per page)"
            content += "\n" + "=" * len(content.split('\n')[-1]) + "\n\n"

            for i, rule in enumerate(rules, 1):
                rule_id = rule.get("id", "unknown")
                attrs = rule.get("attributes", {})
                rule_name = attrs.get("name", "Unnamed")

                filter_obj = attrs.get("filter", {})
                scope = filter_obj.get("scope", "")
                filter_tags = filter_obj.get("tags", [])

                rule_recipients = attrs.get("recipients", [])
                conditional = attrs.get("conditional_recipients", {})

                content += f"{i}. {rule_name}\n"
                content += f"   ID: {rule_id}\n"
                content += f"   Scope: {scope}\n"

                if filter_tags:
                    tags_str = ", ".join(filter_tags[:3])
                    if len(filter_tags) > 3:
                        tags_str += f" (+{len(filter_tags) - 3} more)"
                    content += f"   Tags: {tags_str}\n"

                if rule_recipients:
                    recipients_str = ", ".join(rule_recipients[:3])
                    if len(rule_recipients) > 3:
                        recipients_str += f" (+{len(rule_recipients) - 3} more)"
                    content += f"   Recipients: {recipients_str}\n"

                if conditional:
                    conditions = conditional.get("conditions", [])
                    if conditions:
                        content += f"   Conditional Recipients:\n"
                        for cond in conditions[:2]:
                            cond_scope = cond.get("scope", "")
                            cond_recipients = cond.get("recipients", [])
                            cond_recipients_str = ", ".join(cond_recipients[:2])
                            if len(cond_recipients) > 2:
                                cond_recipients_str += f" (+{len(cond_recipients) - 2})"
                            content += f"     - {cond_scope}: {cond_recipients_str}\n"
                        if len(conditions) > 2:
                            content += f"     (+{len(conditions) - 2} more conditions)\n"

                content += "\n"

        return CallToolResult(
            content=[TextContent(type="text", text=content)],
            isError=False,
        )

    except Exception as e:
        logger.error(f"Error in list_notification_rules: {e}")
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True,
        )
