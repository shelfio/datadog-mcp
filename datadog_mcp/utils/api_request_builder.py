"""
API request builders for constructing Datadog queries and resolving endpoints.

Provides clean abstractions for building metric queries in Datadog's query syntax,
managing API endpoints, and eliminating string concatenation boilerplate.
"""

from typing import List, Optional, Union


class QueryBuilder:
    """Builds Datadog metric queries in proper syntax.

    Datadog metric query format:
    - Simple: `avg:system.cpu{host:prod}`
    - Aggregated: `avg:system.cpu{host:prod} by {region}`
    - Multiple aggregations: `avg:system.cpu{host:prod} by {region,env}`
    """

    def __init__(self, metric_name: str):
        """Initialize query builder.

        Args:
            metric_name: Datadog metric name (e.g., 'system.cpu.user')
        """
        self.metric_name = metric_name
        self.aggregation = "avg"
        self.filters: List[str] = []
        self.by_fields: List[str] = []

    def with_aggregation(self, agg: str) -> "QueryBuilder":
        """Set aggregation function.

        Args:
            agg: Aggregation function (avg, min, max, sum, count)

        Returns:
            Self for method chaining
        """
        valid_aggs = ("avg", "min", "max", "sum", "count")
        if agg not in valid_aggs:
            raise ValueError(f"Invalid aggregation: {agg}. Must be one of {valid_aggs}")
        self.aggregation = agg
        return self

    def with_filter(self, filter_expr: str) -> "QueryBuilder":
        """Add a filter expression.

        Args:
            filter_expr: Filter expression (e.g., 'host:prod' or 'env:us-*')

        Returns:
            Self for method chaining
        """
        if filter_expr:
            self.filters.append(filter_expr)
        return self

    def with_filters(self, filters: List[str]) -> "QueryBuilder":
        """Add multiple filter expressions.

        Args:
            filters: List of filter expressions

        Returns:
            Self for method chaining
        """
        self.filters.extend([f for f in filters if f])
        return self

    def with_group_by(self, *fields: str) -> "QueryBuilder":
        """Add grouping fields.

        Args:
            *fields: Field names to group by (e.g., 'host', 'region', 'env')

        Returns:
            Self for method chaining
        """
        self.by_fields.extend(fields)
        return self

    def with_group_by_list(self, fields: List[str]) -> "QueryBuilder":
        """Add grouping fields from a list.

        Args:
            fields: List of field names to group by

        Returns:
            Self for method chaining
        """
        self.by_fields.extend(fields)
        return self

    def build(self) -> str:
        """Build final query string.

        Returns:
            Datadog metric query string

        Example:
            "avg:system.cpu{host:prod,env:us-east} by {region,instance}"
        """
        # Start with aggregation and metric
        query = f"{self.aggregation}:{self.metric_name}"

        # Add filters if any
        if self.filters:
            filters_str = ",".join(self.filters)
            query += "{" + filters_str + "}"

        # Add grouping if any
        if self.by_fields:
            by_str = ",".join(self.by_fields)
            query += " by {" + by_str + "}"

        return query

    def reset(self) -> "QueryBuilder":
        """Reset builder to initial state.

        Returns:
            Self for method chaining
        """
        self.aggregation = "avg"
        self.filters = []
        self.by_fields = []
        return self


