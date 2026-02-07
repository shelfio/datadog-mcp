"""
Miscellaneous API client for Datadog.

Handles various API operations that don't fit into other specialized clients,
including SLOs, organization info, and other endpoints.
"""

from typing import Any, Dict, Optional

from .base_client import DatadogAPIBaseClient


class MiscClient(DatadogAPIBaseClient):
    """Client for miscellaneous Datadog API operations."""

    async def list_slos(self, limit: int = 50) -> Dict[str, Any]:
        """List all SLOs.

        Args:
            limit: Maximum number of SLOs to return

        Returns:
            API response containing SLOs list
        """
        endpoint = self.endpoint_resolver.slos_list()
        params = {"limit": limit}
        return await self.http_client.get(endpoint, params=params)

    async def get_slo(self, slo_id: str) -> Dict[str, Any]:
        """Get specific SLO by ID.

        Args:
            slo_id: SLO ID

        Returns:
            API response containing SLO details
        """
        endpoint = self.endpoint_resolver.slo_get(slo_id)
        return await self.http_client.get(endpoint)

    async def get_org_info(self) -> Dict[str, Any]:
        """Get organization information.

        Returns:
            API response containing organization info
        """
        endpoint = self.endpoint_resolver.org_info()
        return await self.http_client.get(endpoint)
