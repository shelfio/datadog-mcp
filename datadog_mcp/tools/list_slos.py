"""
List SLOs tool
"""

import json
import logging
from typing import Any, Dict

from mcp.types import CallToolRequest, CallToolResult, Tool, TextContent

logger = logging.getLogger(__name__)

from ..utils.datadog_client import fetch_slos


def get_tool_definition() -> Tool:
    """Get the tool definition for list_slos."""
    return Tool(
        name="list_slos",
        description="List Service Level Objectives (SLOs) from Datadog. SLOs define service level targets and track performance against those targets.",
        inputSchema={
            "type": "object",
            "properties": {
                "tags": {
                    "type": "string",
                    "description": "Filter SLOs by tags (e.g., 'team:backend,env:prod'). Leave empty to list all SLOs.",
                    "default": "",
                },
                "query": {
                    "type": "string", 
                    "description": "Filter SLOs by name or description (substring match). Leave empty to include all SLOs.",
                    "default": "",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of SLOs to return (default: 50, max: 1000)",
                    "default": 50,
                    "minimum": 1,
                    "maximum": 1000,
                },
                "offset": {
                    "type": "integer",
                    "description": "Number of SLOs to skip (default: 0)",
                    "default": 0,
                    "minimum": 0,
                },
                "format": {
                    "type": "string",
                    "description": "Output format",
                    "enum": ["table", "json", "summary"],
                    "default": "table",
                },
            },
            "additionalProperties": False,
            "required": [],
        },
    )


async def handle_call(request: CallToolRequest) -> CallToolResult:
    """Handle the list_slos tool call."""
    try:
        args = request.params.arguments or {}
        
        tags = args.get("tags", "")
        query = args.get("query", "")
        limit = args.get("limit", 50)
        offset = args.get("offset", 0)
        format_type = args.get("format", "table")
        
        # Fetch SLOs list
        slos = await fetch_slos(
            tags=tags if tags else None,
            query=query if query else None,
            limit=limit,
            offset=offset
        )
        
        if not slos:
            return CallToolResult(
                content=[TextContent(type="text", text="No SLOs found")],
                isError=False,
            )
        
        # Format output
        if format_type == "json":
            content = json.dumps(slos, indent=2)
        elif format_type == "summary":
            content = f"Found {len(slos)} SLOs"
            if limit < 1000 or offset > 0:
                page_info = []
                if offset > 0:
                    page_info.append(f"offset {offset}")
                if limit < 1000:
                    page_info.append(f"limit {limit}")
                content += f" ({', '.join(page_info)})"
            if tags or query:
                filters = []
                if tags:
                    filters.append(f"tags: '{tags}'")
                if query:
                    filters.append(f"query: '{query}'")
                content += f" matching filters: {', '.join(filters)}"
            
            # Group by type and status
            by_type = {}
            by_status = {}
            targets = []
            
            for slo in slos:
                slo_type = slo.get("type", "unknown")
                
                by_type[slo_type] = by_type.get(slo_type, 0) + 1
                
                # Get SLO status from thresholds
                thresholds = slo.get("thresholds", [])
                if thresholds:
                    for threshold in thresholds:
                        target = threshold.get("target")
                        if target:
                            targets.append(target)
                            warning = threshold.get("warning")
                            if warning and target:
                                if target >= warning:
                                    status = "healthy"
                                else:
                                    status = "warning"
                            else:
                                status = "unknown"
                            by_status[status] = by_status.get(status, 0) + 1
                            break
            
            content += "\n\nBy Type:"
            for type_name, count in sorted(by_type.items()):
                content += f"\n  {type_name}: {count}"
            
            if by_status:
                content += "\n\nBy Status:"
                for status, count in sorted(by_status.items()):
                    content += f"\n  {status}: {count}"
            
            if targets:
                avg_target = sum(targets) / len(targets)
                content += f"\n\nAverage Target: {avg_target:.2%}"
            
        else:  # table format
            content = f"Datadog SLOs"
            filters = []
            if tags:
                filters.append(f"tags: '{tags}'")
            if query:
                filters.append(f"query: '{query}'")
            
            if filters:
                content += f" (filtered by: {', '.join(filters)})"
            content += f" | Total: {len(slos)}"
            if limit < 1000 or offset > 0:
                page_info = []
                if offset > 0:
                    page_info.append(f"offset {offset}")
                if limit < 1000:
                    page_info.append(f"limit {limit}")
                content += f" ({', '.join(page_info)})"
            content += "\n" + "=" * len(content.split('\n')[-1]) + "\n\n"
            
            for i, slo in enumerate(slos, 1):
                slo_id = slo.get("id", "unknown")
                slo_name = slo.get("name", "Unnamed")
                slo_type = slo.get("type", "unknown")
                
                # Get target from thresholds
                thresholds = slo.get("thresholds", [])
                target_str = "N/A"
                warning_str = ""
                if thresholds:
                    for threshold in thresholds:
                        target = threshold.get("target")
                        warning = threshold.get("warning")
                        if target is not None:
                            target_str = f"{target:.2%}"
                            if warning is not None:
                                warning_str = f" (warn: {warning:.2%})"
                            break
                
                # Get tags if available
                slo_tags = slo.get("tags", [])
                tags_str = ", ".join(slo_tags[:3])  # Show first 3 tags
                if len(slo_tags) > 3:
                    tags_str += f" (+{len(slo_tags) - 3} more)"
                
                # Get description
                description = slo.get("description", "")
                desc_str = f" - {description[:50]}..." if len(description) > 50 else f" - {description}" if description else ""
                
                content += f"{i:3d}. {slo_name}{desc_str}\n"
                content += f"     ID: {slo_id} | Type: {slo_type} | Target: {target_str}{warning_str}"
                if tags_str:
                    content += f"\n     Tags: {tags_str}"
                content += "\n\n"
        
        return CallToolResult(
            content=[TextContent(type="text", text=content)],
            isError=False,
        )
        
    except Exception as e:
        logger.error(f"Error in list_slos: {e}")
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True,
        )