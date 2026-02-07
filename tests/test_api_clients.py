"""
Tests for specialized API client modules.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from datadog_mcp.utils.api_clients.base_client import DatadogAPIBaseClient
from datadog_mcp.utils.api_clients.logs_client import LogsClient
from datadog_mcp.utils.api_clients.metrics_client import MetricsClient
from datadog_mcp.utils.api_clients.traces_client import TracesClient
from datadog_mcp.utils.api_clients.monitors_client import MonitorsClient
from datadog_mcp.utils.api_clients.notebooks_client import NotebooksClient
from datadog_mcp.utils.api_clients.services_client import ServicesClient
from datadog_mcp.utils.api_clients.teams_client import TeamsClient
from datadog_mcp.utils.api_clients.misc_client import MiscClient
from datadog_mcp.utils.auth_strategy import TokenAuthStrategy


@pytest.fixture
def mock_auth_strategy():
    """Create mock auth strategy."""
    strategy = AsyncMock(spec=TokenAuthStrategy)
    strategy.get_headers = AsyncMock(
        return_value={
            "DD-API-KEY": "test-key",
            "DD-APPLICATION-KEY": "test-app",
        }
    )
    strategy.get_cookies = MagicMock(return_value=None)
    return strategy


@pytest.fixture
def base_client(mock_auth_strategy):
    """Create base client."""
    return DatadogAPIBaseClient(mock_auth_strategy)


# ============================================================================
# Test Base Client
# ============================================================================


class TestBaseClient:
    """Tests for DatadogAPIBaseClient."""

    def test_initialization(self, base_client):
        """Test base client initialization."""
        assert base_client.http_client is not None
        assert base_client.endpoint_resolver is not None
        assert base_client.query_builder is not None
        assert base_client.time_converter is not None

    def test_has_required_attributes(self, base_client):
        """Test base client has required attributes."""
        assert hasattr(base_client, "http_client")
        assert hasattr(base_client, "endpoint_resolver")
        assert hasattr(base_client, "query_builder")
        assert hasattr(base_client, "time_converter")


# ============================================================================
# Test Logs Client
# ============================================================================


class TestLogsClient:
    """Tests for LogsClient."""

    def test_initialization(self, mock_auth_strategy):
        """Test logs client initialization."""
        client = LogsClient(mock_auth_strategy)
        assert isinstance(client, DatadogAPIBaseClient)
        assert client.http_client is not None

    @pytest.mark.asyncio
    async def test_list_logs(self, mock_auth_strategy):
        """Test listing logs."""
        client = LogsClient(mock_auth_strategy)
        client.http_client.get = AsyncMock(return_value={"logs": []})

        result = await client.list_logs(query="test", limit=100)

        assert result == {"logs": []}
        client.http_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_logs(self, mock_auth_strategy):
        """Test searching logs."""
        client = LogsClient(mock_auth_strategy)
        client.http_client.get = AsyncMock(return_value={"data": []})

        result = await client.search_logs(query="error", limit=50)

        assert result == {"data": []}
        client.http_client.get.assert_called_once()


# ============================================================================
# Test Metrics Client
# ============================================================================


class TestMetricsClient:
    """Tests for MetricsClient."""

    def test_initialization(self, mock_auth_strategy):
        """Test metrics client initialization."""
        client = MetricsClient(mock_auth_strategy)
        assert isinstance(client, DatadogAPIBaseClient)

    @pytest.mark.asyncio
    async def test_get_metrics(self, mock_auth_strategy):
        """Test getting metrics."""
        client = MetricsClient(mock_auth_strategy)
        client.http_client.get = AsyncMock(return_value={"data": []})

        result = await client.get_metrics("system.cpu.user")

        assert result == {"data": []}
        client.http_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_metrics_with_filters(self, mock_auth_strategy):
        """Test getting metrics with filters."""
        client = MetricsClient(mock_auth_strategy)
        client.http_client.get = AsyncMock(return_value={"data": []})

        result = await client.get_metrics(
            "system.cpu.user",
            filters=["host:prod", "env:us-east"],
            group_by=["region"],
        )

        assert result == {"data": []}

    @pytest.mark.asyncio
    async def test_list_metrics(self, mock_auth_strategy):
        """Test listing metrics."""
        client = MetricsClient(mock_auth_strategy)
        client.http_client.get = AsyncMock(return_value={"metrics": []})

        result = await client.list_metrics()

        assert result == {"metrics": []}

    @pytest.mark.asyncio
    async def test_get_metric_tags(self, mock_auth_strategy):
        """Test getting metric tags."""
        client = MetricsClient(mock_auth_strategy)
        client.http_client.get = AsyncMock(return_value={"tags": []})

        result = await client.get_metric_tags("system.cpu.user")

        assert result == {"tags": []}

    @pytest.mark.asyncio
    async def test_get_metric_tag_values(self, mock_auth_strategy):
        """Test getting metric tag values."""
        client = MetricsClient(mock_auth_strategy)
        client.http_client.get = AsyncMock(return_value={"values": []})

        result = await client.get_metric_tag_values("system.cpu.user", "host")

        assert result == {"values": []}

    @pytest.mark.asyncio
    async def test_query_metric_formula(self, mock_auth_strategy):
        """Test querying metric formula."""
        client = MetricsClient(mock_auth_strategy)
        client.http_client.post = AsyncMock(return_value={"result": 0.5})

        result = await client.query_metric_formula(
            "a / b * 100",
            {"a": "avg:requests{*}", "b": "avg:errors{*}"},
        )

        assert result == {"result": 0.5}


# ============================================================================
# Test Traces Client
# ============================================================================


class TestTracesClient:
    """Tests for TracesClient."""

    def test_initialization(self, mock_auth_strategy):
        """Test traces client initialization."""
        client = TracesClient(mock_auth_strategy)
        assert isinstance(client, DatadogAPIBaseClient)

    @pytest.mark.asyncio
    async def test_search_traces(self, mock_auth_strategy):
        """Test searching traces."""
        client = TracesClient(mock_auth_strategy)
        client.http_client.post = AsyncMock(return_value={"traces": []})

        result = await client.search_traces()

        assert result == {"traces": []}
        client.http_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_traces_with_query(self, mock_auth_strategy):
        """Test searching traces with query."""
        client = TracesClient(mock_auth_strategy)
        client.http_client.post = AsyncMock(return_value={"traces": []})

        result = await client.search_traces(query="service:web AND status:error")

        assert result == {"traces": []}

    @pytest.mark.asyncio
    async def test_aggregate_traces(self, mock_auth_strategy):
        """Test aggregating traces."""
        client = TracesClient(mock_auth_strategy)
        client.http_client.post = AsyncMock(return_value={"aggregates": []})

        result = await client.aggregate_traces(group_by=["service.name"])

        assert result == {"aggregates": []}

    @pytest.mark.asyncio
    async def test_get_trace_with_children(self, mock_auth_strategy):
        """Test getting trace with children."""
        client = TracesClient(mock_auth_strategy)
        client.http_client.get = AsyncMock(return_value={"trace": {}})

        result = await client.get_trace_with_children("abc123def456")

        assert result == {"trace": {}}


# ============================================================================
# Test Monitors Client
# ============================================================================


class TestMonitorsClient:
    """Tests for MonitorsClient."""

    def test_initialization(self, mock_auth_strategy):
        """Test monitors client initialization."""
        client = MonitorsClient(mock_auth_strategy)
        assert isinstance(client, DatadogAPIBaseClient)

    @pytest.mark.asyncio
    async def test_list_monitors(self, mock_auth_strategy):
        """Test listing monitors."""
        client = MonitorsClient(mock_auth_strategy)
        client.http_client.get = AsyncMock(return_value=[])

        result = await client.list_monitors()

        assert result == []

    @pytest.mark.asyncio
    async def test_get_monitor(self, mock_auth_strategy):
        """Test getting monitor."""
        client = MonitorsClient(mock_auth_strategy)
        client.http_client.get = AsyncMock(return_value={"id": 123})

        result = await client.get_monitor(123)

        assert result == {"id": 123}

    @pytest.mark.asyncio
    async def test_create_monitor(self, mock_auth_strategy):
        """Test creating monitor."""
        client = MonitorsClient(mock_auth_strategy)
        client.http_client.post = AsyncMock(return_value={"id": 123})

        result = await client.create_monitor(
            "metric alert",
            "avg:system.cpu{*}",
            "CPU Alert",
            "Alert on high CPU",
        )

        assert result == {"id": 123}

    @pytest.mark.asyncio
    async def test_update_monitor(self, mock_auth_strategy):
        """Test updating monitor."""
        client = MonitorsClient(mock_auth_strategy)
        client.http_client.put = AsyncMock(return_value={"id": 123, "name": "Updated"})

        result = await client.update_monitor(123, name="Updated")

        assert result == {"id": 123, "name": "Updated"}

    @pytest.mark.asyncio
    async def test_delete_monitor(self, mock_auth_strategy):
        """Test deleting monitor."""
        client = MonitorsClient(mock_auth_strategy)
        client.http_client.delete = AsyncMock(return_value=None)

        result = await client.delete_monitor(123)

        assert result is None


# ============================================================================
# Test Notebooks Client
# ============================================================================


class TestNotebooksClient:
    """Tests for NotebooksClient."""

    def test_initialization(self, mock_auth_strategy):
        """Test notebooks client initialization."""
        client = NotebooksClient(mock_auth_strategy)
        assert isinstance(client, DatadogAPIBaseClient)

    @pytest.mark.asyncio
    async def test_list_notebooks(self, mock_auth_strategy):
        """Test listing notebooks."""
        client = NotebooksClient(mock_auth_strategy)
        client.http_client.get = AsyncMock(return_value={"notebooks": []})

        result = await client.list_notebooks()

        assert result == {"notebooks": []}

    @pytest.mark.asyncio
    async def test_get_notebook(self, mock_auth_strategy):
        """Test getting notebook."""
        client = NotebooksClient(mock_auth_strategy)
        client.http_client.get = AsyncMock(return_value={"id": 456})

        result = await client.get_notebook(456)

        assert result == {"id": 456}

    @pytest.mark.asyncio
    async def test_create_notebook(self, mock_auth_strategy):
        """Test creating notebook."""
        client = NotebooksClient(mock_auth_strategy)
        client.http_client.post = AsyncMock(return_value={"id": 456})

        result = await client.create_notebook("My Notebook", "# Title")

        assert result == {"id": 456}

    @pytest.mark.asyncio
    async def test_update_notebook(self, mock_auth_strategy):
        """Test updating notebook."""
        client = NotebooksClient(mock_auth_strategy)
        client.http_client.put = AsyncMock(return_value={"id": 456})

        result = await client.update_notebook(456, name="Updated")

        assert result == {"id": 456}

    @pytest.mark.asyncio
    async def test_delete_notebook(self, mock_auth_strategy):
        """Test deleting notebook."""
        client = NotebooksClient(mock_auth_strategy)
        client.http_client.delete = AsyncMock(return_value=None)

        result = await client.delete_notebook(456)

        assert result is None


# ============================================================================
# Test Services Client
# ============================================================================


class TestServicesClient:
    """Tests for ServicesClient."""

    def test_initialization(self, mock_auth_strategy):
        """Test services client initialization."""
        client = ServicesClient(mock_auth_strategy)
        assert isinstance(client, DatadogAPIBaseClient)

    @pytest.mark.asyncio
    async def test_list_service_definitions(self, mock_auth_strategy):
        """Test listing service definitions."""
        client = ServicesClient(mock_auth_strategy)
        client.http_client.get = AsyncMock(return_value={"services": []})

        result = await client.list_service_definitions()

        assert result == {"services": []}

    @pytest.mark.asyncio
    async def test_get_service_definition(self, mock_auth_strategy):
        """Test getting service definition."""
        client = ServicesClient(mock_auth_strategy)
        client.http_client.get = AsyncMock(return_value={"name": "my-service"})

        result = await client.get_service_definition("my-service")

        assert result == {"name": "my-service"}

    @pytest.mark.asyncio
    async def test_get_service_definition_custom_version(self, mock_auth_strategy):
        """Test getting service definition with custom version."""
        client = ServicesClient(mock_auth_strategy)
        client.http_client.get = AsyncMock(return_value={"name": "my-service"})

        result = await client.get_service_definition("my-service", schema_version="v2")

        assert result == {"name": "my-service"}


# ============================================================================
# Test Teams Client
# ============================================================================


class TestTeamsClient:
    """Tests for TeamsClient."""

    def test_initialization(self, mock_auth_strategy):
        """Test teams client initialization."""
        client = TeamsClient(mock_auth_strategy)
        assert isinstance(client, DatadogAPIBaseClient)

    @pytest.mark.asyncio
    async def test_list_teams(self, mock_auth_strategy):
        """Test listing teams."""
        client = TeamsClient(mock_auth_strategy)
        client.http_client.get = AsyncMock(return_value={"teams": []})

        result = await client.list_teams()

        assert result == {"teams": []}

    @pytest.mark.asyncio
    async def test_list_team_members(self, mock_auth_strategy):
        """Test listing team members."""
        client = TeamsClient(mock_auth_strategy)
        client.http_client.get = AsyncMock(return_value={"members": []})

        result = await client.list_team_members(789)

        assert result == {"members": []}


# ============================================================================
# Test Misc Client
# ============================================================================


class TestMiscClient:
    """Tests for MiscClient."""

    def test_initialization(self, mock_auth_strategy):
        """Test misc client initialization."""
        client = MiscClient(mock_auth_strategy)
        assert isinstance(client, DatadogAPIBaseClient)

    @pytest.mark.asyncio
    async def test_list_slos(self, mock_auth_strategy):
        """Test listing SLOs."""
        client = MiscClient(mock_auth_strategy)
        client.http_client.get = AsyncMock(return_value={"slos": []})

        result = await client.list_slos()

        assert result == {"slos": []}

    @pytest.mark.asyncio
    async def test_get_slo(self, mock_auth_strategy):
        """Test getting SLO."""
        client = MiscClient(mock_auth_strategy)
        client.http_client.get = AsyncMock(return_value={"id": "slo123"})

        result = await client.get_slo("slo123")

        assert result == {"id": "slo123"}

    @pytest.mark.asyncio
    async def test_get_org_info(self, mock_auth_strategy):
        """Test getting organization info."""
        client = MiscClient(mock_auth_strategy)
        client.http_client.get = AsyncMock(return_value={"org": {}})

        result = await client.get_org_info()

        assert result == {"org": {}}
