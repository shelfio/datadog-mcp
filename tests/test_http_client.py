"""
Tests for HTTP client module.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from datadog_mcp.utils.auth_strategy import TokenAuthStrategy
from datadog_mcp.utils.http_client import DatadogHTTPClient


@pytest.fixture
def mock_auth_strategy():
    """Create mock auth strategy."""
    strategy = AsyncMock(spec=TokenAuthStrategy)
    strategy.get_headers = AsyncMock(
        return_value={
            "DD-API-KEY": "test-key",
            "DD-APPLICATION-KEY": "test-app",
            "Content-Type": "application/json",
        }
    )
    strategy.get_cookies = MagicMock(return_value=None)
    return strategy


@pytest.fixture
def http_client(mock_auth_strategy):
    """Create HTTP client with mock auth."""
    return DatadogHTTPClient(mock_auth_strategy)


# ============================================================================
# Test GET Requests
# ============================================================================


class TestGetRequests:
    """Tests for GET request functionality."""

    @pytest.mark.asyncio
    async def test_get_success(self, http_client, mock_auth_strategy):
        """Test successful GET request."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": "test"}

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            result = await http_client.get("https://api.example.com/test")

            assert result == {"data": "test"}
            mock_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_with_params(self, http_client, mock_auth_strategy):
        """Test GET request with query parameters."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": "test"}

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            result = await http_client.get(
                "https://api.example.com/test", params={"foo": "bar"}
            )

            assert result == {"data": "test"}
            call_kwargs = mock_client.get.call_args[1]
            assert call_kwargs["params"] == {"foo": "bar"}

    @pytest.mark.asyncio
    async def test_get_error_response(self, http_client, mock_auth_strategy):
        """Test GET request with error response."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_response.text = "Not found"
            mock_response.json.side_effect = Exception("No JSON")

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            with pytest.raises(ValueError, match="404"):
                await http_client.get("https://api.example.com/test")


# ============================================================================
# Test POST Requests
# ============================================================================


class TestPostRequests:
    """Tests for POST request functionality."""

    @pytest.mark.asyncio
    async def test_post_success(self, http_client, mock_auth_strategy):
        """Test successful POST request."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.status_code = 201
            mock_response.json.return_value = {"id": "123"}

            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            payload = {"name": "test"}
            result = await http_client.post(
                "https://api.example.com/test", json=payload
            )

            assert result == {"id": "123"}
            call_kwargs = mock_client.post.call_args[1]
            assert call_kwargs["json"] == payload

    @pytest.mark.asyncio
    async def test_post_with_custom_status(self, http_client, mock_auth_strategy):
        """Test POST request with custom expected status codes."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.status_code = 202
            mock_response.json.return_value = {"accepted": True}

            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            result = await http_client.post(
                "https://api.example.com/test",
                json={},
                expected_status=(202,),
            )

            assert result == {"accepted": True}

    @pytest.mark.asyncio
    async def test_post_error_with_json_error(self, http_client, mock_auth_strategy):
        """Test POST request with JSON error response."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.status_code = 400
            mock_response.text = "Bad request"
            mock_response.json.return_value = {"error": {"message": "Invalid input"}}

            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            with pytest.raises(ValueError, match="Invalid input"):
                await http_client.post("https://api.example.com/test", json={})


# ============================================================================
# Test DELETE Requests
# ============================================================================


class TestDeleteRequests:
    """Tests for DELETE request functionality."""

    @pytest.mark.asyncio
    async def test_delete_with_content(self, http_client, mock_auth_strategy):
        """Test DELETE request with response content."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.content = b'{"deleted": true}'
            mock_response.json.return_value = {"deleted": True}

            mock_client = AsyncMock()
            mock_client.delete = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            result = await http_client.delete("https://api.example.com/test/123")

            assert result == {"deleted": True}

    @pytest.mark.asyncio
    async def test_delete_no_content(self, http_client, mock_auth_strategy):
        """Test DELETE request with 204 No Content."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.status_code = 204
            mock_response.content = b""

            mock_client = AsyncMock()
            mock_client.delete = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            result = await http_client.delete("https://api.example.com/test/123")

            assert result is None


# ============================================================================
# Test PATCH Requests
# ============================================================================


class TestPatchRequests:
    """Tests for PATCH request functionality."""

    @pytest.mark.asyncio
    async def test_patch_success(self, http_client, mock_auth_strategy):
        """Test successful PATCH request."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"updated": True}

            mock_client = AsyncMock()
            mock_client.patch = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            result = await http_client.patch(
                "https://api.example.com/test/123", json={"name": "updated"}
            )

            assert result == {"updated": True}


# ============================================================================
# Test PUT Requests
# ============================================================================


class TestPutRequests:
    """Tests for PUT request functionality."""

    @pytest.mark.asyncio
    async def test_put_success(self, http_client, mock_auth_strategy):
        """Test successful PUT request."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"replaced": True}

            mock_client = AsyncMock()
            mock_client.put = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            result = await http_client.put(
                "https://api.example.com/test/123", json={"name": "replaced"}
            )

            assert result == {"replaced": True}


# ============================================================================
# Test Error Handling
# ============================================================================


class TestErrorHandling:
    """Tests for error handling and response validation."""

    def test_get_status_name(self, http_client):
        """Test status code name mapping."""
        assert http_client._get_status_name(400) == "Bad Request"
        assert http_client._get_status_name(401) == "Unauthorized"
        assert http_client._get_status_name(403) == "Forbidden"
        assert http_client._get_status_name(404) == "Not Found"
        assert http_client._get_status_name(999) == "Error"

    def test_check_response_success(self, http_client):
        """Test response validation for success."""
        mock_response = MagicMock()
        mock_response.status_code = 200

        # Should not raise
        http_client._check_response(mock_response, (200,))

    def test_check_response_multiple_valid(self, http_client):
        """Test response validation with multiple valid codes."""
        mock_response = MagicMock()
        mock_response.status_code = 201

        # Should not raise
        http_client._check_response(mock_response, (200, 201))

    def test_check_response_error_with_json_error_msg(self, http_client):
        """Test response validation with JSON error message."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad request"
        mock_response.json.return_value = {"error": {"message": "Invalid input"}}

        with pytest.raises(ValueError, match="Invalid input"):
            http_client._check_response(mock_response, (200,))

    def test_check_response_error_with_errors_list(self, http_client):
        """Test response validation with errors list."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad request"
        mock_response.json.return_value = {"errors": ["Error 1", "Error 2"]}

        with pytest.raises(ValueError, match="Error 1"):
            http_client._check_response(mock_response, (200,))

    def test_check_response_error_no_json(self, http_client):
        """Test response validation without JSON."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not found"
        mock_response.json.side_effect = Exception("No JSON")

        with pytest.raises(ValueError, match="Not found"):
            http_client._check_response(mock_response, (200,))


# ============================================================================
# Test Authentication Integration
# ============================================================================


class TestAuthenticationIntegration:
    """Tests for authentication strategy integration."""

    @pytest.mark.asyncio
    async def test_headers_from_strategy(self, http_client, mock_auth_strategy):
        """Test that headers are fetched from auth strategy."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {}

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            await http_client.get("https://api.example.com/test")

            mock_auth_strategy.get_headers.assert_called_once()

    @pytest.mark.asyncio
    async def test_cookies_from_strategy(self, http_client, mock_auth_strategy):
        """Test that cookies are fetched from auth strategy."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {}

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            await http_client.get("https://api.example.com/test")

            mock_auth_strategy.get_cookies.assert_called_once()
