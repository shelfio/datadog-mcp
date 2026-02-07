"""
Monitors API client for Datadog.

Handles all monitor management operations including creation, update, deletion, and listing.
"""

from typing import Any, Dict, List, Optional, Union

from .base_client import DatadogAPIBaseClient


class MonitorsClient(DatadogAPIBaseClient):
    """Client for Datadog Monitors API operations."""

    async def list_monitors(
        self,
        limit: int = 50,
        tags: Optional[List[str]] = None,
        monitor_tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """List all monitors.

        Args:
            limit: Maximum number of monitors to return
            tags: Filter by tags
            monitor_tags: Filter by monitor tags

        Returns:
            API response containing monitors list
        """
        endpoint = self.endpoint_resolver.monitors_list()
        params = {"page_size": limit}

        if tags:
            params["filter"] = ",".join(tags)
        if monitor_tags:
            params["monitor_tags"] = ",".join(monitor_tags)

        return await self.http_client.get(endpoint, params=params)

    async def get_monitor(self, monitor_id: Union[str, int]) -> Dict[str, Any]:
        """Get specific monitor by ID.

        Args:
            monitor_id: Monitor ID

        Returns:
            API response containing monitor details
        """
        endpoint = self.endpoint_resolver.monitor_get(monitor_id)
        return await self.http_client.get(endpoint)

    async def create_monitor(
        self,
        monitor_type: str,
        query: str,
        name: str,
        message: str,
        tags: Optional[List[str]] = None,
        thresholds: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create a new monitor.

        Args:
            monitor_type: Type of monitor (e.g., 'metric alert', 'log alert')
            query: Monitor query
            name: Monitor name
            message: Alert message
            tags: Optional monitor tags
            thresholds: Optional threshold configuration

        Returns:
            API response containing created monitor
        """
        endpoint = self.endpoint_resolver.monitor_create()
        payload = {
            "type": monitor_type,
            "query": query,
            "name": name,
            "message": message,
        }

        if tags:
            payload["tags"] = tags
        if thresholds:
            payload["thresholds"] = thresholds

        return await self.http_client.post(
            endpoint, json=payload, expected_status=(200, 201)
        )

    async def update_monitor(
        self,
        monitor_id: Union[str, int],
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Update existing monitor.

        Args:
            monitor_id: Monitor ID to update
            **kwargs: Fields to update (name, query, message, thresholds, tags, etc.)

        Returns:
            API response containing updated monitor
        """
        endpoint = self.endpoint_resolver.monitor_update(monitor_id)
        return await self.http_client.put(endpoint, json=kwargs)

    async def delete_monitor(self, monitor_id: Union[str, int]) -> Optional[Dict[str, Any]]:
        """Delete a monitor.

        Args:
            monitor_id: Monitor ID to delete

        Returns:
            API response (typically empty on success)
        """
        endpoint = self.endpoint_resolver.monitor_delete(monitor_id)
        return await self.http_client.delete(endpoint)
