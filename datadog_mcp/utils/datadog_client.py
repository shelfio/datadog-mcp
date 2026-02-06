"""
Datadog API client utilities
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

# Cookie file location - can be overridden with DD_COOKIE_FILE env var
DEFAULT_COOKIE_FILE = os.path.expanduser("~/.datadog_cookie")
COOKIE_FILE_PATH = os.getenv("DD_COOKIE_FILE", DEFAULT_COOKIE_FILE)

# CSRF token file location - required for some endpoints with cookie auth
DEFAULT_CSRF_FILE = os.path.expanduser("~/.datadog_csrf")
CSRF_FILE_PATH = os.getenv("DD_CSRF_FILE", DEFAULT_CSRF_FILE)

# API key credentials (static, loaded once)
DATADOG_API_KEY = os.getenv("DD_API_KEY")
DATADOG_APP_KEY = os.getenv("DD_APP_KEY")


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


def get_auth_mode() -> tuple[bool, str]:
    """Determine authentication mode and API URL dynamically.

    Returns:
        Tuple of (use_cookie_auth, api_url)
    """
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


# Validate that at least one auth method is available at startup
# (but allow cookie to be added later via file)
_initial_cookie = get_cookie()
if not _initial_cookie and (not DATADOG_API_KEY or not DATADOG_APP_KEY):
    logger.warning(
        "No credentials configured. Set DD_COOKIE env var, "
        f"create {COOKIE_FILE_PATH}, or set DD_API_KEY and DD_APP_KEY."
    )


def get_auth_headers(include_csrf: bool = False) -> Dict[str, str]:
    """Get authentication headers based on auth mode (read fresh each call).

    Priority: Cookie (if available) > API keys
    This allows dynamic cookie updates without restart while still supporting API keys.

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
    elif DATADOG_API_KEY and DATADOG_APP_KEY:
        return {
            "Content-Type": "application/json",
            "DD-API-KEY": DATADOG_API_KEY,
            "DD-APPLICATION-KEY": DATADOG_APP_KEY,
        }
    else:
        raise ValueError(
            "No Datadog credentials available. Set DD_COOKIE env var, "
            f"create {COOKIE_FILE_PATH}, or set DD_API_KEY and DD_APP_KEY."
        )


async def fetch_ci_pipelines(
    repository: Optional[str] = None,
    pipeline_name: Optional[str] = None,
    days_back: int = 90,
    limit: int = 100,
    cursor: Optional[str] = None,
) -> Dict[str, Any]:
    """Fetch CI pipelines from Datadog API.

    Note: CI Pipelines endpoint only supports API key authentication (no v1 internal endpoint).
    Cookies are not supported for this endpoint.
    """
    cookie = get_cookie()
    if cookie:
        logger.warning(
            "CI Pipelines endpoint does not support cookie authentication. "
            "Please use API key authentication (DD_API_KEY and DD_APP_KEY) instead."
        )

    url = f"{get_api_url()}/api/v2/ci/pipelines/events/search"
    headers = get_auth_headers()  # Will use API keys since no cookie endpoint exists

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
                            "\n❌ AUTHENTICATION FAILED (401 Unauthorized)\n"
                            "Cookies may be invalid or in wrong format.\n\n"
                            "COOKIE SETUP:\n"
                            "1. Save cookies to: ~/.datadog_cookie\n"
                            "2. Save CSRF token to: ~/.datadog_csrf\n\n"
                            "TO EXTRACT FROM BROWSER:\n"
                            "1. Go to https://app.datadoghq.com\n"
                            "2. Open DevTools → Application → Cookies\n"
                            "3. Export as Netscape format OR\n"
                            "4. Copy specific cookie value (dd-session, etc.)\n\n"
                            "CSRF TOKEN:\n"
                            "1. Make any POST request in DevTools → Network\n"
                            "2. Find request header: x-csrf-token: <value>\n"
                            "3. Save that value to ~/.datadog_csrf\n\n"
                            "Current cookie file: ~/.datadog_cookie\n"
                            "Current CSRF file: ~/.datadog_csrf"
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
                            "API key or token is invalid/expired.\n\n"
                            "API KEY SETUP:\n"
                            "1. Set environment variables:\n"
                            "   export DD_API_KEY=<your-api-key>\n"
                            "   export DD_APP_KEY=<your-app-key>\n\n"
                            "2. OR set in AWS Secrets Manager:\n"
                            "   Path: /DEVELOPMENT/datadog/API_KEY\n"
                            "   Path: /DEVELOPMENT/datadog/APP_KEY\n\n"
                            "3. OR create in home directory:\n"
                            "   echo $DD_API_KEY > ~/.datadog_api_key\n"
                            "   echo $DD_APP_KEY > ~/.datadog_app_key"
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
    - Cookie auth: Internal endpoint /api/v1/team (supports cookies)
    - API key auth: Public endpoint /api/v2/team
    """
    cookie = get_cookie()
    headers = get_auth_headers(include_csrf=True if cookie else False)

    if cookie:
        # Use v1 internal endpoint for cookie auth
        url = f"{get_api_url()}/api/v1/team"
        # v1 endpoint uses different parameter format
        params = {
            "page[size]": page_size,
            "page[offset]": page_number * page_size,  # v1 uses offset, not page number
        }
    else:
        # Use v2 public endpoint for API key auth
        url = f"{get_api_url()}/api/v2/team"
        # v2 endpoint uses page number
        params = {
            "page[size]": page_size,
            "page[number]": page_number,
        }

    async with httpx.AsyncClient() as client:
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
    - Cookie auth: Internal endpoint /api/v1/services/definitions (supports cookies)
    - API key auth: Public endpoint /api/v2/services/definitions
    """
    cookie = get_cookie()
    headers = get_auth_headers(include_csrf=True if cookie else False)

    if cookie:
        # Use v1 internal endpoint for cookie auth
        url = f"{get_api_url()}/api/v1/services/definitions"
        # v1 uses different parameter format
        params = {
            "page[size]": page_size,
            "page[offset]": page_number * page_size,
        }
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

    async with httpx.AsyncClient() as client:
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
) -> List[Dict[str, Any]]:
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
            return response.json()
            
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