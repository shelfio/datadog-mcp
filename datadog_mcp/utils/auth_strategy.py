"""
Authentication strategies for Datadog API access.

Provides clean separation between cookie-based and token-based authentication
methods, reducing duplication and improving testability.
"""

import logging
import os
from abc import ABC, abstractmethod
from typing import Dict, Optional

import httpx

logger = logging.getLogger(__name__)

# Cookie file location - can be overridden with DD_COOKIE_FILE env var
DEFAULT_COOKIE_FILE = os.path.expanduser("~/.datadog_cookie")
COOKIE_FILE_PATH = os.getenv("DD_COOKIE_FILE", DEFAULT_COOKIE_FILE)

# CSRF token file location - required for some endpoints with cookie auth
DEFAULT_CSRF_FILE = os.path.expanduser("~/.datadog_csrf")
CSRF_FILE_PATH = os.getenv("DD_CSRF_FILE", DEFAULT_CSRF_FILE)

# API key file locations - allows updates without restarting
DEFAULT_API_KEY_FILE = os.path.expanduser("~/.datadog_api_key")
API_KEY_FILE_PATH = os.getenv("DD_API_KEY_FILE", DEFAULT_API_KEY_FILE)

DEFAULT_APP_KEY_FILE = os.path.expanduser("~/.datadog_app_key")
APP_KEY_FILE_PATH = os.getenv("DD_APP_FILE", DEFAULT_APP_KEY_FILE)

# Optional: Force specific auth method (overrides automatic detection)
FORCE_AUTH_METHOD = os.getenv("DD_FORCE_AUTH", "").lower()


# ============================================================================
# Credential Loading Functions (shared by all strategies)
# ============================================================================


def get_cookie() -> Optional[str]:
    """Get cookie from environment variable or file (read fresh each time).

    Supports formats:
    - Raw value: c9829ab768105289702a99...
    - Named format: dogweb=c9829ab768105289702a99...
    - Netscape jar format: dogweb    c9829ab768105289702a99...

    This allows updating the cookie without restarting the server.
    """
    # First check environment variable
    env_cookie = os.getenv("DD_COOKIE")
    if env_cookie:
        return format_cookie_header(env_cookie)

    # Then check cookie file
    if os.path.isfile(COOKIE_FILE_PATH):
        try:
            with open(COOKIE_FILE_PATH, "r") as f:
                cookie_raw = f.read().strip()
                if cookie_raw:
                    return format_cookie_header(cookie_raw)
        except Exception as e:
            logger.warning(f"Failed to read cookie file {COOKIE_FILE_PATH}: {e}")

    return None


def format_cookie_header(cookie_value: str) -> str:
    """Format cookie value into proper Cookie header format.

    Handles:
    - Raw hex/token: c9829ab7... → dogweb=c9829ab7...
    - Already named: dogweb=c9829ab7... → dogweb=c9829ab7...
    - Netscape format: dogweb    c9829ab7... → dogweb=c9829ab7...
    """
    if not cookie_value:
        return ""

    cookie_value = cookie_value.strip()

    # Check again after stripping (may be whitespace-only)
    if not cookie_value:
        return ""

    # Check if it's Netscape format (name whitespace value)
    if "\t" in cookie_value:
        parts = cookie_value.split("\t")
        if len(parts) >= 7:  # Netscape format has 7 fields
            return f"{parts[5]}={parts[6]}"  # name=value
        elif len(parts) == 2:
            return f"{parts[0]}={parts[1]}"

    # Check if it's already in name=value format
    if "=" in cookie_value:
        return cookie_value

    # Otherwise, treat as raw token and add dogweb prefix
    return f"dogweb={cookie_value}"


def save_cookie(cookie: str) -> str:
    """Save cookie to file for persistence.

    Args:
        cookie: The cookie string to save

    Returns:
        Path where cookie was saved
    """
    os.makedirs(os.path.dirname(COOKIE_FILE_PATH) or ".", exist_ok=True)
    with open(COOKIE_FILE_PATH, "w") as f:
        f.write(cookie.strip())
    os.chmod(COOKIE_FILE_PATH, 0o600)  # Restrict permissions
    logger.info(f"Cookie saved to {COOKIE_FILE_PATH}")
    return COOKIE_FILE_PATH


def get_csrf_token() -> Optional[str]:
    """Get CSRF token from environment variable or file (read fresh each time).

    Required for some Datadog endpoints when using cookie auth.
    """
    # First check environment variable
    env_csrf = os.getenv("DD_CSRF_TOKEN")
    if env_csrf:
        return env_csrf

    # Then check CSRF file
    if os.path.isfile(CSRF_FILE_PATH):
        try:
            with open(CSRF_FILE_PATH, "r") as f:
                csrf = f.read().strip()
                if csrf:
                    return csrf
        except Exception as e:
            logger.warning(f"Failed to read CSRF file {CSRF_FILE_PATH}: {e}")

    return None


