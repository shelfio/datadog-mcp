"""
Tests for API request builder module.
"""

import pytest

from datadog_mcp.utils.api_request_builder import (
    EndpointResolver,
    QueryBuilder,
    TimeRangeConverter,
)


# ============================================================================
# Test Query Builder
# ============================================================================


class TestQueryBuilder:
    """Tests for QueryBuilder class."""

    def test_simple_query(self):
        """Test building simple query."""
        query = QueryBuilder("system.cpu.user").build()
        assert query == "avg:system.cpu.user"

    def test_query_with_aggregation(self):
        """Test building query with custom aggregation."""
        query = (
            QueryBuilder("system.cpu.user")
            .with_aggregation("max")
            .build()
        )
        assert query == "max:system.cpu.user"

    def test_query_with_single_filter(self):
        """Test building query with single filter."""
        query = (
            QueryBuilder("system.cpu.user")
            .with_filter("host:prod")
            .build()
        )
        assert query == "avg:system.cpu.user{host:prod}"

    def test_query_with_multiple_filters(self):
        """Test building query with multiple filters."""
        query = (
            QueryBuilder("system.cpu.user")
            .with_filter("host:prod")
            .with_filter("env:us-east")
            .build()
        )
        assert query == "avg:system.cpu.user{host:prod,env:us-east}"

    def test_query_with_filter_list(self):
        """Test building query with filter list."""
        query = (
            QueryBuilder("system.cpu.user")
            .with_filters(["host:prod", "env:us-east"])
            .build()
        )
        assert query == "avg:system.cpu.user{host:prod,env:us-east}"

    def test_query_with_single_group_by(self):
        """Test building query with single grouping."""
        query = (
            QueryBuilder("system.cpu.user")
            .with_group_by("host")
            .build()
        )
        assert query == "avg:system.cpu.user by {host}"

    def test_query_with_multiple_group_by(self):
        """Test building query with multiple grouping."""
        query = (
            QueryBuilder("system.cpu.user")
            .with_group_by("host", "region")
            .build()
        )
        assert query == "avg:system.cpu.user by {host,region}"

    def test_query_with_group_by_list(self):
        """Test building query with grouping list."""
        query = (
            QueryBuilder("system.cpu.user")
            .with_group_by_list(["host", "region"])
            .build()
        )
        assert query == "avg:system.cpu.user by {host,region}"

    def test_complete_query(self):
        """Test building complete query with all components."""
        query = (
            QueryBuilder("system.cpu.user")
            .with_aggregation("sum")
            .with_filters(["host:prod", "env:*"])
            .with_group_by("region", "instance")
            .build()
        )
        assert query == "sum:system.cpu.user{host:prod,env:*} by {region,instance}"

    def test_invalid_aggregation(self):
        """Test error on invalid aggregation."""
        with pytest.raises(ValueError, match="Invalid aggregation"):
            QueryBuilder("system.cpu.user").with_aggregation("invalid").build()

    def test_reset(self):
        """Test resetting builder."""
        builder = QueryBuilder("system.cpu.user")
        builder.with_aggregation("max").with_filter("host:prod")

        builder.reset()
        query = builder.build()

        assert query == "avg:system.cpu.user"

    def test_method_chaining(self):
        """Test that all methods return self for chaining."""
        builder = QueryBuilder("test.metric")
        result = builder.with_aggregation("max").with_filter("a:b").with_group_by("x")

        assert result is builder


# ============================================================================
# Test Endpoint Resolver
# ============================================================================


