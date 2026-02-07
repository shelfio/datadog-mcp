"""
Logs API client for Datadog.

Handles all logs-related API operations including searching, listing, and analytics.
"""

from typing import Any, Dict, Optional

from .base_client import DatadogAPIBaseClient


class LogsClient(DatadogAPIBaseClient):
    """Client for Datadog Logs API operations."""

    async def list_logs(
        self,
        query: str = "*",
        limit: int = 50,
        time_range: str = "1h",
    ) -> Dict[str, Any]:
        """List logs matching query.

        Args:
            query: Search query string
            limit: Maximum number of logs to return
            time_range: Time range (1h, 4h, 8h, 1d, 7d, 14d, 30d)

        Returns:
            API response containing logs
        """
        endpoint = self.endpoint_resolver.logs_list_v2()
        params = {
            "filter[query]": query,
            "page[limit]": limit,
        }
        return await self.http_client.get(endpoint, params=params)

    async def search_logs(
        self,
        query: str,
        limit: int = 50,
        time_range: str = "1h",
    ) -> Dict[str, Any]:
        """Search logs with custom query.

        Args:
            query: Search query string
            limit: Maximum number of results
            time_range: Time range to search

        Returns:
            API response containing search results
        """
        return await self.list_logs(query=query, limit=limit, time_range=time_range)
