"""
Tests for authentication strategy module.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from datadog_mcp.utils.auth_strategy import (
    AuthStrategyFactory,
    CookieAuthStrategy,
    TokenAuthStrategy,
    format_cookie_header,
    get_api_key,
    get_app_key,
    get_cookie,
    get_csrf_token,
)


# ============================================================================
# Test Cookie Header Formatting
# ============================================================================


class TestFormatCookieHeader:
    """Tests for format_cookie_header function."""

    def test_raw_token_format(self):
        """Test formatting raw hex token."""
        result = format_cookie_header("c9829ab768105289702a99")
        assert result == "dogweb=c9829ab768105289702a99"

    def test_already_named_format(self):
        """Test formatting already-named cookie."""
        result = format_cookie_header("dogweb=c9829ab768105289702a99")
        assert result == "dogweb=c9829ab768105289702a99"

    def test_netscape_format(self):
        """Test formatting Netscape jar format."""
        netscape = "dogweb\t.datadoghq.com\t/\tTRUE\t1735689600\tdogweb\tc9829ab768105289702a99"
        result = format_cookie_header(netscape)
        assert result == "dogweb=c9829ab768105289702a99"

    def test_empty_string(self):
        """Test formatting empty string."""
        result = format_cookie_header("")
        assert result == ""

    def test_whitespace_only(self):
        """Test formatting whitespace-only string."""
        result = format_cookie_header("   ")
        assert result == ""


# ============================================================================
# Test Credential Loading (Mocked File I/O)
# ============================================================================


class TestCredentialLoading:
    """Tests for credential loading functions."""

    @patch.dict(os.environ, {"DD_API_KEY": "test-api-key"})
    def test_get_api_key_from_env(self):
        """Test getting API key from environment variable."""
        result = get_api_key()
        assert result == "test-api-key"

    @patch.dict(os.environ, {"DD_API_KEY": ""})
    @patch("datadog_mcp.utils.auth_strategy.os.path.isfile", return_value=False)
    def test_get_api_key_not_available(self, mock_isfile):
        """Test API key returns None when not available."""
        result = get_api_key()
        assert result is None

    @patch.dict(os.environ, {"DD_APP_KEY": "test-app-key"})
    def test_get_app_key_from_env(self):
        """Test getting app key from environment variable."""
        result = get_app_key()
        assert result == "test-app-key"

    @patch.dict(os.environ, {"DD_COOKIE": "dogweb=test-cookie"})
    def test_get_cookie_from_env(self):
        """Test getting cookie from environment variable."""
        result = get_cookie()
        assert result == "dogweb=test-cookie"

    @patch.dict(os.environ, {"DD_CSRF_TOKEN": "test-csrf-token"})
    def test_get_csrf_token_from_env(self):
        """Test getting CSRF token from environment variable."""
        result = get_csrf_token()
        assert result == "test-csrf-token"


# ============================================================================
# Test Token Authentication Strategy
# ============================================================================


class TestTokenAuthStrategy:
    """Tests for TokenAuthStrategy."""

    @pytest.mark.asyncio
    @patch("datadog_mcp.utils.auth_strategy.get_api_key", return_value="test-api-key")
    @patch("datadog_mcp.utils.auth_strategy.get_app_key", return_value="test-app-key")
    async def test_get_headers(self, mock_app_key, mock_api_key):
        """Test getting authentication headers."""
        strategy = TokenAuthStrategy()
        headers = await strategy.get_headers()

        assert headers["DD-API-KEY"] == "test-api-key"
        assert headers["DD-APPLICATION-KEY"] == "test-app-key"
        assert headers["Content-Type"] == "application/json"

    @pytest.mark.asyncio
    @patch("datadog_mcp.utils.auth_strategy.get_api_key", return_value=None)
    async def test_get_headers_missing_api_key(self, mock_api_key):
        """Test headers raise error when API key missing."""
        strategy = TokenAuthStrategy()
        with pytest.raises(ValueError, match="TokenAuthStrategy requires"):
            await strategy.get_headers()

    def test_get_cookies(self):
        """Test that token auth returns no cookies."""
        strategy = TokenAuthStrategy()
        assert strategy.get_cookies() is None

    def test_get_api_url(self):
        """Test that token auth uses public API URL."""
        strategy = TokenAuthStrategy()
        assert strategy.get_api_url() == "https://api.datadoghq.com"

    def test_name(self):
        """Test strategy name."""
        strategy = TokenAuthStrategy()
        assert strategy.name == "token"


# ============================================================================
# Test Cookie Authentication Strategy
# ============================================================================


class TestCookieAuthStrategy:
    """Tests for CookieAuthStrategy."""

    @pytest.mark.asyncio
    @patch("datadog_mcp.utils.auth_strategy.get_csrf_token", return_value="test-csrf")
    async def test_get_headers(self, mock_csrf):
        """Test getting authentication headers."""
        strategy = CookieAuthStrategy()
        headers = await strategy.get_headers()

        assert headers["x-csrf-token"] == "test-csrf"
        assert headers["Content-Type"] == "application/json"

    @pytest.mark.asyncio
    @patch("datadog_mcp.utils.auth_strategy.get_csrf_token", return_value=None)
    async def test_get_headers_missing_csrf(self, mock_csrf):
        """Test headers raise error when CSRF token missing."""
        strategy = CookieAuthStrategy()
        with pytest.raises(ValueError, match="CookieAuthStrategy requires"):
            await strategy.get_headers()

    @patch("datadog_mcp.utils.auth_strategy.get_cookie", return_value="dogweb=test-value")
    def test_get_cookies(self, mock_cookie):
        """Test getting cookies."""
        strategy = CookieAuthStrategy()
        cookies = strategy.get_cookies()

        assert cookies == {"dogweb": "test-value"}

    @patch("datadog_mcp.utils.auth_strategy.get_cookie", return_value=None)
    def test_get_cookies_missing(self, mock_cookie):
        """Test cookies raise error when missing."""
        strategy = CookieAuthStrategy()
        with pytest.raises(ValueError, match="CookieAuthStrategy requires"):
            strategy.get_cookies()

    def test_get_api_url(self):
        """Test that cookie auth uses internal API URL."""
        strategy = CookieAuthStrategy()
        assert strategy.get_api_url() == "https://app.datadoghq.com"

    def test_name(self):
        """Test strategy name."""
        strategy = CookieAuthStrategy()
        assert strategy.name == "cookie"


# ============================================================================
# Test Auth Strategy Factory
# ============================================================================


class TestAuthStrategyFactory:
    """Tests for AuthStrategyFactory."""

    @pytest.mark.asyncio
    @patch("datadog_mcp.utils.auth_strategy.FORCE_AUTH_METHOD", "token")
    @patch("datadog_mcp.utils.auth_strategy.get_api_key", return_value="test-key")
    @patch("datadog_mcp.utils.auth_strategy.get_app_key", return_value="test-app")
    async def test_get_strategy_forced_token(self, mock_app, mock_key):
        """Test getting forced token strategy."""
        strategy = await AuthStrategyFactory.get_strategy()
        assert isinstance(strategy, TokenAuthStrategy)

    @pytest.mark.asyncio
    @patch("datadog_mcp.utils.auth_strategy.FORCE_AUTH_METHOD", "cookie")
    @patch("datadog_mcp.utils.auth_strategy.get_cookie", return_value="dogweb=test")
    async def test_get_strategy_forced_cookie(self, mock_cookie):
        """Test getting forced cookie strategy."""
        strategy = await AuthStrategyFactory.get_strategy()
        assert isinstance(strategy, CookieAuthStrategy)

    @pytest.mark.asyncio
    @patch("datadog_mcp.utils.auth_strategy.FORCE_AUTH_METHOD", "token")
    @patch("datadog_mcp.utils.auth_strategy.get_api_key", return_value=None)
    async def test_get_strategy_forced_unavailable(self, mock_key):
        """Test error when forced auth method unavailable."""
        with pytest.raises(ValueError):
            await AuthStrategyFactory.get_strategy()

    @pytest.mark.asyncio
    @patch("datadog_mcp.utils.auth_strategy.FORCE_AUTH_METHOD", "")
    @patch("datadog_mcp.utils.auth_strategy.get_cookie", return_value="dogweb=test")
    async def test_get_strategy_auto_cookie_preferred(self, mock_cookie):
        """Test auto-detection prefers cookie when available."""
        strategy = await AuthStrategyFactory.get_strategy()
        assert isinstance(strategy, CookieAuthStrategy)

    @pytest.mark.asyncio
    @patch("datadog_mcp.utils.auth_strategy.FORCE_AUTH_METHOD", "")
    @patch("datadog_mcp.utils.auth_strategy.get_cookie", return_value=None)
    @patch("datadog_mcp.utils.auth_strategy.get_api_key", return_value="test-key")
    @patch("datadog_mcp.utils.auth_strategy.get_app_key", return_value="test-app")
    async def test_get_strategy_auto_token_fallback(self, mock_app, mock_key, mock_cookie):
        """Test auto-detection falls back to token when cookie unavailable."""
        strategy = await AuthStrategyFactory.get_strategy()
        assert isinstance(strategy, TokenAuthStrategy)

    @patch("datadog_mcp.utils.auth_strategy.FORCE_AUTH_METHOD", "token")
    @patch("datadog_mcp.utils.auth_strategy.get_api_key", return_value="test-key")
    @patch("datadog_mcp.utils.auth_strategy.get_app_key", return_value="test-app")
    def test_get_strategy_sync_forced_token(self, mock_app, mock_key):
        """Test synchronous forced token strategy."""
        strategy = AuthStrategyFactory.get_strategy_sync()
        assert isinstance(strategy, TokenAuthStrategy)

    @patch("datadog_mcp.utils.auth_strategy.FORCE_AUTH_METHOD", "cookie")
    @patch("datadog_mcp.utils.auth_strategy.get_cookie", return_value="dogweb=test")
    def test_get_strategy_sync_forced_cookie(self, mock_cookie):
        """Test synchronous forced cookie strategy."""
        strategy = AuthStrategyFactory.get_strategy_sync()
        assert isinstance(strategy, CookieAuthStrategy)