class TestEndpointResolver:
    """Tests for EndpointResolver class."""

    def test_logs_list_v2(self):
        """Test logs list v2 endpoint."""
        endpoint = EndpointResolver.logs_list_v2()
        assert "api/v2" in endpoint
        assert "logs" in endpoint

    def test_logs_analytics_v1(self):
        """Test logs analytics v1 endpoint."""
        endpoint = EndpointResolver.logs_analytics_v1()
        assert "app.datadoghq.com" in endpoint
        assert "v1" in endpoint

    def test_metrics_data(self):
        """Test metrics data endpoint."""
        endpoint = EndpointResolver.metrics_data("system.cpu")
        assert "system.cpu" in endpoint
        assert "data" in endpoint

    def test_metrics_all_tags(self):
        """Test metrics all tags endpoint."""
        endpoint = EndpointResolver.metrics_all_tags("system.cpu")
        assert "system.cpu" in endpoint
        assert "all-tags" in endpoint

    def test_metrics_tag_values(self):
        """Test metrics tag values endpoint."""
        endpoint = EndpointResolver.metrics_tag_values("system.cpu", "host")
        assert "system.cpu" in endpoint
        assert "host" in endpoint

    def test_metrics_list(self):
        """Test metrics list endpoint."""
        endpoint = EndpointResolver.metrics_list()
        assert "v2" in endpoint
        assert "metrics" in endpoint

    def test_monitors_list(self):
        """Test monitors list endpoint."""
        endpoint = EndpointResolver.monitors_list()
        assert "monitor" in endpoint

    def test_monitor_get(self):
        """Test monitor get endpoint."""
        endpoint = EndpointResolver.monitor_get(12345)
        assert "12345" in endpoint

    def test_monitor_create(self):
        """Test monitor create endpoint."""
        endpoint = EndpointResolver.monitor_create()
        assert "monitor" in endpoint

    def test_notebooks_list(self):
        """Test notebooks list endpoint."""
        endpoint = EndpointResolver.notebooks_list()
        assert "v2" in endpoint
        assert "notebooks" in endpoint

    def test_notebook_get(self):
        """Test notebook get endpoint."""
        endpoint = EndpointResolver.notebook_get(456)
        assert "456" in endpoint

    def test_slos_list(self):
        """Test SLOs list endpoint."""
        endpoint = EndpointResolver.slos_list()
        assert "slo" in endpoint

    def test_traces_search(self):
        """Test traces search endpoint."""
        endpoint = EndpointResolver.traces_search()
        assert "traces" in endpoint
        assert "search" in endpoint

    def test_traces_aggregate(self):
        """Test traces aggregate endpoint."""
        endpoint = EndpointResolver.traces_aggregate()
        assert "traces" in endpoint
        assert "aggregate" in endpoint

    def test_org_info(self):
        """Test org info endpoint."""
        endpoint = EndpointResolver.org_info()
        assert "org" in endpoint

    def test_get_api_url_for_v2_endpoint(self):
        """Test extracting API URL from v2 endpoint."""
        endpoint = EndpointResolver.metrics_data("test")
        url = EndpointResolver.get_api_url_for_endpoint(endpoint)
        assert url == "https://api.datadoghq.com"

    def test_get_api_url_for_internal_endpoint(self):
        """Test extracting API URL from internal endpoint."""
        endpoint = EndpointResolver.logs_analytics_v1()
        url = EndpointResolver.get_api_url_for_endpoint(endpoint)
        assert url == "https://app.datadoghq.com"

    def test_uses_internal_api_true(self):
        """Test detecting internal API endpoints."""
        endpoint = EndpointResolver.logs_analytics_v1()
        assert EndpointResolver.uses_internal_api(endpoint) is True

    def test_uses_internal_api_false(self):
        """Test detecting public API endpoints."""
        endpoint = EndpointResolver.logs_list_v2()
        assert EndpointResolver.uses_internal_api(endpoint) is False

    def test_service_definition_get(self):
        """Test service definition get endpoint."""
        endpoint = EndpointResolver.service_definition_get("my-service")
        assert "my-service" in endpoint
        assert "v2.2" in endpoint  # Default schema version

    def test_service_definition_get_custom_version(self):
        """Test service definition get endpoint with custom version."""
        endpoint = EndpointResolver.service_definition_get(
            "my-service", schema_version="v2"
        )
        assert "my-service" in endpoint
        assert "v2" in endpoint


# ============================================================================
# Test Time Range Converter
# ============================================================================


class TestTimeRangeConverter:
    """Tests for TimeRangeConverter class."""

    def test_to_seconds_1h(self):
        """Test converting 1 hour to seconds."""
        assert TimeRangeConverter.to_seconds("1h") == 3600

    def test_to_seconds_1d(self):
        """Test converting 1 day to seconds."""
        assert TimeRangeConverter.to_seconds("1d") == 86400

    def test_to_seconds_7d(self):
        """Test converting 7 days to seconds."""
        assert TimeRangeConverter.to_seconds("7d") == 604800

    def test_to_seconds_30d(self):
        """Test converting 30 days to seconds."""
        assert TimeRangeConverter.to_seconds("30d") == 2592000

    def test_invalid_time_range(self):
        """Test error on invalid time range."""
        with pytest.raises(ValueError, match="Invalid time range"):
            TimeRangeConverter.to_seconds("2w")

    def test_validate_time_range_valid(self):
        """Test validating valid time range."""
        assert TimeRangeConverter.validate_time_range("1h") is True
        assert TimeRangeConverter.validate_time_range("7d") is True

    def test_validate_time_range_invalid(self):
        """Test validating invalid time range."""
        assert TimeRangeConverter.validate_time_range("2w") is False
        assert TimeRangeConverter.validate_time_range("invalid") is False

    def test_all_time_ranges_have_seconds(self):
        """Test that all time range strings have corresponding seconds."""
        for time_range in TimeRangeConverter.TIME_RANGE_TO_SECONDS.keys():
            seconds = TimeRangeConverter.to_seconds(time_range)
            assert seconds > 0