class EndpointResolver:
    """Resolves correct Datadog API endpoints.

    Datadog has multiple API versions and endpoint structures.
    This class centralizes endpoint management.
    """

    # Base URLs
    API_V1_BASE = "https://api.datadoghq.com/api"
    API_V2_BASE = "https://api.datadoghq.com/api/v2"
    INTERNAL_API_BASE = "https://app.datadoghq.com/api"

    # ========================================================================
    # Logs API Endpoints
    # ========================================================================

    @staticmethod
    def logs_list_v2() -> str:
        """Get logs list endpoint (v2 API)."""
        return f"{EndpointResolver.API_V2_BASE}/logs/events/search"

    @staticmethod
    def logs_analytics_v1() -> str:
        """Get logs analytics endpoint (v1 internal API)."""
        return f"{EndpointResolver.INTERNAL_API_BASE}/v1/logs-analytics/list"

    # ========================================================================
    # Metrics API Endpoints
    # ========================================================================

    @staticmethod
    def metrics_data(metric_name: str) -> str:
        """Get metric data endpoint."""
        return f"{EndpointResolver.API_V2_BASE}/metrics/{metric_name}/data"

    @staticmethod
    def metrics_all_tags(metric_name: str) -> str:
        """Get all tags for a metric."""
        return f"{EndpointResolver.API_V2_BASE}/metrics/{metric_name}/all-tags"

    @staticmethod
    def metrics_tag_values(metric_name: str, tag_name: str) -> str:
        """Get values for a specific metric tag."""
        return f"{EndpointResolver.API_V2_BASE}/metrics/{metric_name}/tags/{tag_name}"

    @staticmethod
    def metrics_list() -> str:
        """Get list of all metrics."""
        return f"{EndpointResolver.API_V2_BASE}/metrics"

    @staticmethod
    def metrics_query_formula() -> str:
        """Get metrics query formula endpoint (for formula calculations)."""
        return f"{EndpointResolver.API_V2_BASE}/query/timeseries"

    # ========================================================================
    # Monitors API Endpoints
    # ========================================================================

    @staticmethod
    def monitors_list() -> str:
        """Get list of monitors endpoint."""
        return f"{EndpointResolver.API_V1_BASE}/monitor"

    @staticmethod
    def monitor_get(monitor_id: Union[str, int]) -> str:
        """Get specific monitor endpoint."""
        return f"{EndpointResolver.API_V1_BASE}/monitor/{monitor_id}"

    @staticmethod
    def monitor_create() -> str:
        """Create monitor endpoint."""
        return f"{EndpointResolver.API_V1_BASE}/monitor"

    @staticmethod
    def monitor_update(monitor_id: Union[str, int]) -> str:
        """Update monitor endpoint."""
        return f"{EndpointResolver.API_V1_BASE}/monitor/{monitor_id}"

    @staticmethod
    def monitor_delete(monitor_id: Union[str, int]) -> str:
        """Delete monitor endpoint."""
        return f"{EndpointResolver.API_V1_BASE}/monitor/{monitor_id}"

    # ========================================================================
    # SLO API Endpoints
    # ========================================================================

    @staticmethod
    def slos_list() -> str:
        """Get SLOs list endpoint."""
        return f"{EndpointResolver.API_V1_BASE}/slo"

    @staticmethod
    def slo_get(slo_id: str) -> str:
        """Get specific SLO endpoint."""
        return f"{EndpointResolver.API_V1_BASE}/slo/{slo_id}"

    # ========================================================================
    # Notebooks API Endpoints
    # ========================================================================

    @staticmethod
    def notebooks_list() -> str:
        """Get notebooks list endpoint."""
        return f"{EndpointResolver.API_V2_BASE}/notebooks"

    @staticmethod
    def notebook_get(notebook_id: Union[str, int]) -> str:
        """Get specific notebook endpoint."""
        return f"{EndpointResolver.API_V2_BASE}/notebooks/{notebook_id}"

    @staticmethod
    def notebook_create() -> str:
        """Create notebook endpoint."""
        return f"{EndpointResolver.API_V2_BASE}/notebooks"

    @staticmethod
    def notebook_update(notebook_id: Union[str, int]) -> str:
        """Update notebook endpoint."""
        return f"{EndpointResolver.API_V2_BASE}/notebooks/{notebook_id}"

    @staticmethod
    def notebook_delete(notebook_id: Union[str, int]) -> str:
        """Delete notebook endpoint."""
        return f"{EndpointResolver.API_V2_BASE}/notebooks/{notebook_id}"

    # ========================================================================
    # Services API Endpoints
    # ========================================================================

    @staticmethod
    def service_definitions_list() -> str:
        """Get service definitions list endpoint."""
        return f"{EndpointResolver.API_V2_BASE}/service_definitions"

    @staticmethod
    def service_definition_get(service_name: str, schema_version: str = "v2.2") -> str:
        """Get service definition endpoint."""
        return f"{EndpointResolver.API_V2_BASE}/service_definitions/{schema_version}/{service_name}"

    # ========================================================================
    # Teams API Endpoints
    # ========================================================================

    @staticmethod
    def teams_list() -> str:
        """Get teams list endpoint."""
        return f"{EndpointResolver.API_V2_BASE}/teams"

    @staticmethod
    def team_members_list(team_id: Union[str, int]) -> str:
        """Get team members endpoint."""
        return f"{EndpointResolver.API_V2_BASE}/teams/{team_id}/members"

    # ========================================================================
    # Traces/APM API Endpoints
    # ========================================================================

    @staticmethod
    def traces_search() -> str:
        """Get traces search endpoint."""
        return f"{EndpointResolver.API_V2_BASE}/traces/search"

    @staticmethod
    def traces_aggregate() -> str:
        """Get traces aggregate endpoint."""
        return f"{EndpointResolver.API_V2_BASE}/traces/aggregate/search"

    @staticmethod
    def traces_with_children(trace_id: str) -> str:
        """Get trace with children endpoint."""
        return f"{EndpointResolver.API_V2_BASE}/traces/{trace_id}"

    # ========================================================================
    # Authentication API Endpoints
    # ========================================================================

    @staticmethod
    def org_info() -> str:
        """Get organization info endpoint (for CSRF token renewal)."""
        return f"{EndpointResolver.INTERNAL_API_BASE}/v1/org"

    # ========================================================================
    # Helper Methods
    # ========================================================================

    @staticmethod
    def get_api_url_for_endpoint(endpoint: str) -> str:
        """Extract base URL from endpoint.

        Args:
            endpoint: Full endpoint URL

        Returns:
            Base URL (https://api.datadoghq.com or https://app.datadoghq.com)
        """
        if endpoint.startswith(EndpointResolver.INTERNAL_API_BASE):
            return "https://app.datadoghq.com"
        elif endpoint.startswith(EndpointResolver.API_V2_BASE):
            return "https://api.datadoghq.com"
        elif endpoint.startswith(EndpointResolver.API_V1_BASE):
            return "https://api.datadoghq.com"
        else:
            return "https://api.datadoghq.com"  # Default fallback

    @staticmethod
    def uses_internal_api(endpoint: str) -> bool:
        """Check if endpoint uses internal API (cookie auth).

        Args:
            endpoint: Full endpoint URL

        Returns:
            True if endpoint requires cookie auth (internal API)
        """
        return endpoint.startswith(EndpointResolver.INTERNAL_API_BASE)