def save_csrf_token(csrf_token: str) -> str:
    """Save CSRF token to file for persistence.

    Args:
        csrf_token: The CSRF token to save

    Returns:
        Path where token was saved
    """
    os.makedirs(os.path.dirname(CSRF_FILE_PATH) or ".", exist_ok=True)
    with open(CSRF_FILE_PATH, "w") as f:
        f.write(csrf_token.strip())
    os.chmod(CSRF_FILE_PATH, 0o600)  # Restrict permissions
    logger.info(f"CSRF token saved to {CSRF_FILE_PATH}")
    return CSRF_FILE_PATH


async def renew_csrf_token(api_url: str = "https://app.datadoghq.com") -> Optional[str]:
    """Renew CSRF token from Datadog API response headers.

    Makes an authenticated request to a public Datadog endpoint and extracts
    the x-csrf-token from the response headers, then saves it for future use.

    Args:
        api_url: Base URL for the API endpoint

    Returns:
        The new CSRF token, or None if renewal failed
    """
    try:
        cookie = get_cookie()
        if not cookie:
            logger.warning("Cannot renew CSRF token: no cookie available")
            return None

        # Use a lightweight GET endpoint to obtain fresh CSRF token
        url = f"{api_url}/api/v1/org"
        headers = {
            "Content-Type": "application/json",
            "Cookie": cookie,
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, follow_redirects=True)

            # Extract CSRF token from response headers (case-insensitive)
            csrf_token = None
            for header_name, header_value in response.headers.items():
                if header_name.lower() == "x-csrf-token":
                    csrf_token = header_value
                    break

            if csrf_token:
                save_csrf_token(csrf_token)
                logger.info("CSRF token renewed successfully")
                return csrf_token
            else:
                logger.warning("No x-csrf-token found in response headers")
                return None

    except Exception as e:
        logger.error(f"Failed to renew CSRF token: {e}")
        return None


def get_api_key() -> Optional[str]:
    """Get API key from environment variable or file (read fresh each time).

    Priority: Environment variable > File
    This allows updating the API key without restarting the server.
    """
    # First check environment variable
    env_key = os.getenv("DD_API_KEY")
    if env_key:
        return env_key

    # Then check API key file
    if os.path.isfile(API_KEY_FILE_PATH):
        try:
            with open(API_KEY_FILE_PATH, "r") as f:
                key = f.read().strip()
                if key:
                    return key
        except Exception as e:
            logger.warning(f"Failed to read API key file {API_KEY_FILE_PATH}: {e}")

    return None


def get_app_key() -> Optional[str]:
    """Get application key from environment variable or file (read fresh each time).

    Priority: Environment variable > File
    This allows updating the application key without restarting the server.
    """
    # First check environment variable
    env_key = os.getenv("DD_APP_KEY")
    if env_key:
        return env_key

    # Then check app key file
    if os.path.isfile(APP_KEY_FILE_PATH):
        try:
            with open(APP_KEY_FILE_PATH, "r") as f:
                key = f.read().strip()
                if key:
                    return key
        except Exception as e:
            logger.warning(f"Failed to read app key file {APP_KEY_FILE_PATH}: {e}")

    return None


def save_api_key(api_key: str) -> str:
    """Save API key to file for persistence."""
    os.makedirs(os.path.dirname(API_KEY_FILE_PATH) or ".", exist_ok=True)
    with open(API_KEY_FILE_PATH, "w") as f:
        f.write(api_key.strip())
    os.chmod(API_KEY_FILE_PATH, 0o600)
    logger.info(f"API key saved to {API_KEY_FILE_PATH}")
    return API_KEY_FILE_PATH


def save_app_key(app_key: str) -> str:
    """Save application key to file for persistence."""
    os.makedirs(os.path.dirname(APP_KEY_FILE_PATH) or ".", exist_ok=True)
    with open(APP_KEY_FILE_PATH, "w") as f:
        f.write(app_key.strip())
    os.chmod(APP_KEY_FILE_PATH, 0o600)
    logger.info(f"App key saved to {APP_KEY_FILE_PATH}")
    return APP_KEY_FILE_PATH


# ============================================================================
# Authentication Strategy Classes
# ============================================================================


class AuthStrategy(ABC):
    """Base class for authentication strategies."""

    @abstractmethod
    async def get_headers(self) -> Dict[str, str]:
        """Return authentication headers for this strategy."""
        pass

    @abstractmethod
    def get_cookies(self) -> Optional[Dict[str, str]]:
        """Return cookies for this strategy (if applicable)."""
        pass

    @abstractmethod
    def get_api_url(self) -> str:
        """Return the API URL for this strategy."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of this strategy."""
        pass


