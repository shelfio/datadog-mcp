"""
Datadog API client utilities
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

import httpx
from datadog_api_client import Configuration

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
APP_KEY_FILE_PATH = os.getenv("DD_APP_KEY_FILE", DEFAULT_APP_KEY_FILE)

# Optional: Force specific auth method (overrides automatic detection)
# Set DD_FORCE_AUTH=cookie or DD_FORCE_AUTH=token to bypass auto-detection
FORCE_AUTH_METHOD = os.getenv("DD_FORCE_AUTH", "").lower()


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
    # This handles the case where the file contains just the value
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


async def renew_csrf_token() -> Optional[str]:
    """Renew CSRF token from Datadog API response headers.

    Makes an authenticated request to a public Datadog endpoint and extracts
    the x-csrf-token from the response headers, then saves it for future use.

    Returns:
        The new CSRF token, or None if renewal failed
    """
    try:
        cookie = get_cookie()
        if not cookie:
            logger.warning("Cannot renew CSRF token: no cookie available")
            return None

        # Use a lightweight GET endpoint to obtain fresh CSRF token
        url = f"{get_api_url()}/api/v1/org"
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
                logger.info(f"CSRF token renewed successfully")
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
    """Save API key to file for persistence.

    Args:
        api_key: The API key to save

    Returns:
        Path where API key was saved
    """
    os.makedirs(os.path.dirname(API_KEY_FILE_PATH) or ".", exist_ok=True)
    with open(API_KEY_FILE_PATH, "w") as f:
        f.write(api_key.strip())
    os.chmod(API_KEY_FILE_PATH, 0o600)  # Restrict permissions
    logger.info(f"API key saved to {API_KEY_FILE_PATH}")
    return API_KEY_FILE_PATH


def save_app_key(app_key: str) -> str:
    """Save application key to file for persistence.

    Args:
        app_key: The application key to save

    Returns:
        Path where application key was saved
    """
    os.makedirs(os.path.dirname(APP_KEY_FILE_PATH) or ".", exist_ok=True)
    with open(APP_KEY_FILE_PATH, "w") as f:
        f.write(app_key.strip())
    os.chmod(APP_KEY_FILE_PATH, 0o600)  # Restrict permissions
    logger.info(f"App key saved to {APP_KEY_FILE_PATH}")
    return APP_KEY_FILE_PATH


def get_auth_mode() -> tuple[bool, str]:
    """Determine authentication mode and API URL dynamically.

    Respects DD_FORCE_AUTH environment variable if set:
    - DD_FORCE_AUTH=cookie → Force cookie authentication (requires DD_COOKIE env/file)
    - DD_FORCE_AUTH=token → Force token authentication (requires DD_API_KEY/DD_APP_KEY)
    - Otherwise: Auto-detect (prefer cookie if available, else token)

    Returns:
        Tuple of (use_cookie_auth, api_url)
    """
    # Check if auth method is forced
    if FORCE_AUTH_METHOD == "cookie":
        cookie = get_cookie()
        if not cookie:
            raise ValueError(
                "DD_FORCE_AUTH=cookie set but no cookie available. "
                "Set DD_COOKIE env var or create ~/.datadog_cookie"
            )
        logger.info("Using forced cookie authentication")
        return True, "https://app.datadoghq.com"
    elif FORCE_AUTH_METHOD == "token":
        api_key = get_api_key()
        app_key = get_app_key()
        if not api_key or not app_key:
            raise ValueError(
                "DD_FORCE_AUTH=token set but API keys not available. "
                "Set DD_API_KEY/DD_APP_KEY env vars or create ~/.datadog_api_key/~/.datadog_app_key"
            )
        logger.info("Using forced token authentication")
        return False, "https://api.datadoghq.com"

    # Auto-detect: prefer cookie if available, else token
    cookie = get_cookie()
    if cookie:
        return True, "https://app.datadoghq.com"
    else:
        return False, "https://api.datadoghq.com"


def get_api_url() -> str:
    """Get the appropriate Datadog API URL based on current auth mode."""
    _, url = get_auth_mode()
    return url


# For backwards compatibility - but prefer get_api_url() for dynamic behavior
DATADOG_API_URL = "https://api.datadoghq.com"  # Default, overridden dynamically


# Validate that appropriate auth credentials are available at startup
# (but allow credentials to be added later via file or setup_auth tool)
_initial_cookie = get_cookie()
_initial_api_key = get_api_key()
_initial_app_key = get_app_key()

if FORCE_AUTH_METHOD == "cookie":
    if not _initial_cookie:
        logger.error(
            "DD_FORCE_AUTH=cookie set but no cookie available. "
            f"Set DD_COOKIE env var or create {COOKIE_FILE_PATH}"
        )
elif FORCE_AUTH_METHOD == "token":
    if not _initial_api_key or not _initial_app_key:
        logger.error(
            "DD_FORCE_AUTH=token set but API keys not available. "
            f"Set DD_API_KEY/DD_APP_KEY env vars or create {API_KEY_FILE_PATH}/{APP_KEY_FILE_PATH}"
        )
elif not _initial_cookie and (not _initial_api_key or not _initial_app_key):
    logger.warning(
        "No credentials configured. Set DD_COOKIE env var, "
        f"create {COOKIE_FILE_PATH}, or set DD_API_KEY and DD_APP_KEY. "
        "Optionally use DD_FORCE_AUTH=cookie or DD_FORCE_AUTH=token to force a method. "
        "Or use setup_auth tool to configure authentication."
    )


def get_auth_headers(include_csrf: bool = False) -> Dict[str, str]:
    """Get authentication headers based on auth mode (read fresh each call).

    Priority: Cookie (if available) > API keys
    This allows dynamic credential updates without restart.

    Args:
        include_csrf: If True and using cookie auth, include x-csrf-token header.
                     Required for some endpoints like traces/spans.
    """
    cookie = get_cookie()
    if cookie:
        headers = {
            "Content-Type": "application/json",
            "Cookie": cookie,
        }
        if include_csrf:
            csrf_token = get_csrf_token()
            if csrf_token:
                headers["x-csrf-token"] = csrf_token
            else:
                logger.warning("CSRF token requested but not available. Some endpoints may fail.")
        return headers
    else:
        # Use API keys (read fresh each call, not cached)
        api_key = get_api_key()
        app_key = get_app_key()
        if api_key and app_key:
            return {
                "Content-Type": "application/json",
                "DD-API-KEY": api_key,
                "DD-APPLICATION-KEY": app_key,
            }
        else:
            raise ValueError(
                "No Datadog credentials available. Set DD_COOKIE env var, "
                f"create {COOKIE_FILE_PATH}, or set DD_API_KEY/DD_APP_KEY env vars "
                f"or create {API_KEY_FILE_PATH}/{APP_KEY_FILE_PATH}. "
                "Use setup_auth tool to configure authentication."
            )


async def fetch_ci_pipelines(
    repository: Optional[str] = None,
    pipeline_name: Optional[str] = None,
    days_back: int = 90,
    limit: int = 100,
    cursor: Optional[str] = None,
) -> Dict[str, Any]:
    """Fetch CI pipelines from Datadog API.

    Tries cookie auth first (internal UI), falls back to token auth (v2 API).
    """
    # Try internal UI endpoint with cookie auth first
    cookie = get_cookie()
    if cookie:
        url = f"{get_api_url()}/api/v1/ci/pipelines/events/search"
        headers = get_auth_headers(include_csrf=True)
    else:
        # Fall back to v2 API with token auth
        url = f"{get_api_url()}/api/v2/ci/pipelines/events/search"
        api_key = get_api_key()
        app_key = get_app_key()
        if not api_key or not app_key:
            logger.error("No authentication available for CI Visibility")
            raise ValueError("CI Visibility requires either DD_COOKIE or DD_API_KEY/DD_APP_KEY")
        headers = {
            "Content-Type": "application/json",
            "DD-API-KEY": api_key,
            "DD-APPLICATION-KEY": app_key,
        }

    # Build query filter
    query_parts = []
    if repository:
        query_parts.append(f'@git.repository.name:"{repository}"')
    if pipeline_name:
        query_parts.append(f'@ci.pipeline.name:"{pipeline_name}"')

    query = " AND ".join(query_parts) if query_parts else "*"

    payload = {
        "filter": {
            "query": query,
            "from": f"now-{days_back}d",
            "to": "now",
        },
        "page": {"limit": limit},
    }

    if cursor:
        payload["page"]["cursor"] = cursor

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching pipelines: {e}")
            raise
        except Exception as e:
            logger.error(f"Error fetching pipelines: {e}")
            raise


async def fetch_logs(
    time_range: str = "1h",
    filters: Optional[Dict[str, str]] = None,
    query: Optional[str] = None,
    limit: int = 50,
    cursor: Optional[str] = None,
) -> Dict[str, Any]:
    """Fetch logs from Datadog API with flexible filtering using httpx.

    Uses different endpoints based on auth mode:
    - Cookie auth: Internal UI endpoint /api/v1/logs-analytics/list (supports cookies)
    - API key auth: Public endpoint /api/v2/logs/events/search
    """
    import asyncio

    cookie = get_cookie()

    # Build query filter
    query_parts = []
    if filters:
        for key, value in filters.items():
            query_parts.append(f"{key}:{value}")
    if query:
        query_parts.append(query)
    combined_query = " AND ".join(query_parts) if query_parts else "*"

    # Convert time_range to seconds for internal API
    time_seconds_map = {
        "1h": 3600,
        "4h": 14400,
        "8h": 28800,
        "1d": 86400,
        "7d": 604800,
        "14d": 1209600,
        "30d": 2592000,
    }
    time_seconds = time_seconds_map.get(time_range, 3600)

    if cookie:
        # Use internal UI endpoint for cookie auth
        url = f"{get_api_url()}/api/v1/logs-analytics/list"
        headers = get_auth_headers(include_csrf=True)
        # Add origin header required by internal endpoint
        headers["origin"] = "https://app.datadoghq.com"

        csrf_token = get_csrf_token()

        # Build internal API payload format
        payload = {
            "list": {
                "columns": [],
                "sort": {
                    "field": {
                        "path": "@timestamp",
                        "order": "desc"
                    }
                },
                "limit": limit,
                "time": {
                    "from": f"now-{time_seconds}s",
                    "to": "now"
                },
                "search": {
                    "query": combined_query
                },
                "includeEvents": True,
                "computeCount": False,
                "indexes": ["*"],
                "executionInfo": {},
                "paging": {}
            }
        }

        # Add cursor for pagination
        if cursor:
            payload["list"]["paging"]["after"] = cursor

        # Add CSRF token to body
        if csrf_token:
            payload["_authentication_token"] = csrf_token

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, headers=headers, json=payload, timeout=30.0)
                response.raise_for_status()
                result = response.json()

                # Internal API uses async polling pattern - poll until status is "done"
                max_polls = 30  # Maximum number of poll attempts
                poll_interval = 0.5  # Seconds between polls

                while result.get("status") == "running" and max_polls > 0:
                    await asyncio.sleep(poll_interval)
                    # Re-post the same request to get updated status
                    response = await client.post(url, headers=headers, json=payload, timeout=30.0)
                    response.raise_for_status()
                    result = response.json()
                    max_polls -= 1

                if result.get("status") == "running":
                    logger.warning("Log query timed out waiting for results")

                # Extract events from the result
                events = result.get("result", {}).get("events", [])

                # Transform events to match public API format
                # Internal API structure: event.event contains the log data
                normalized_data = []
                for evt in events:
                    event_data = evt.get("event", {})
                    custom = event_data.get("custom", {})

                    # Extract status/level from custom fields or tags
                    status = custom.get("level", "").lower()
                    if not status:
                        # Try to extract from tags
                        for tag in event_data.get("tags", []):
                            if tag.startswith("status:"):
                                status = tag.split(":", 1)[1]
                                break

                    normalized_data.append({
                        "id": evt.get("id", ""),
                        "attributes": {
                            "timestamp": custom.get("timestamp") or event_data.get("discovery_timestamp"),
                            "message": event_data.get("message", ""),
                            "service": event_data.get("service"),
                            "status": status,
                            "host": event_data.get("host"),
                            "tags": event_data.get("tags", []),
                            "attributes": event_data,
                        }
                    })

                # Get pagination cursor from response
                paging = result.get("result", {}).get("paging", {})
                next_cursor = paging.get("after")

                return {
                    "data": normalized_data,
                    "meta": {
                        "page": {
                            "after": next_cursor
                        }
                    }
                }
            except httpx.HTTPError as e:
                if hasattr(e, 'response') and e.response is not None:
                    status = e.response.status_code
                    body = e.response.text
                    logger.error(f"HTTP error fetching logs: {e}")
                    logger.error(f"Response status: {status}")
                    logger.error(f"Response body: {body}")

                    if status == 401:
                        logger.error(
                            "\n❌ AUTHENTICATION FAILED (401 Unauthorized)\n\n"
                            "🔑 COOKIE SETUP (REQUIRED):\n\n"
                            "Save to ~/.datadog_cookie (NETSCAPE FORMAT):\n"
                            "  dogweb    c9829ab768105289702a99dcf45d2d9511430cbe67c628ce2f7b4460b0a1beda0e084d2e\n\n"
                            "OR (NAMED FORMAT):\n"
                            "  dogweb=c9829ab768105289702a99dcf45d2d9511430cbe67c628ce2f7b4460b0a1beda0e084d2e\n\n"
                            "⚠️  KEY POINT: Cookie name MUST be 'dogweb' (not 'session' or others)\n\n"
                            "🔐 CSRF TOKEN SETUP (REQUIRED):\n"
                            "Save to ~/.datadog_csrf:\n"
                            "  633591dfef19d8a51260ae1442d822a1e3ca9932\n\n"
                            "📖 TO EXTRACT FROM BROWSER:\n"
                            "1. Go to https://app.datadoghq.com\n"
                            "2. Open DevTools → Application → Cookies → datadoghq.com\n"
                            "3. Find 'dogweb' cookie in the list\n"
                            "4. Copy the VALUE (the long hex string)\n"
                            "5. For CSRF: Network tab → make any POST request → Find x-csrf-token header\n\n"
                            "📁 FILES TO UPDATE:\n"
                            "  ~/.datadog_cookie (contains: dogweb=<value>)\n"
                            "  ~/.datadog_csrf   (contains: <csrf-token>)"
                        )
                    elif status == 403:
                        logger.error(
                            "\n⚠️  PERMISSION DENIED (403 Forbidden)\n"
                            "Cookie/token valid, but API key lacks required permissions.\n"
                            "For logs: Ensure 'logs_read_data' permission is granted.\n"
                            "For traces: Ensure 'traces_read_data' permission is granted."
                        )
                raise
            except Exception as e:
                logger.error(f"Error fetching logs: {e}")
                raise
    else:
        # Use public API endpoint for API key auth
        url = f"{get_api_url()}/api/v2/logs/events/search"
        headers = get_auth_headers()

        payload = {
            "filter": {
                "query": combined_query,
                "from": f"now-{time_range}",
                "to": "now",
            },
            "options": {
                "timezone": "GMT",
            },
            "page": {
                "limit": limit,
            },
            "sort": "-timestamp",
        }

        if cursor:
            payload["page"]["cursor"] = cursor

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, headers=headers, json=payload, timeout=30.0)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                if hasattr(e, 'response') and e.response is not None:
                    status = e.response.status_code
                    body = e.response.text
                    logger.error(f"HTTP error fetching logs: {e}")
                    logger.error(f"Response status: {status}")
                    logger.error(f"Response body: {body}")

                    if status == 401:
                        logger.error(
                            "\n❌ AUTHENTICATION FAILED (401 Unauthorized)\n"
                            "Using token/API key auth. Credentials invalid/expired.\n\n"
                            "🔑 API KEY SETUP (TOKEN AUTH):\n\n"
                            "Option 1: Environment Variables\n"
                            "  export DD_API_KEY=<your-api-key>\n"
                            "  export DD_APP_KEY=<your-app-key>\n\n"
                            "Option 2: AWS Secrets Manager\n"
                            "  Path: /DEVELOPMENT/datadog/API_KEY\n"
                            "  Path: /DEVELOPMENT/datadog/APP_KEY\n\n"
                            "Option 3: Home Directory Files\n"
                            "  echo $DD_API_KEY > ~/.datadog_api_key\n"
                            "  echo $DD_APP_KEY > ~/.datadog_app_key\n\n"
                            "⚠️  ALTERNATIVE: If you prefer cookie auth instead:\n"
                            "  Use ~/.datadog_cookie with 'dogweb=<value>' format\n"
                            "  Use ~/.datadog_csrf with CSRF token value"
                        )
                    elif status == 403:
                        logger.error(
                            "\n⚠️  PERMISSION DENIED (403 Forbidden)\n"
                            "Credentials valid, but API key lacks required scopes.\n"
                            "For logs: Grant 'logs_read_data' permission\n"
                            "For traces: Grant 'traces_read_data' permission\n"
                            "Contact Datadog admin to update API key scopes."
                        )
                raise
            except Exception as e:
                logger.error(f"Error fetching logs: {e}")
                raise


async def fetch_logs_filter_values(
    field_name: str,
    time_range: str = "1h",
    query: Optional[str] = None,
    limit: int = 100,
) -> Dict[str, Any]:
    """
    Fetch possible values for a specific log field to understand filtering options.

    Args:
        field_name: The field to get possible values for (e.g., 'service', 'env', 'status', 'host')
        time_range: Time range to look back (default: 1h)
        query: Optional query to filter logs before aggregation
        limit: Maximum number of values to return

    Returns:
        Dict containing the field values and their counts
    """
    cookie = get_cookie()

    if cookie:
        # Cookie auth: Use logs endpoint and extract unique values from results
        # The aggregation API doesn't support cookie auth, so we derive values from logs
        filters = {}
        if query and ":" in query:
            # Try to parse simple key:value queries as filters
            pass  # Keep as free-text query

        logs_result = await fetch_logs(
            time_range=time_range,
            filters=filters,
            query=query,
            limit=500,  # Fetch more logs to get better coverage of values
        )

        # Extract unique values from log attributes
        value_counts: Dict[str, int] = {}
        for log in logs_result.get("data", []):
            attrs = log.get("attributes", {})
            event_data = attrs.get("attributes", {})  # Nested attributes contains raw event

            # Map field names to where they appear in the data
            value = None
            if field_name == "service":
                value = attrs.get("service") or event_data.get("service")
            elif field_name == "host":
                value = attrs.get("host") or event_data.get("host")
            elif field_name == "status":
                value = attrs.get("status") or event_data.get("custom", {}).get("level", "").lower()
            elif field_name == "env":
                # Extract from tags
                for tag in (attrs.get("tags") or event_data.get("tags", [])):
                    if tag.startswith("env:"):
                        value = tag.split(":", 1)[1]
                        break
            elif field_name == "source":
                value = event_data.get("source")
            else:
                # Try to find in tags or custom fields
                for tag in (attrs.get("tags") or event_data.get("tags", [])):
                    if tag.startswith(f"{field_name}:"):
                        value = tag.split(":", 1)[1]
                        break
                if not value:
                    value = event_data.get("custom", {}).get(field_name)

            if value:
                value_counts[value] = value_counts.get(value, 0) + 1

        # Convert to list format and sort by count
        field_values = [
            {"value": v, "count": c}
            for v, c in value_counts.items()
        ]
        field_values.sort(key=lambda x: x["count"], reverse=True)

        return {
            "field": field_name,
            "time_range": time_range,
            "values": field_values[:limit],
            "total_values": len(field_values),
        }

    # API key auth: Use the aggregation endpoint
    url = f"{get_api_url()}/api/v2/logs/analytics/aggregate"
    headers = get_auth_headers()

    # Build base query
    base_query = query if query else "*"

    # Build aggregation request payload
    payload = {
        "compute": [
            {
                "aggregation": "count",
                "type": "total",
            }
        ],
        "filter": {
            "query": base_query,
            "from": f"now-{time_range}",
            "to": "now",
        },
        "group_by": [
            {
                "facet": field_name,
                "limit": limit,
            }
        ],
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

            # Extract field values from buckets
            field_values = []
            if "data" in data and "buckets" in data["data"]:
                for bucket in data["data"]["buckets"]:
                    if "by" in bucket and field_name in bucket["by"]:
                        field_values.append({
                            "value": bucket["by"][field_name],
                            "count": bucket.get("computes", {}).get("c0", 0)
                        })

            # Sort by count descending
            field_values.sort(key=lambda x: x["count"], reverse=True)

            return {
                "field": field_name,
                "time_range": time_range,
                "values": field_values,
                "total_values": len(field_values),
            }

        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching filter values for field '{field_name}': {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response body: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error fetching filter values for field '{field_name}': {e}")
            raise


# Backward compatibility alias
async def fetch_service_logs(
    service: Optional[str] = None,
    time_range: str = "1h",
    environment: Optional[List[str]] = None,
    log_level: Optional[str] = None,
    query: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Backward compatibility wrapper for fetch_logs."""
    filters = {}
    if service:
        filters["service"] = service
    if environment and len(environment) > 0:
        # Use first environment for simplicity
        filters["env"] = environment[0]
    if log_level:
        filters["status"] = log_level
    
    return await fetch_logs(
        time_range=time_range,
        filters=filters,
        query=query,
        limit=limit,
    )


