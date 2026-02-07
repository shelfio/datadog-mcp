"""
Base client for all Datadog API clients.

Provides unified HTTP client, endpoint resolution, and query building
for consistent request handling across all API domains.
"""

from datadog_mcp.utils.auth_strategy import AuthStrategy
from datadog_mcp.utils.http_client import DatadogHTTPClient
from datadog_mcp.utils.api_request_builder import (
    EndpointResolver,
    QueryBuilder,
    TimeRangeConverter,
)


class DatadogAPIBaseClient:
    """Base client for Datadog API operations.

    Provides unified HTTP client access, endpoint management, and query builders
    for all specialized API clients (logs, metrics, traces, etc.).

    Attributes:
        http_client: Unified HTTP client with authentication
        endpoint_resolver: Centralized endpoint management
        query_builder: Query builder for metric queries
        time_converter: Time range conversion utilities
    """

    def __init__(self, auth_strategy: AuthStrategy):
        """Initialize base client with authentication strategy.

        Args:
            auth_strategy: Authentication strategy (token or cookie)
        """
        self.http_client = DatadogHTTPClient(auth_strategy)
        self.endpoint_resolver = EndpointResolver
        self.query_builder = QueryBuilder
        self.time_converter = TimeRangeConverter