class TokenAuthStrategy(AuthStrategy):
    """Token-based authentication using DD_API_KEY and DD_APPLICATION_KEY.

    Uses Datadog's v2 public API endpoints.
    """

    async def get_headers(self) -> Dict[str, str]:
        """Return headers for token authentication."""
        api_key = get_api_key()
        app_key = get_app_key()
        if not api_key or not app_key:
            raise ValueError(
                "TokenAuthStrategy requires DD_API_KEY and DD_APP_KEY. "
                "Set environment variables or create ~/.datadog_api_key and ~/.datadog_app_key"
            )
        return {
            "Content-Type": "application/json",
            "DD-API-KEY": api_key,
            "DD-APPLICATION-KEY": app_key,
        }

    def get_cookies(self) -> Optional[Dict[str, str]]:
        """Token auth doesn't use cookies."""
        return None

    def get_api_url(self) -> str:
        """Return the public API URL."""
        return "https://api.datadoghq.com"

    @property
    def name(self) -> str:
        return "token"


class CookieAuthStrategy(AuthStrategy):
    """Cookie-based authentication using DD_COOKIE_FILE and DD_CSRF_FILE.

    Uses Datadog's internal UI endpoints (v1 API with app.datadoghq.com).
    """

    async def get_headers(self) -> Dict[str, str]:
        """Return headers for cookie authentication."""
        csrf_token = get_csrf_token()
        if not csrf_token:
            raise ValueError(
                "CookieAuthStrategy requires DD_CSRF_TOKEN. "
                "Set environment variable or create ~/.datadog_csrf"
            )
        return {
            "Content-Type": "application/json",
            "x-csrf-token": csrf_token,
        }

    def get_cookies(self) -> Optional[Dict[str, str]]:
        """Return cookies for this strategy."""
        cookie = get_cookie()
        if not cookie:
            raise ValueError(
                "CookieAuthStrategy requires DD_COOKIE. "
                "Set environment variable or create ~/.datadog_cookie"
            )
        # httpx expects cookies as dict, but we have it as a formatted string
        # Extract the cookie value
        if "=" in cookie:
            name, value = cookie.split("=", 1)
            return {name: value}
        return {"dogweb": cookie}

    def get_api_url(self) -> str:
        """Return the internal API URL."""
        return "https://app.datadoghq.com"

    @property
    def name(self) -> str:
        return "cookie"


class AuthStrategyFactory:
    """Factory for selecting and managing authentication strategies."""

    @staticmethod
    async def get_strategy() -> AuthStrategy:
        """Select and return appropriate auth strategy.

        Priority:
        1. If DD_FORCE_AUTH is set, use that method (cookie or token)
        2. If cookie available, use CookieAuthStrategy
        3. Otherwise use TokenAuthStrategy

        Returns:
            AuthStrategy: The appropriate strategy instance

        Raises:
            ValueError: If forced auth method is unavailable
        """
        # Check if auth method is forced
        if FORCE_AUTH_METHOD == "cookie":
            if not get_cookie():
                raise ValueError(
                    "DD_FORCE_AUTH=cookie set but no cookie available. "
                    f"Set DD_COOKIE env var or create {COOKIE_FILE_PATH}"
                )
            logger.info("Using forced cookie authentication")
            return CookieAuthStrategy()

        elif FORCE_AUTH_METHOD == "token":
            if not get_api_key() or not get_app_key():
                raise ValueError(
                    "DD_FORCE_AUTH=token set but API keys not available. "
                    f"Set DD_API_KEY/DD_APP_KEY env vars or create {API_KEY_FILE_PATH}/{APP_KEY_FILE_PATH}"
                )
            logger.info("Using forced token authentication")
            return TokenAuthStrategy()

        # Auto-detect: prefer cookie if available, else token
        if get_cookie():
            logger.debug("Auto-detected cookie authentication")
            return CookieAuthStrategy()
        else:
            logger.debug("Auto-detected token authentication")
            return TokenAuthStrategy()

    @staticmethod
    def get_strategy_sync() -> AuthStrategy:
        """Synchronous version of get_strategy for startup validation.

        This is used at module load time to validate credentials are available.
        """
        # Check if auth method is forced
        if FORCE_AUTH_METHOD == "cookie":
            if not get_cookie():
                raise ValueError(
                    "DD_FORCE_AUTH=cookie set but no cookie available. "
                    f"Set DD_COOKIE env var or create {COOKIE_FILE_PATH}"
                )
            return CookieAuthStrategy()

        elif FORCE_AUTH_METHOD == "token":
            if not get_api_key() or not get_app_key():
                raise ValueError(
                    "DD_FORCE_AUTH=token set but API keys not available. "
                    f"Set DD_API_KEY/DD_APP_KEY env vars or create {API_KEY_FILE_PATH}/{APP_KEY_FILE_PATH}"
                )
            return TokenAuthStrategy()

        # Auto-detect: prefer cookie if available, else token
        if get_cookie():
            return CookieAuthStrategy()
        else:
            return TokenAuthStrategy()
