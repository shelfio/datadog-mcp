"""
Traces/APM API client for Datadog.

Handles all traces and APM-related API operations including searching and aggregating traces.
"""

from typing import Any, Dict, List, Optional

from .base_client import DatadogAPIBaseClient


class TracesClient(DatadogAPIBaseClient):
    """Client for Datadog Traces/APM API operations."""

    async def search_traces(
        self,
        query: str = "*",
        limit: int = 10,
        time_range: str = "1h",
    ) -> Dict[str, Any]:
        """Search traces with optional query.

        Args:
            query: Trace search query
            limit: Maximum number of traces to return
            time_range: Time range to search

        Returns:
            API response containing traces
        """
        endpoint = self.endpoint_resolver.traces_search()
        seconds = self.time_converter.to_seconds(time_range)
        payload = {
            "filter": {
                "from": -seconds * 1000,
                "to": 0,
                "query": query,
            },
            "options": {
                "apm_stats": False,
            },
            "page": {
                "limit": limit,
            },
        }
        return await self.http_client.post(endpoint, json=payload)

    async def aggregate_traces(
        self,
        query: str = "*",
        group_by: Optional[List[str]] = None,
        time_range: str = "1h",
    ) -> Dict[str, Any]:
        """Aggregate traces by specified dimensions.

        Args:
            query: Trace search query
            group_by: Fields to group aggregation by
            time_range: Time range to aggregate

        Returns:
            API response containing aggregated trace data
        """
        endpoint = self.endpoint_resolver.traces_aggregate()
        seconds = self.time_converter.to_seconds(time_range)

        compute = [
            {
                "aggregation": "count",
                "metric": "@duration",
            }
        ]
        group_bys = [{"facet": field} for field in (group_by or [])]

        payload = {
            "filter": {
                "from": -seconds * 1000,
                "to": 0,
                "query": query,
            },
            "compute": compute,
            "group_by": group_bys,
        }
        return await self.http_client.post(endpoint, json=payload)

    async def get_trace_with_children(
        self,
        trace_id: str,
    ) -> Dict[str, Any]:
        """Get trace with all child spans.

        Args:
            trace_id: Trace ID to retrieve

        Returns:
            API response containing trace with children
        """
        endpoint = self.endpoint_resolver.traces_with_children(trace_id)
        return await self.http_client.get(endpoint)
