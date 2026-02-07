"""
Metrics API client for Datadog.

Handles all metrics-related API operations including querying, listing tags, and formulas.
"""

from typing import Any, Dict, List, Optional

from .base_client import DatadogAPIBaseClient


class MetricsClient(DatadogAPIBaseClient):
    """Client for Datadog Metrics API operations."""

    async def get_metrics(
        self,
        metric_name: str,
        aggregation: str = "avg",
        filters: Optional[List[str]] = None,
        group_by: Optional[List[str]] = None,
        time_range: str = "1h",
    ) -> Dict[str, Any]:
        """Get metric data.

        Args:
            metric_name: Metric name to query
            aggregation: Aggregation function (avg, sum, min, max, count)
            filters: Optional list of filter expressions
            group_by: Optional list of fields to group by
            time_range: Time range for the query

        Returns:
            API response containing metric data
        """
        endpoint = self.endpoint_resolver.metrics_data(metric_name)
        builder = self.query_builder(metric_name)

        if aggregation != "avg":
            builder.with_aggregation(aggregation)
        if filters:
            builder.with_filters(filters)
        if group_by:
            builder.with_group_by(*group_by)

        query_str = builder.build()
        params = {
            "query": query_str,
            "time_range": time_range,
        }
        return await self.http_client.get(endpoint, params=params)

    async def list_metrics(self, limit: int = 50) -> Dict[str, Any]:
        """List all available metrics.

        Args:
            limit: Maximum number of metrics to return

        Returns:
            API response containing metrics list
        """
        endpoint = self.endpoint_resolver.metrics_list()
        params = {"limit": limit}
        return await self.http_client.get(endpoint, params=params)

    async def get_metric_tags(self, metric_name: str) -> Dict[str, Any]:
        """Get all tags for a metric.

        Args:
            metric_name: Metric name

        Returns:
            API response containing tags
        """
        endpoint = self.endpoint_resolver.metrics_all_tags(metric_name)
        return await self.http_client.get(endpoint)

    async def get_metric_tag_values(
        self,
        metric_name: str,
        tag_name: str,
    ) -> Dict[str, Any]:
        """Get values for a specific metric tag.

        Args:
            metric_name: Metric name
            tag_name: Tag name

        Returns:
            API response containing tag values
        """
        endpoint = self.endpoint_resolver.metrics_tag_values(metric_name, tag_name)
        return await self.http_client.get(endpoint)

    async def query_metric_formula(
        self,
        formula: str,
        queries: Dict[str, str],
        time_range: str = "1h",
    ) -> Dict[str, Any]:
        """Execute metric formula query.

        Args:
            formula: Formula string (e.g., 'a / b * 100')
            queries: Dict of query variable names to metric queries
            time_range: Time range for the query

        Returns:
            API response containing formula result
        """
        endpoint = self.endpoint_resolver.metrics_query_formula()
        payload = {
            "data": {
                "attributes": {
                    "expression": formula,
                    "queries": queries,
                },
                "type": "timeseries_request",
            },
            "from": int(self.time_converter.to_seconds(time_range)) * 1000,
            "to": 0,  # Current time
        }
        return await self.http_client.post(endpoint, json=payload)
