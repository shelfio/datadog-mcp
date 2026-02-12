"""
Get teams and their members tool
"""

import json
from typing import Any, Dict, List

from mcp.types import CallToolRequest, CallToolResult, Tool, TextContent

from ..utils.datadog_client import fetch_teams, fetch_team_memberships
from ..utils.formatters import (
    extract_team_info,
    extract_membership_info,
    format_teams_as_table,
    format_team_with_members,
)


def get_tool_definition() -> Tool:
    """Get the tool definition for get_teams."""
    return Tool(
        name="get_teams",
        description="Get Datadog teams and their members",
        inputSchema={
            "type": "object",
            "properties": {
                "team_name": {
                    "type": "string",
                    "description": "Specific team name to get details for (optional)",
                },
                "include_members": {
                    "type": "boolean",
                    "description": "Include team member details (default: true)",
                    "default": True,
                },
                "page_size": {
                    "type": "integer",
                    "description": "Number of teams per page (default: 50, max: 100)",
                    "default": 50,
                    "minimum": 1,
                    "maximum": 100,
                },
                "page_number": {
                    "type": "integer",
                    "description": "Page number (0-indexed, default: 0)",
                    "default": 0,
                    "minimum": 0,
                },
                "format": {
                    "type": "string",
                    "description": "Output format",
                    "enum": ["table", "detailed", "json"],
                    "default": "table",
                },
            },
            "additionalProperties": False,
        },
    )


async def handle_call(request: CallToolRequest) -> CallToolResult:
    """Handle the get_teams tool call."""
    try:
        args = request.params.arguments or {}
        
        team_name = args.get("team_name")
        include_members = args.get("include_members", True)
        page_size = args.get("page_size", 50)
        page_number = args.get("page_number", 0)
        format_type = args.get("format", "table")
        
        # Fetch teams with pagination
        teams_response = await fetch_teams(page_size=page_size, page_number=page_number)
        teams_data = teams_response.get("data", [])
        teams = extract_team_info(teams_data)
        
        # Get pagination info
        meta = teams_response.get("meta", {})
        pagination = meta.get("pagination", {})
        
        if not teams:
            return CallToolResult(
                content=[TextContent(type="text", text="No teams found.")],
                isError=False,
            )
        
        # Filter by team name if specified
        if team_name:
            teams = [t for t in teams if team_name.lower() in t.get("name", "").lower()]
            if not teams:
                return CallToolResult(
                    content=[TextContent(type="text", text=f"No teams found matching '{team_name}'.")],
                    isError=False,
                )
        
        # If detailed format or specific team, get members
        if format_type == "detailed" or (team_name and include_members):
            detailed_teams = []
            
            for team in teams:
                team_id = team.get("id")
                if team_id and include_members:
                    try:
                        memberships_data = await fetch_team_memberships(team_id)
                        members = extract_membership_info(memberships_data)
                        
                        team_detail = {
                            "team": team,
                            "members": members,
                        }
                        detailed_teams.append(team_detail)
                    except Exception as e:
                        # Continue with other teams if one fails
                        team_detail = {
                            "team": team,
                            "members": [],
                            "error": str(e),
                        }
                        detailed_teams.append(team_detail)
                else:
                    detailed_teams.append({"team": team, "members": []})
            
            # Format detailed output
            if format_type == "json":
                content = json.dumps(detailed_teams, indent=2)
            else:
                content_parts = []
                for detail in detailed_teams:
                    team_content = format_team_with_members(
                        detail["team"], detail.get("members", [])
                    )
                    if "error" in detail:
                        team_content += f"\n\nError fetching members: {detail['error']}"
                    content_parts.append(team_content)
                
                content = "\n\n" + "="*60 + "\n\n".join([""] + content_parts)
        
        else:
            # Simple table format
            if format_type == "json":
                content = json.dumps(teams, indent=2)
            else:
                content = format_teams_as_table(teams)

        # Add summary header with pagination info (not for JSON format)
        if format_type != "json":
            total_count = pagination.get("total_count", len(teams))
            summary = f"Found {total_count} team(s) total"
            if page_size < total_count:
                summary += f" (showing page {page_number + 1}, {len(teams)} teams)"
            if team_name:
                summary += f" matching '{team_name}'"
            if include_members and format_type != "table":
                summary += " (with member details)"

            # Add pagination info
            if pagination and total_count > page_size:
                total_pages = pagination.get("total_pages", 1)
                current_page = page_number + 1
                summary += f"\nPage {current_page} of {total_pages}"
                if current_page < total_pages:
                    summary += f" | Use page_number={page_number + 1} for next page"

            final_content = f"{summary}\n{'=' * len(summary.split('\n')[0])}\n\n{content}"
        else:
            final_content = content

        return CallToolResult(
            content=[TextContent(type="text", text=final_content)],
            isError=False,
        )
        
    except Exception as e:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True,
        )