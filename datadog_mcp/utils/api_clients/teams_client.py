"""
Teams API client for Datadog.

Handles all teams-related API operations including listing teams and team members.
"""

from typing import Any, Dict, Optional, Union

from .base_client import DatadogAPIBaseClient


class TeamsClient(DatadogAPIBaseClient):
    """Client for Datadog Teams API operations."""

    async def list_teams(self, limit: int = 50) -> Dict[str, Any]:
        """List all teams.

        Args:
            limit: Maximum number of teams to return

        Returns:
            API response containing teams list
        """
        endpoint = self.endpoint_resolver.teams_list()
        params = {"limit": limit}
        return await self.http_client.get(endpoint, params=params)

    async def list_team_members(
        self,
        team_id: Union[str, int],
        limit: int = 50,
    ) -> Dict[str, Any]:
        """List members of a team.

        Args:
            team_id: Team ID
            limit: Maximum number of members to return

        Returns:
            API response containing team members
        """
        endpoint = self.endpoint_resolver.team_members_list(team_id)
        params = {"limit": limit}
        return await self.http_client.get(endpoint, params=params)
