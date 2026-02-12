"""
Pytest configuration and shared fixtures
"""

import pytest
import os
from unittest.mock import patch, MagicMock, AsyncMock


@pytest.fixture
def mock_env_credentials():
    """Mock environment with valid Datadog credentials"""
    with patch.dict(os.environ, {"DD_API_KEY": "test_key", "DD_APP_KEY": "test_app"}):
        yield


@pytest.fixture(autouse=True)
def auto_mock_credentials():
    """Automatically mock credentials for all tests that need them"""
    # Mock AWS Secrets Manager to prevent real AWS calls during tests
    with patch('datadog_mcp.utils.secrets_provider.is_aws_secrets_configured', return_value=False), \
         patch.dict(os.environ, {"DD_API_KEY": "test_key", "DD_APP_KEY": "test_app"}):
        yield


@pytest.fixture
def mock_httpx_client():
    """Mock httpx client for API calls"""
    with patch('datadog_mcp.utils.datadog_client.httpx.AsyncClient') as mock_client:
        # Setup default successful response with synchronous methods
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": []}
        mock_response.raise_for_status.return_value = None
        mock_response.status_code = 200

        # Create async mocks for post and get that return the response when awaited
        # These are the HTTP methods that need to be awaitable
        async_post = AsyncMock(return_value=mock_response)
        async_get = AsyncMock(return_value=mock_response)

        # Setup the async context manager __aenter__ to return a client with async methods
        mock_client_instance = MagicMock()
        mock_client_instance.get = async_get
        mock_client_instance.post = async_post

        mock_client.return_value.__aenter__.return_value = mock_client_instance
        mock_client.return_value.__aexit__.return_value = None

        yield mock_client


@pytest.fixture
def sample_request():
    """Create a sample request object with proper structure for handlers"""
    class RequestParams:
        """Container for request parameters that maintains argument references"""
        def __init__(self):
            self.arguments = {}

    class SampleRequest:
        """Mock request object matching CallToolRequest structure"""
        def __init__(self):
            self.arguments = {}
            self.params = RequestParams()

        def __setattr__(self, name, value):
            if name == "arguments":
                # When tests set request.arguments, also update request.params.arguments
                super().__setattr__(name, value)
                if hasattr(self, "params"):
                    self.params.arguments = value
            else:
                super().__setattr__(name, value)

    return SampleRequest()


@pytest.fixture
def sample_logs_data():
    """Sample logs data for testing"""
    return [
        {
            "timestamp": "2023-01-01T12:00:00Z",
            "message": "Test log message",
            "service": "test-service",
            "status": "info",
            "host": "test-host"
        },
        {
            "timestamp": "2023-01-01T12:01:00Z", 
            "message": "Error occurred",
            "service": "test-service",
            "status": "error",
            "host": "test-host"
        }
    ]


@pytest.fixture
def sample_metrics_data():
    """Sample metrics data for testing"""
    return {
        "data": {
            "attributes": {
                "series": [
                    {
                        "metric": "system.cpu.user",
                        "points": [
                            [1640995200000, 25.5],
                            [1640995260000, 30.2]
                        ],
                        "tags": ["host:web-01", "env:prod"]
                    }
                ]
            }
        }
    }


@pytest.fixture
def sample_teams_data():
    """Sample teams data for testing"""
    return {
        "teams": [
            {
                "id": "team-123",
                "name": "Backend Team",
                "handle": "backend-team",
                "description": "Backend development team"
            }
        ],
        "users": [
            {
                "id": "user-1",
                "name": "John Doe",
                "email": "john@example.com",
                "teams": ["team-123"]
            }
        ]
    }