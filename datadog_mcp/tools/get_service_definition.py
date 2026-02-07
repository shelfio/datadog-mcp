"""
Get service definition tool
"""

import json
import logging
from typing import Any, Dict

from mcp.types import CallToolRequest, CallToolResult, Tool, TextContent

logger = logging.getLogger(__name__)

from ..utils.datadog_client import fetch_service_definition


def get_tool_definition() -> Tool:
    """Get the tool definition for get_service_definition."""
    return Tool(
        name="get_service_definition",
        description="Retrieve the definition of a specific service from Datadog. Service definitions contain metadata, ownership, and configuration details for individual services.",
        inputSchema={
            "type": "object",
            "properties": {
                "service_name": {
                    "type": "string",
                    "description": "Name of the service to retrieve the definition for",
                },
                "schema_version": {
                    "type": "string",
                    "description": "Schema version to retrieve",
                    "enum": ["v1", "v2", "v2.1", "v2.2"],
                    "default": "v2.2",
                },
                "format": {
                    "type": "string",
                    "description": "Output format",
                    "enum": ["formatted", "json", "yaml"],
                    "default": "formatted",
                },
            },
            "additionalProperties": False,
            "required": ["service_name"],
        },
    )


async def handle_call(request: CallToolRequest) -> CallToolResult:
    """Handle the get_service_definition tool call."""
    try:
        args = request.params.arguments or {}
        
        service_name = args.get("service_name")
        if not service_name:
            return CallToolResult(
                content=[TextContent(type="text", text="Error: service_name is required")],
                isError=True,
            )
        
        schema_version = args.get("schema_version", "v2.2")
        format_type = args.get("format", "formatted")
        
        # Fetch service definition
        service_definition_response = await fetch_service_definition(
            service_name=service_name,
            schema_version=schema_version
        )
        
        if "data" not in service_definition_response:
            return CallToolResult(
                content=[TextContent(type="text", text=f"No service definition found for '{service_name}'")],
                isError=True,
            )
        
        service_definition = service_definition_response["data"]
        
        # Format output
        if format_type == "json":
            content = json.dumps(service_definition_response, indent=2)
        elif format_type == "yaml":
            try:
                import yaml
                content = yaml.dump(service_definition_response, default_flow_style=False, indent=2)
            except ImportError:
                content = "YAML format requires pyyaml package. Showing JSON instead:\n\n"
                content += json.dumps(service_definition_response, indent=2)
        else:  # formatted
            attributes = service_definition.get("attributes", {})
            service_info = attributes.get("service", {})
            
            content = f"Service Definition: {service_name}\n"
            content += "=" * (len(content) - 1) + "\n\n"
            
            # Basic info
            content += f"Schema Version: {attributes.get('schema-version', 'unknown')}\n"
            content += f"Service Name: {service_info.get('name', 'unknown')}\n"
            
            # Description
            if "description" in service_info:
                content += f"Description: {service_info['description']}\n"
            
            # Team and contacts
            if "team" in service_info:
                content += f"Team: {service_info['team']}\n"
            
            if "contacts" in service_info:
                contacts = service_info["contacts"]
                if contacts:
                    content += f"Contacts:\n"
                    for contact in contacts:
                        contact_type = contact.get("type", "unknown")
                        contact_name = contact.get("name", "unknown")
                        contact_contact = contact.get("contact", "")
                        content += f"  - {contact_type}: {contact_name}"
                        if contact_contact:
                            content += f" ({contact_contact})"
                        content += "\n"
            
            # Links
            if "links" in service_info:
                links = service_info["links"]
                if links:
                    content += f"Links:\n"
                    for link in links:
                        link_name = link.get("name", "unknown")
                        link_type = link.get("type", "unknown")
                        link_url = link.get("url", "")
                        content += f"  - {link_name} ({link_type}): {link_url}\n"
            
            # Technologies
            if "languages" in service_info:
                languages = service_info["languages"]
                if languages:
                    content += f"Languages: {', '.join(languages)}\n"
            
            if "type" in service_info:
                content += f"Type: {service_info['type']}\n"
            
            # Tags
            if "tags" in service_info:
                tags = service_info["tags"]
                if tags:
                    content += f"Tags: {', '.join(tags)}\n"
            
            # Integrations
            if "integrations" in service_info:
                integrations = service_info["integrations"]
                if integrations:
                    content += f"\nIntegrations:\n"
                    for integration_type, integration_config in integrations.items():
                        content += f"  {integration_type}:\n"
                        if isinstance(integration_config, dict):
                            for key, value in integration_config.items():
                                content += f"    {key}: {value}\n"
                        else:
                            content += f"    {integration_config}\n"
            
            # Application info
            if "application" in attributes:
                app_info = attributes["application"]
                content += f"\nApplication:\n"
                for key, value in app_info.items():
                    if isinstance(value, (list, dict)):
                        content += f"  {key}: {json.dumps(value, indent=2)}\n"
                    else:
                        content += f"  {key}: {value}\n"
            
            # Extensions
            if "extensions" in service_info:
                extensions = service_info["extensions"]
                if extensions:
                    content += f"\nExtensions:\n"
                    for ext_key, ext_value in extensions.items():
                        if isinstance(ext_value, (list, dict)):
                            content += f"  {ext_key}: {json.dumps(ext_value, indent=2)}\n"
                        else:
                            content += f"  {ext_key}: {ext_value}\n"
        
        return CallToolResult(
            content=[TextContent(type="text", text=content)],
            isError=False,
        )
        
    except Exception as e:
        logger.error(f"Error in get_service_definition: {e}")
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True,
        )