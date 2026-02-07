"""
Datadog API client modules organized by domain.

Each client module handles a specific domain of the Datadog API:
- logs_client: Logs API endpoints
- metrics_client: Metrics API endpoints
- traces_client: Traces/APM API endpoints
- monitors_client: Monitor management API endpoints
- notebooks_client: Notebook management API endpoints
- services_client: Service definitions API endpoints
- teams_client: Teams API endpoints
- misc_client: Miscellaneous endpoints (org info, SLOs, etc.)

All clients inherit from DatadogAPIBaseClient and use the unified HTTP client
and authentication strategy pattern for consistency.
"""

from .base_client import DatadogAPIBaseClient

__all__ = ["DatadogAPIBaseClient"]