# ============================================================================
# Time Range Utilities
# ============================================================================


class TimeRangeConverter:
    """Converts time range strings to seconds and ISO timestamps."""

    TIME_RANGE_TO_SECONDS = {
        "1h": 3600,
        "4h": 14400,
        "8h": 28800,
        "1d": 86400,
        "7d": 604800,
        "14d": 1209600,
        "30d": 2592000,
    }

    @staticmethod
    def to_seconds(time_range: str) -> int:
        """Convert time range string to seconds.

        Args:
            time_range: Time range string (e.g., '1h', '7d')

        Returns:
            Number of seconds

        Raises:
            ValueError: If time range format is invalid
        """
        if time_range not in TimeRangeConverter.TIME_RANGE_TO_SECONDS:
            valid = ", ".join(TimeRangeConverter.TIME_RANGE_TO_SECONDS.keys())
            raise ValueError(
                f"Invalid time range: {time_range}. Must be one of: {valid}"
            )
        return TimeRangeConverter.TIME_RANGE_TO_SECONDS[time_range]

    @staticmethod
    def validate_time_range(time_range: str) -> bool:
        """Check if time range string is valid.

        Args:
            time_range: Time range string to validate

        Returns:
            True if valid, False otherwise
        """
        return time_range in TimeRangeConverter.TIME_RANGE_TO_SECONDS