async def fetch_teams(
    page_size: int = 50,
    page_number: int = 0,
) -> Dict[str, Any]:
    """Fetch teams from Datadog API with flexible authentication.

    Uses different endpoints based on auth mode:
    - Cookie auth: Internal endpoint /api/v1/team (supports cookies), falls back to v2
    - API key auth: Public endpoint /api/v2/team
    """
    cookie = get_cookie()
    headers = get_auth_headers(include_csrf=True if cookie else False)

    async with httpx.AsyncClient() as client:
        if cookie:
            # Try v1 internal endpoint for cookie auth first
            url = f"{get_api_url()}/api/v1/team"
            # v1 endpoint uses different parameter format
            params = {
                "page[size]": page_size,
                "page[offset]": page_number * page_size,  # v1 uses offset, not page number
            }
            try:
                response = await client.get(url, headers=headers, params=params)
                if response.status_code == 404:
                    logger.warning(f"v1 teams endpoint not found at {url}, falling back to v2")
                else:
                    response.raise_for_status()
                    return response.json()
            except httpx.HTTPError as e:
                if hasattr(e, 'response') and e.response.status_code == 404:
                    logger.warning(f"v1 teams endpoint returned 404, falling back to v2")
                else:
                    logger.error(f"HTTP error fetching teams from v1: {e}")
                    # Fall through to v2 fallback below

            # Fall back to v2 for both token auth and if v1 fails
            url = f"{get_api_url()}/api/v2/team"
            params = {
                "page[size]": page_size,
                "page[number]": page_number,
            }

        else:
            # Use v2 public endpoint for API key auth
            url = f"{get_api_url()}/api/v2/team"
            # v2 endpoint uses page number
            params = {
                "page[size]": page_size,
                "page[number]": page_number,
            }

        try:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching teams: {e}")
            raise
        except Exception as e:
            logger.error(f"Error fetching teams: {e}")
            raise


