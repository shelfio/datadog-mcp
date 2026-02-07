"""
List service definitions tool
"""

import json
import logging
from typing import Any, Dict

from mcp.types import CallToolRequest, CallToolResult, Tool, TextContent

logger = logging.getLogger(__name__)

from ..utils.datadog_client import fetch_service_definitions


def get_tool_definition() -> Tool:
    """Get the tool definition for list_service_definitions."""
    return Tool(
        name="list_service_definitions",
        description="List all service definitions from Datadog. Service definitions describe the structure, ownership, and metadata of services in your organization.",
        inputSchema={
            "type": "object",
            "properties": {
                "page_size": {
                    "type": "integer",
                    "description": "Number of service definitions to return per page",
                    "minimum": 1,
                    "maximum": 100,
                    "default": 10,
                },
                "page_number": {
                    "type": "integer", 
                    "description": "Page number for pagination (0-indexed)",
                    "minimum": 0,
                    "default": 0,
                },
                "schema_version": {
                    "type": "string",
                    "description": "Filter by schema version (e.g., 'v2', 'v2.1', 'v2.2')",
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
    """Handle the list_service_definitions tool call."""
    try:
        args = request.params.arguments or {}
        
        page_size = args.get("page_size", 10)
        page_number = args.get("page_number", 0)
        schema_version = args.get("schema_version")
        format_type = args.get("format", "table")
        
        # Fetch service definitions
        service_definitions_response = await fetch_service_definitions(
            page_size=page_size,
            page_number=page_number,
            schema_version=schema_version
        )
        
        if "data" not in service_definitions_response:
            return CallToolResult(
                content=[TextContent(type="text", text="No service definitions data returned from API")],
                isError=True,
            )
        
        service_definitions = service_definitions_response["data"]
        meta = service_definitions_response.get("meta", {})
        
        # Format output
        if format_type == "json":
            content = json.dumps(service_definitions_response, indent=2)
        elif format_type == "summary":
            total_count = meta.get("pagination", {}).get("total_count", len(service_definitions))
            content = f"Found {total_count} service definitions"
            if schema_version:
                content += f" with schema version: '{schema_version}'"
            content += f"\n\nShowing page {page_number + 1} ({len(service_definitions)} definitions):\n"
            for i, definition in enumerate(service_definitions):
                attributes = definition.get("attributes", {})
                service_name = attributes.get("service", {}).get("name", "unknown")
                schema_ver = attributes.get("schema-version", "unknown")
                content += f"{i+1:2d}. {service_name} (schema: {schema_ver})\n"
        else:  # table format
            total_count = meta.get("pagination", {}).get("total_count", len(service_definitions))
            content = f"Datadog Service Definitions"
            if schema_version:
                content += f" (schema: {schema_version})"
            content += f" | Total: {total_count}"
            content += f" | Page: {page_number + 1} ({len(service_definitions)} shown)"
            content += "\n" + "=" * len(content.split('\n')[-1]) + "\n\n"
            
            if service_definitions:
                # Table headers
                content += f"{'#':<3} {'Service Name':<30} {'Schema':<8} {'Team':<20} {'Language':<12}\n"
                content += "-" * 76 + "\n"
                
                for i, definition in enumerate(service_definitions, 1):
                    attributes = definition.get("attributes", {})
                    service_info = attributes.get("service", {})
                    
                    service_name = service_info.get("name", "unknown")[:29]
                    schema_ver = attributes.get("schema-version", "unknown")[:7]
                    
                    # Try to get team info
                    team = ""
                    if "team" in service_info:
                        team = service_info["team"][:19]
                    elif "contacts" in service_info:
                        contacts = service_info["contacts"]
                        if contacts and len(contacts) > 0:
                            team = contacts[0].get("name", "")[:19]
                    
                    # Try to get language info
                    language = ""
                    if "languages" in service_info:
                        languages = service_info["languages"]
                        if languages:
                            language = languages[0][:11]
                    
                    content += f"{i:<3} {service_name:<30} {schema_ver:<8} {team:<20} {language:<12}\n"
                
                # Pagination info
                pagination = meta.get("pagination", {})
                if pagination:
                    current_page = page_number + 1
                    total_pages = pagination.get("total_pages", 1)
                    content += f"\nPage {current_page} of {total_pages}"
                    if current_page < total_pages:
                        content += f" | Use page_number={page_number + 1} for next page"
            else:
                content += "No service definitions found"
                if schema_version:
                    content += f" with schema version: '{schema_version}'"
        
        return CallToolResult(
            content=[TextContent(type="text", text=content)],
            isError=False,
        )
        
    except Exception as e:
        logger.error(f"Error in list_service_definitions: {e}")
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True,
        )