async def fetch_team_memberships(team_id: str) -> List[Dict[str, Any]]:
    """Fetch team memberships from Datadog API with flexible authentication.

    Uses different endpoints based on auth mode:
    - Cookie auth: Internal endpoint /api/v1/team/{id}/users (supports cookies)
    - API key auth: Public endpoint /api/v2/team/{id}/memberships
    """
    cookie = get_cookie()
    headers = get_auth_headers(include_csrf=True if cookie else False)

    if cookie:
        # Use v1 internal endpoint for cookie auth
        url = f"{get_api_url()}/api/v1/team/{team_id}/users"
    else:
        # Use v2 public endpoint for API key auth
        url = f"{get_api_url()}/api/v2/team/{team_id}/memberships"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()

            # Both v1 and v2 return data in "data" field
            if isinstance(data, dict) and "data" in data:
                return data.get("data", [])
            return data if isinstance(data, list) else []

        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching team memberships for {team_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error fetching team memberships for {team_id}: {e}")
            raise


async def fetch_metrics(
    metric_name: str,
    time_range: str = "1h",
    aggregation: str = "avg",
    filters: Optional[Dict[str, str]] = None,
    aggregation_by: Optional[List[str]] = None,
    as_count: bool = False,
) -> Dict[str, Any]:
    """Fetch metrics from Datadog API with flexible filtering.

    Args:
        metric_name: The metric to query
        time_range: Time window to query
        aggregation: Aggregation method (avg, sum, min, max, count)
        filters: Tag filters to apply
        aggregation_by: Fields to group by
        as_count: If True, applies .as_count() to get totals instead of rates.
                  Use for count/rate metrics (e.g., request.hits, error.count).
                  Do NOT use for gauge metrics (e.g., cpu.percent, memory.usage).
    """
    
    headers = get_auth_headers()
    
    # Build metric query
    query_parts = [f"{aggregation}:{metric_name}"]
    
    # Add filters if specified
    filter_list = []
    if filters:
        for key, value in filters.items():
            filter_list.append(f"{key}:{value}")
    
    # Combine filters with proper syntax first
    if filter_list:
        query_parts.append("{" + ",".join(filter_list) + "}")
    else:
        # Datadog requires a scope - use {*} for "all sources" when no filters
        query_parts.append("{*}")

    # Add aggregation_by to the query if specified (must come before .as_count())
    if aggregation_by:
        by_clause = ",".join(aggregation_by)
        query_parts.append(f" by {{{by_clause}}}")

    # Add .as_count() modifier if requested (for count/rate metrics)
    # This converts rate metrics to totals instead of per-second rates
    # Only use for count/rate metrics, NOT for gauge metrics
    # MUST come AFTER the 'by' clause in Datadog query syntax
    if as_count:
        query_parts.append(".as_count()")

    query = "".join(query_parts)
    
    # Log the constructed query for debugging
    logger.debug(f"Constructed query: {query}")
    
    # Calculate time range in seconds
    import time
    to_timestamp = int(time.time())
    
    time_deltas = {
        "1h": 3600,
        "4h": 14400,
        "8h": 28800,
        "1d": 86400,
        "7d": 604800,
        "14d": 1209600,
        "30d": 2592000,
    }
    
    seconds_back = time_deltas.get(time_range, 3600)
    from_timestamp = to_timestamp - seconds_back
    
    # Use GET request with query parameters
    params = {
        "query": query,
        "from": from_timestamp,
        "to": to_timestamp,
    }
    
    url = f"{get_api_url()}/api/v1/query"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching metrics: {e}")
            logger.error(f"Query: {query}")
            raise
        except Exception as e:
            logger.error(f"Error fetching metrics: {e}")
            raise




async def fetch_metrics_list(
    filter_query: str = "",
    limit: int = 50,
    cursor: Optional[str] = None,
) -> Dict[str, Any]:
    """Fetch list of all available metrics from Datadog API with flexible authentication.

    Uses different endpoints based on auth mode:
    - Cookie auth: Internal endpoint (if available, fallback to v2 with cookie)
    - API key auth: Public endpoint /api/v2/metrics
    """
    cookie = get_cookie()
    headers = get_auth_headers(include_csrf=True if cookie else False)

    # Note: v1 internal endpoint for metrics list may not exist
    # For now, use v2 endpoint which supports both auth methods via headers
    url = f"{get_api_url()}/api/v2/metrics"

    # Build query parameters
    params = {
        "page[size]": min(limit, 10000),  # API maximum
    }

    if filter_query:
        params["filter[tags]"] = filter_query

    if cursor:
        params["page[cursor]"] = cursor

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching metrics list: {e}")
            raise
        except Exception as e:
            logger.error(f"Error fetching metrics list: {e}")
            raise


async def fetch_metric_available_fields(
    metric_name: str,
    time_range: str = "1h",
) -> List[str]:
    """Fetch available fields/tags for a metric from Datadog API.

    Uses a hybrid approach:
    1. First tries the /all-tags metadata endpoint (fast, but misses custom tags)
    2. Then probes for common custom tag names by querying actual data

    This ensures we find both indexed infrastructure tags AND custom application tags.
    """

    headers = get_auth_headers()

    available_fields = set()

    # Method 1: Try the metadata endpoint first (fast)
    try:
        url = f"{get_api_url()}/api/v2/metrics/{metric_name}/all-tags"
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()

            if "data" in data and "attributes" in data["data"]:
                attributes = data["data"]["attributes"]
                if "tags" in attributes:
                    for tag in attributes["tags"]:
                        if ":" in tag:
                            field_name = tag.split(":", 1)[0]
                            available_fields.add(field_name)
    except Exception as e:
        logger.warning(f"Could not fetch from /all-tags endpoint: {e}")

    # Method 2: Probe for common custom tag names by actually querying with them
    # These are common custom application tags that often aren't indexed
    common_custom_tags = ["variant", "status", "version", "release", "deployment"]

    import time
    to_timestamp = int(time.time())
    time_deltas = {
        "1h": 3600,
        "4h": 14400,
        "8h": 28800,
        "1d": 86400,
        "7d": 604800,
        "14d": 1209600,
        "30d": 2592000,
    }
    seconds_back = time_deltas.get(time_range, 604800)  # Default to 7 days for better coverage
    from_timestamp = to_timestamp - seconds_back

    url = f"{get_api_url()}/api/v1/query"

    async with httpx.AsyncClient() as client:
        for tag_name in common_custom_tags:
            try:
                # Query with this tag to see if it exists
                query = f"avg:{metric_name}{{*}} by {{{tag_name}}}"
                params = {
                    "query": query,
                    "from": from_timestamp,
                    "to": to_timestamp,
                }

                response = await client.get(url, headers=headers, params=params)
                response.raise_for_status()
                data = response.json()

                # If we got series back, this tag exists
                if "series" in data and data["series"]:
                    available_fields.add(tag_name)

            except Exception as e:
                # Tag doesn't exist or query failed, skip it
                logger.debug(f"Tag '{tag_name}' not found or query failed: {e}")
                continue

    return sorted(list(available_fields))



async def fetch_metric_field_values(
    metric_name: str,
    field_name: str,
) -> List[str]:
    """Fetch all possible values for a specific field of a metric from Datadog API.

    This queries the actual timeseries data grouped by the field to discover all values,
    which is more reliable than the metadata endpoint for custom tags.
    """

    headers = get_auth_headers()

    # Query the actual metric data grouped by the field to get all unique values
    # This is more reliable than /all-tags for custom application tags
    import time
    to_timestamp = int(time.time())
    from_timestamp = to_timestamp - 604800  # Last 7 days

    # Build query: avg:metric{*} by {field}
    query = f"avg:{metric_name}{{*}} by {{{field_name}}}"

    params = {
        "query": query,
        "from": from_timestamp,
        "to": to_timestamp,
    }

    url = f"{get_api_url()}/api/v1/query"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

            field_values = set()

            # Extract unique values from the series tag_set
            if "series" in data:
                for series in data["series"]:
                    if "tag_set" in series:
                        for tag in series["tag_set"]:
                            # Tags are in format "field:value"
                            if ":" in tag:
                                tag_field, tag_value = tag.split(":", 1)
                                if tag_field == field_name:
                                    field_values.add(tag_value)

            return sorted(list(field_values))

        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching metric field values: {e}")
            if hasattr(e, 'response') and e.response.status_code == 404:
                logger.warning(f"Metric '{metric_name}' not found")
                return []
            raise
        except Exception as e:
            logger.error(f"Error fetching metric field values: {e}")
            raise


async def fetch_service_definitions(
    page_size: int = 10,
    page_number: int = 0,
    schema_version: Optional[str] = None,
) -> Dict[str, Any]:
    """Fetch service definitions from Datadog API with flexible authentication.

    Uses different endpoints based on auth mode:
    - Cookie auth: Internal endpoint /api/v1/services/definitions (supports cookies), falls back to v2
    - API key auth: Public endpoint /api/v2/services/definitions
    """
    cookie = get_cookie()
    headers = get_auth_headers(include_csrf=True if cookie else False)

    async with httpx.AsyncClient() as client:
        if cookie:
            # Try v1 internal endpoint for cookie auth first
            url = f"{get_api_url()}/api/v1/services/definitions"
            # v1 uses different parameter format
            params = {
                "page[size]": page_size,
                "page[offset]": page_number * page_size,
            }
            if schema_version:
                params["filter[schema_version]"] = schema_version

            try:
                response = await client.get(url, headers=headers, params=params)
                if response.status_code == 404:
                    logger.warning(f"v1 service definitions endpoint not found at {url}, falling back to v2")
                else:
                    response.raise_for_status()
                    return response.json()
            except httpx.HTTPError as e:
                if hasattr(e, 'response') and e.response.status_code == 404:
                    logger.warning(f"v1 service definitions endpoint returned 404, falling back to v2")
                else:
                    logger.error(f"HTTP error fetching service definitions from v1: {e}")
                    # Fall through to v2 fallback below

            # Fall back to v2 for both token auth and if v1 fails
            url = f"{get_api_url()}/api/v2/services/definitions"
            # v2 uses page number
            params = {
                "page[size]": page_size,
                "page[number]": page_number,
            }
            if schema_version:
                params["filter[schema_version]"] = schema_version

        else:
            # Use v2 public endpoint for API key auth
            url = f"{get_api_url()}/api/v2/services/definitions"
            # v2 uses page number
            params = {
                "page[size]": page_size,
                "page[number]": page_number,
            }
            if schema_version:
                params["filter[schema_version]"] = schema_version

        try:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching service definitions: {e}")
            raise
        except Exception as e:
            logger.error(f"Error fetching service definitions: {e}")
            raise


async def fetch_service_definition(
    service_name: str,
    schema_version: str = "v2.2",
) -> Dict[str, Any]:
    """Fetch a single service definition from Datadog API with flexible authentication.

    Uses different endpoints based on auth mode:
    - Cookie auth: Internal endpoint /api/v1/services/definitions/{name} (supports cookies)
    - API key auth: Public endpoint /api/v2/services/definitions/{name}
    """
    cookie = get_cookie()
    headers = get_auth_headers(include_csrf=True if cookie else False)

    if cookie:
        # Use v1 internal endpoint for cookie auth
        url = f"{get_api_url()}/api/v1/services/definitions/{service_name}"
    else:
        # Use v2 public endpoint for API key auth
        url = f"{get_api_url()}/api/v2/services/definitions/{service_name}"

    # Build query parameters
    params = {
        "schema_version": schema_version,
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching service definition for '{service_name}': {e}")
            if hasattr(e, 'response') and e.response.status_code == 404:
                logger.warning(f"Service definition for '{service_name}' not found")
            raise
        except Exception as e:
            logger.error(f"Error fetching service definition for '{service_name}': {e}")
            raise


async def fetch_monitors(
    tags: str = "",
    name: str = "",
    monitor_tags: str = "",
    page_size: int = 50,
    page: int = 0,
) -> Dict[str, Any]:
    """Fetch monitors from Datadog API."""

    headers = get_auth_headers()

    # Use the v1 monitors endpoint
    url = f"{get_api_url()}/api/v1/monitor"

    # Build query parameters
    params = {}

    if tags:
        params["tags"] = tags
    if name:
        params["name"] = name
    if monitor_tags:
        params["monitor_tags"] = monitor_tags

    # Add pagination parameters
    params["page_size"] = page_size
    params["page"] = page

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            monitors = response.json()

            # v1 API returns array directly, wrap in dict for compatibility
            return {
                "monitors": monitors if isinstance(monitors, list) else [],
                "returned": len(monitors) if isinstance(monitors, list) else 0,
                "has_more": False,  # v1 API doesn't provide pagination info
                "next_page": None,
            }

        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching monitors: {e}")
            raise
        except Exception as e:
            logger.error(f"Error fetching monitors: {e}")
            raise


async def fetch_slos(
    tags: Optional[str] = None,
    query: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """Fetch SLOs from Datadog API."""
    url = f"{get_api_url()}/api/v1/slo"
    
    headers = get_auth_headers()
    
    params = {
        "limit": limit,
        "offset": offset,
    }
    
    if tags:
        params["tags_query"] = tags
    if query:
        params["query"] = query
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching SLOs: {e}")
            raise
        except Exception as e:
            logger.error(f"Error fetching SLOs: {e}")
            raise


async def fetch_slo_details(slo_id: str) -> Dict[str, Any]:
    """Fetch detailed information for a specific SLO."""
    url = f"{get_api_url()}/api/v1/slo/{slo_id}"
    
    headers = get_auth_headers()
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data.get("data", {})
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching SLO details: {e}")
            raise
        except Exception as e:
            logger.error(f"Error fetching SLO details: {e}")
            raise


async def fetch_slo_history(
    slo_id: str,
    from_ts: int,
    to_ts: int,
    target: Optional[float] = None,
) -> Dict[str, Any]:
    """Fetch SLO history data."""
    url = f"{get_api_url()}/api/v1/slo/{slo_id}/history"

    headers = get_auth_headers()

    params = {
        "from_ts": from_ts,
        "to_ts": to_ts,
    }

    if target is not None:
        params["target"] = target

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("data", {})

        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching SLO history: {e}")
            raise
        except Exception as e:
            logger.error(f"Error fetching SLO history: {e}")
            raise


async def fetch_traces(
    time_range: str = "1h",
    filters: Optional[Dict[str, str]] = None,
    query: Optional[str] = None,
    limit: int = 50,
    cursor: Optional[str] = None,
) -> Dict[str, Any]:
    """Fetch APM traces (spans) from Datadog API with flexible filtering.

    Args:
        time_range: Time range to look back (e.g., '1h', '4h', '1d')
        filters: Filters to apply (e.g., {'service': 'web', 'env': 'prod', 'resource_name': 'GET /api/users'})
        query: Free-text search query (e.g., 'error', 'status:error', 'service:web AND env:prod')
        limit: Maximum number of spans to return (default: 50, max: 1000)
        cursor: Pagination cursor from previous response

    Returns:
        Dict containing traces data and pagination info

    Note: APM Traces endpoint requires API key authentication with appropriate scopes.
    Ensure your API key has `traces_read_data` permission.
    """
    cookie = get_cookie()
    headers = get_auth_headers(include_csrf=True)

    # Traces endpoints are v2 only (no v1 internal equivalent)
    url = f"{get_api_url()}/api/v2/spans/events/search"

    if cookie:
        logger.warning(
            "APM Traces endpoint has limited support for cookie authentication. "
            "For best results, use API key authentication (DD_API_KEY and DD_APP_KEY)."
        )

    # Build query filter
    query_parts = []

    # Add filters from the filters dictionary
    if filters:
        for key, value in filters.items():
            # Handle special characters in values by quoting them
            if " " in value or ":" in value:
                query_parts.append(f'{key}:"{value}"')
            else:
                query_parts.append(f"{key}:{value}")

    # Add free-text query
    if query:
        query_parts.append(query)

    combined_query = " AND ".join(query_parts) if query_parts else "*"

    # Build request body
    payload = {
        "data": {
            "attributes": {
                "filter": {
                    "from": f"now-{time_range}",
                    "to": "now",
                    "query": combined_query,
                },
                "options": {
                    "timezone": "GMT",
                },
                "page": {
                    "limit": min(limit, 1000),  # API max is 1000
                },
                "sort": "timestamp",  # Most recent first (use "-timestamp" for oldest first)
            },
            "type": "search_request",
        },
    }

    # Add CSRF token to body if using cookie auth
    csrf_token = get_csrf_token()
    if csrf_token and get_cookie():
        payload["_authentication_token"] = csrf_token

    # Add cursor for pagination if provided
    if cursor:
        payload["data"]["attributes"]["page"]["cursor"] = cursor

    async with httpx.AsyncClient() as client:
        try:
            logger.debug(f"Fetching traces with query: {combined_query}")
            logger.debug(f"Request payload: {json.dumps(payload, indent=2)}")

            response = await client.post(url, headers=headers, json=payload, timeout=30.0)
            response.raise_for_status()

            result = response.json()

            # Validate we got a proper response
            if result is None:
                logger.error("API returned None")
                raise ValueError("Datadog API returned null response")

            if not isinstance(result, dict):
                logger.error(f"API returned non-dict: {type(result)}")
                raise ValueError(f"Datadog API returned unexpected type: {type(result)}")

            logger.debug(f"Successfully fetched {len(result.get('data', []))} traces")
            return result

        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching traces: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response body: {e.response.text}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON response: {e}")
            raise
        except Exception as e:
            logger.error(f"Error fetching traces: {e}", exc_info=True)
            raise


async def aggregate_traces(
    time_range: str = "1h",
    filters: Optional[Dict[str, str]] = None,
    query: Optional[str] = None,
    group_by: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Aggregate APM traces using Datadog Analytics API.

    Args:
        time_range: Time range to look back (e.g., '1h', '4h', '1d', '7d')
        filters: Filters to apply (e.g., {'service': 'web', 'env': 'prod'})
        query: Free-text search query (e.g., '@duration:>8000000000')
        group_by: List of fields to group by (e.g., ['env', 'service'])

    Returns:
        Dict containing aggregated trace counts grouped by specified fields

    Note: APM Analytics endpoint requires API key authentication with appropriate scopes.
    Ensure your API key has `traces_read_data` permission.
    """
    cookie = get_cookie()
    headers = get_auth_headers(include_csrf=True)

    # Traces endpoints are v2 only (no v1 internal equivalent)
    url = f"{get_api_url()}/api/v2/spans/analytics/aggregate"

    if cookie:
        logger.warning(
            "APM Traces endpoint has limited support for cookie authentication. "
            "For best results, use API key authentication (DD_API_KEY and DD_APP_KEY)."
        )

    # Build query filter
    query_parts = []

    # Add filters from the filters dictionary
    if filters:
        for key, value in filters.items():
            # Handle special characters in values by quoting them
            if " " in value or ":" in value:
                query_parts.append(f'{key}:"{value}"')
            else:
                query_parts.append(f"{key}:{value}")

    # Add free-text query
    if query:
        query_parts.append(query)

    combined_query = " AND ".join(query_parts) if query_parts else "*"

    # Build request body
    payload = {
        "data": {
            "attributes": {
                "filter": {
                    "from": f"now-{time_range}",
                    "to": "now",
                    "query": combined_query,
                },
                "compute": [
                    {
                        "aggregation": "count",
                        "type": "total"
                    }
                ],
            },
            "type": "aggregate_request",
        },
    }

    # Add CSRF token to body if using cookie auth
    csrf_token = get_csrf_token()
    if csrf_token and get_cookie():
        payload["_authentication_token"] = csrf_token

    # Add group by if specified
    if group_by:
        payload["data"]["attributes"]["group_by"] = [
            {
                "facet": field,
                "type": "facet"
            }
            for field in group_by
        ]

    async with httpx.AsyncClient() as client:
        try:
            logger.debug(f"Aggregating traces with query: {combined_query}")
            logger.debug(f"Group by: {group_by}")
            logger.debug(f"Request payload: {json.dumps(payload, indent=2)}")

            response = await client.post(url, headers=headers, json=payload, timeout=30.0)
            response.raise_for_status()

            result = response.json()

            logger.debug(f"Successfully aggregated traces")
            return result

        except httpx.HTTPError as e:
            logger.error(f"HTTP error aggregating traces: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response body: {e.response.text}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON response: {e}")
            raise
        except Exception as e:
            logger.error(f"Error aggregating traces: {e}", exc_info=True)
            raise


async def get_monitor(monitor_id: int) -> Dict[str, Any]:
    """Get a specific monitor from Datadog API.

    Supports both cookie-based (v1 internal) and token-based (v1 public) auth.

    Args:
        monitor_id: The ID of the monitor to retrieve

    Returns:
        Dict containing the monitor details
    """
    use_cookie, api_url = get_auth_mode()
    headers = get_auth_headers()

    # Both cookie and token auth use v1 endpoint for monitors
    url = f"{api_url}/api/v1/monitor/{monitor_id}"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"HTTP error getting monitor {monitor_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error getting monitor {monitor_id}: {e}")
            raise


async def create_monitor(
    name: str,
    type: str,
    query: str,
    message: Optional[str] = None,
    tags: Optional[List[str]] = None,
    thresholds: Optional[Dict[str, Any]] = None,
    **kwargs,
) -> Dict[str, Any]:
    """Create a new monitor in Datadog API.

    Supports both cookie-based (v1 internal) and token-based (v1 public) auth.

    Args:
        name: Monitor name
        type: Monitor type (e.g., 'metric alert', 'log alert')
        query: Monitor query
        message: Optional alert message
        tags: Optional list of tags
        thresholds: Optional thresholds configuration
        **kwargs: Additional monitor properties

    Returns:
        Dict containing the created monitor details
    """
    use_cookie, api_url = get_auth_mode()
    headers = get_auth_headers(include_csrf=True)
    headers["Content-Type"] = "application/json"

    url = f"{api_url}/api/v1/monitor"

    payload = {
        "name": name,
        "type": type,
        "query": query,
    }

    if message:
        payload["message"] = message
    if tags:
        payload["tags"] = tags
    if thresholds:
        payload["thresholds"] = thresholds

    # Add any additional parameters
    payload.update(kwargs)

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"HTTP error creating monitor: {e}")
            raise
        except Exception as e:
            logger.error(f"Error creating monitor: {e}")
            raise


async def update_monitor(
    monitor_id: int,
    name: Optional[str] = None,
    query: Optional[str] = None,
    message: Optional[str] = None,
    tags: Optional[List[str]] = None,
    thresholds: Optional[Dict[str, Any]] = None,
    **kwargs,
) -> Dict[str, Any]:
    """Update an existing monitor in Datadog API.

    Supports both cookie-based (v1 internal) and token-based (v1 public) auth.

    Args:
        monitor_id: The ID of the monitor to update
        name: Optional new monitor name
        query: Optional new monitor query
        message: Optional new alert message
        tags: Optional new tags
        thresholds: Optional new thresholds configuration
        **kwargs: Additional properties to update

    Returns:
        Dict containing the updated monitor details
    """
    use_cookie, api_url = get_auth_mode()
    headers = get_auth_headers(include_csrf=True)
    headers["Content-Type"] = "application/json"

    url = f"{api_url}/api/v1/monitor/{monitor_id}"

    payload = {}

    if name is not None:
        payload["name"] = name
    if query is not None:
        payload["query"] = query
    if message is not None:
        payload["message"] = message
    if tags is not None:
        payload["tags"] = tags
    if thresholds is not None:
        payload["thresholds"] = thresholds

    # Add any additional parameters
    payload.update(kwargs)

    async with httpx.AsyncClient() as client:
        try:
            response = await client.put(url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"HTTP error updating monitor {monitor_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error updating monitor {monitor_id}: {e}")
            raise


async def delete_monitor(monitor_id: int) -> Dict[str, Any]:
    """Delete a monitor from Datadog API.

    Supports both cookie-based (v1 internal) and token-based (v1 public) auth.

    Args:
        monitor_id: The ID of the monitor to delete

    Returns:
        Dict containing the API response
    """
    use_cookie, api_url = get_auth_mode()
    headers = get_auth_headers(include_csrf=True)

    url = f"{api_url}/api/v1/monitor/{monitor_id}"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.delete(url, headers=headers)
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"HTTP error deleting monitor {monitor_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error deleting monitor {monitor_id}: {e}")
            raise


async def create_notebook(
    title: str,
    description: Optional[str] = None,
    tags: Optional[List[str]] = None,
    cells: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Create a new Datadog notebook.

    Supports both cookie-based (v1 internal) and token-based (v1 public) auth.

    Args:
        title: Notebook title
        description: Optional notebook description
        tags: Optional list of tags
        cells: Optional list of cell configurations

    Returns:
        Dict containing the created notebook details
    """
    import time as time_module

    use_cookie, api_url = get_auth_mode()
    url = f"{api_url}/api/v1/notebooks"

    # Use cookie auth for notebooks (token auth lacks permissions)
    headers = get_auth_headers(include_csrf=True)
    headers["Content-Type"] = "application/json"
    logger.info("Using cookie auth for create_notebook")

    # Only name, cells, and time are supported for CREATE
    # Description and tags can only be set via UPDATE
    cells_to_send = cells if cells else []

    payload = {
        "data": {
            "type": "notebooks",
            "attributes": {
                "name": title,
                "cells": cells_to_send,
                "time": {
                    "live_span": "1h"  # Relative time - required by API
                }
            }
        }
    }

    logger.info(f"create_notebook payload: {json.dumps(payload, indent=2)}")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code not in (200, 201):
                try:
                    error_detail = response.json()
                    logger.error(f"Notebook creation failed: Status {response.status_code} | Response: {error_detail}")
                    raise ValueError(f"Datadog API error: {error_detail}")
                except ValueError:
                    raise
                except:
                    logger.error(f"Notebook creation failed: Status {response.status_code} | Body: {response.text}")
                    raise ValueError(f"Datadog API error (status {response.status_code}): {response.text}")
            data = response.json()
            return data.get("data", {})
        except Exception as e:
            logger.error(f"Error creating notebook: {e}")
            raise


async def list_notebooks(
    limit: int = 20,
    offset: int = 0,
) -> Dict[str, Any]:
    """List all notebooks.

    Supports both cookie-based (v1 internal) and token-based (v1 public) auth.

    Args:
        limit: Maximum number of notebooks to return (default: 20, max: 100)
        offset: Offset for pagination (default: 0)

    Returns:
        Dict containing list of notebooks and pagination info
    """
    use_cookie, api_url = get_auth_mode()
    url = f"{api_url}/api/v1/notebooks"

    headers = get_auth_headers()
    headers["Content-Type"] = "application/json"

    params = {
        "limit": min(limit, 100),  # Cap at 100
        "offset": offset,
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            notebooks = data.get("data", [])
            meta = data.get("meta", {})
            return {
                "notebooks": notebooks,
                "page_count": meta.get("page", {}).get("total_count", 0),
                "limit": limit,
                "offset": offset,
            }
        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching notebooks: {e}")
            raise
        except Exception as e:
            logger.error(f"Error fetching notebooks: {e}")
            raise


async def get_notebook(notebook_id: str) -> Dict[str, Any]:
    """Fetch a specific notebook by ID.

    Supports both cookie-based (v1 internal) and token-based (v1 public) auth.

    Args:
        notebook_id: The ID of the notebook to retrieve

    Returns:
        Dict containing the notebook details
    """
    use_cookie, api_url = get_auth_mode()
    url = f"{api_url}/api/v1/notebooks/{notebook_id}"

    headers = get_auth_headers()
    headers["Content-Type"] = "application/json"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data.get("data", {})
        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching notebook: {e}")
            raise
        except Exception as e:
            logger.error(f"Error fetching notebook: {e}")
            raise


async def update_notebook(
    notebook_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    tags: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Update a notebook's metadata.

    Supports both cookie-based (v1 internal) and token-based (v1 public) auth.

    Args:
        notebook_id: The ID of the notebook to update
        title: Optional new notebook title
        description: Optional new description
        tags: Optional new tags

    Returns:
        Dict containing the updated notebook details
    """
    use_cookie, api_url = get_auth_mode()
    url = f"{api_url}/api/v1/notebooks/{notebook_id}"

    headers = get_auth_headers(include_csrf=True)
    headers["Content-Type"] = "application/json"

    payload = {
        "data": {
            "type": "notebooks",
            "id": notebook_id,
            "attributes": {}
        }
    }

    if title:
        payload["data"]["attributes"]["name"] = title
    if description is not None:
        payload["data"]["attributes"]["description"] = description
    if tags is not None:
        payload["data"]["attributes"]["tags"] = tags

    async with httpx.AsyncClient() as client:
        try:
            response = await client.put(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("data", {})
        except httpx.HTTPError as e:
            logger.error(f"HTTP error updating notebook: {e}")
            raise
        except Exception as e:
            logger.error(f"Error updating notebook: {e}")
            raise


async def add_notebook_cell(
    notebook_id: str,
    cell_type: str,
    position: Optional[int] = None,
    title: Optional[str] = None,
    query: Optional[str] = None,
    content: Optional[str] = None,
    visualization: Optional[str] = None,
) -> Dict[str, Any]:
    """Add a cell to a notebook.

    Supports both cookie-based (v1 internal) and token-based (v1 public) auth.

    Args:
        notebook_id: The ID of the notebook
        cell_type: The type of cell to add
        position: Optional position in the notebook
        title: Optional cell title
        query: Optional metric query
        content: Optional cell content
        visualization: Optional visualization type

    Returns:
        Dict containing the created cell details
    """
    use_cookie, api_url = get_auth_mode()
    url = f"{api_url}/api/v1/notebooks/{notebook_id}/cells"

    headers = get_auth_headers(include_csrf=True)
    headers["Content-Type"] = "application/json"

    cell_attributes = {"type": cell_type}

    if title:
        cell_attributes["title"] = title
    if query:
        cell_attributes["query"] = query
    if content:
        cell_attributes["content"] = content
    if visualization:
        cell_attributes["visualization"] = visualization

    payload = {
        "data": {
            "type": "notebook_cells",
            "attributes": cell_attributes
        }
    }

    if position is not None:
        payload["data"]["attributes"]["position"] = position

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("data", {})
        except httpx.HTTPError as e:
            logger.error(f"HTTP error adding notebook cell: {e}")
            raise
        except Exception as e:
            logger.error(f"Error adding notebook cell: {e}")
            raise


async def update_notebook_cell(
    notebook_id: str,
    cell_id: str,
    title: Optional[str] = None,
    query: Optional[str] = None,
    content: Optional[str] = None,
    visualization: Optional[str] = None,
    position: Optional[int] = None,
) -> Dict[str, Any]:
    """Update a cell in a notebook.

    Supports both cookie-based (v1 internal) and token-based (v1 public) auth.

    Args:
        notebook_id: The ID of the notebook
        cell_id: The ID of the cell to update
        title: Optional new cell title
        query: Optional new metric query
        content: Optional new cell content
        visualization: Optional new visualization type
        position: Optional new position

    Returns:
        Dict containing the updated cell details
    """
    use_cookie, api_url = get_auth_mode()
    url = f"{api_url}/api/v1/notebooks/{notebook_id}/cells/{cell_id}"

    headers = get_auth_headers(include_csrf=True)
    headers["Content-Type"] = "application/json"

    attributes = {}

    if title is not None:
        attributes["title"] = title
    if query is not None:
        attributes["query"] = query
    if content is not None:
        attributes["content"] = content
    if visualization is not None:
        attributes["visualization"] = visualization
    if position is not None:
        attributes["position"] = position

    payload = {
        "data": {
            "type": "notebook_cells",
            "id": cell_id,
            "attributes": attributes
        }
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.put(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("data", {})
        except httpx.HTTPError as e:
            logger.error(f"HTTP error updating notebook cell: {e}")
            raise
        except Exception as e:
            logger.error(f"Error updating notebook cell: {e}")
            raise


async def delete_notebook_cell(
    notebook_id: str,
    cell_id: str,
) -> Dict[str, Any]:
    """Delete a cell from a notebook.

    Supports both cookie-based (v1 internal) and token-based (v1 public) auth.

    Args:
        notebook_id: The ID of the notebook
        cell_id: The ID of the cell to delete

    Returns:
        Dict containing the deletion status
    """
    use_cookie, api_url = get_auth_mode()
    url = f"{api_url}/api/v1/notebooks/{notebook_id}/cells/{cell_id}"

    headers = get_auth_headers(include_csrf=True)

    async with httpx.AsyncClient() as client:
        try:
            response = await client.delete(url, headers=headers)
            response.raise_for_status()
            return {"status": "deleted", "cell_id": cell_id}
        except httpx.HTTPError as e:
            logger.error(f"HTTP error deleting notebook cell: {e}")
            raise
        except Exception as e:
            logger.error(f"Error deleting notebook cell: {e}")
            raise


async def delete_notebook(notebook_id: str) -> Dict[str, Any]:
    """Delete a notebook.

    Supports both cookie-based (v1 internal) and token-based (v1 public) auth.

    Args:
        notebook_id: The ID of the notebook to delete

    Returns:
        Dict containing the deletion status
    """
    use_cookie, api_url = get_auth_mode()
    url = f"{api_url}/api/v1/notebooks/{notebook_id}"

    headers = get_auth_headers(include_csrf=True)

    async with httpx.AsyncClient() as client:
        try:
            response = await client.delete(url, headers=headers)
            response.raise_for_status()
            return {"status": "deleted", "notebook_id": notebook_id}
        except httpx.HTTPError as e:
            logger.error(f"HTTP error deleting notebook: {e}")
            raise
        except Exception as e:
            logger.error(f"Error deleting notebook: {e}")
            raise


def get_datadog_configuration() -> Configuration:
    """Get Datadog API configuration."""
    configuration = Configuration()
    configuration.api_key["apiKeyAuth"] = get_api_key()
    configuration.api_key["appKeyAuth"] = get_app_key()
    return configuration


def get_api_cookies() -> Optional[Dict[str, str]]:
    """Get cookies for API calls if using cookie auth."""
    cookie = get_cookie()
    if cookie:
        return {"dogweb": cookie}
    return None


async def fetch_metric_formula(
    formula: str,
    queries: Dict[str, Dict[str, Any]],
    time_range: str = "1h",
    filters: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Fetch and calculate metrics using a formula with the Datadog V2 API.

    Supports both cookie-based (v1 internal) and token-based (v1 public) auth.

    Args:
        formula: Formula string (e.g., "a / b * 100")
        queries: Dict of query definitions
        time_range: Time range to query (default: 1h)
        filters: Optional filters to apply to all queries

    Returns:
        Dict containing formula result with timeseries data
    """
    import time

    api_url = get_api_url()

    # V2 API only supports token auth, never cookie auth
    api_key = get_api_key()
    app_key = get_app_key()
    if not api_key or not app_key:
        raise ValueError("query_metric_formula requires DD_API_KEY and DD_APP_KEY (token auth)")

    headers = {
        "Content-Type": "application/json",
        "DD-API-KEY": api_key,
        "DD-APPLICATION-KEY": app_key,
    }

    # Calculate time range in milliseconds (V2 API uses milliseconds)
    to_timestamp = int(time.time()) * 1000

    time_deltas_ms = {
        "1h": 3600 * 1000,
        "4h": 14400 * 1000,
        "8h": 28800 * 1000,
        "1d": 86400 * 1000,
        "7d": 604800 * 1000,
        "14d": 1209600 * 1000,
        "30d": 2592000 * 1000,
    }

    milliseconds_back = time_deltas_ms.get(time_range, 3600 * 1000)
    from_timestamp = to_timestamp - milliseconds_back

    # Build queries for the formula
    formula_queries = {}
    for var_name, query_def in queries.items():
        metric_name = query_def.get("metric_name")
        aggregation = query_def.get("aggregation", "avg")

        if not metric_name:
            raise ValueError(f"Query '{var_name}' missing 'metric_name'")

        # Build metric query with filters
        query_parts = [f"{aggregation}:{metric_name}"]

        filter_list = []
        if filters:
            for key, value in filters.items():
                filter_list.append(f"{key}:{value}")

        if filter_list:
            query_parts.append("{" + ",".join(filter_list) + "}")

        query_string = "".join(query_parts)

        formula_queries[var_name] = {
            "metric_query": query_string
        }

    # Build the V2 API request payload
    payload = {
        "data": {
            "type": "timeseries_request",
            "attributes": {
                "formulas": [
                    {
                        "formula": formula
                    }
                ],
                "queries": formula_queries,
                "from": int(from_timestamp),
                "to": int(to_timestamp),
            }
        }
    }

    # Use v2 API for formula queries (requires token auth)
    url = f"{api_url}/api/v2/query/timeseries"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return await response.json()
        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching metric formula: {e}")
            raise
        except Exception as e:
            logger.error(f"Error fetching metric formula: {e}")
            raise


async def check_deployment_status(
    service_name: str,
    env: str = "prod",
    time_range: str = "1h",
) -> Dict[str, Any]:
    """Check deployment status by querying related metrics and logs.

    Supports both cookie-based (v1 internal) and token-based (v1 public) auth.

    Args:
        service_name: The service name to check
        env: The environment (prod, staging, etc.)
        time_range: Time range to check

    Returns:
        Dict containing deployment status and related metrics
    """
    import time

    use_cookie, api_url = get_auth_mode()
    headers = get_auth_headers()

    # Fetch recent metrics for the service
    metric_query = f"avg:trace.web.request{{service:{service_name},env:{env}}}"

    url = f"{api_url}/api/v1/query"
    params = {
        "query": metric_query,
        "from": int((time.time() - 3600)),
        "to": int(time.time()),
    }

    result = {
        "service": service_name,
        "environment": env,
        "status": "unknown",
        "metrics": None,
        "error": None,
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

            if data.get("status") == "ok":
                result["status"] = "healthy"
                result["metrics"] = data.get("series", [])
            else:
                result["status"] = "degraded"
                result["error"] = data.get("error", "Unknown error")

            return result

        except httpx.HTTPError as e:
            logger.error(f"HTTP error checking deployment status: {e}")
            result["error"] = str(e)
            result["status"] = "error"
            return result
        except Exception as e:
            logger.error(f"Error checking deployment status: {e}")
            result["error"] = str(e)
            result["status"] = "error"
            return result