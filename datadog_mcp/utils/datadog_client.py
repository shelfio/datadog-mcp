"""
Datadog API client utilities
"""

import logging
import os
from typing import Any, Dict, List, Optional

import httpx
from datadog_api_client import ApiClient, Configuration
from datadog_api_client.v2.api.logs_api import LogsApi
from datadog_api_client.v2.model.logs_list_request import LogsListRequest
from datadog_api_client.v2.model.logs_list_request_page import LogsListRequestPage
from datadog_api_client.v2.model.logs_query_filter import LogsQueryFilter
from datadog_api_client.v2.model.logs_query_options import LogsQueryOptions
from datadog_api_client.v2.model.logs_sort import LogsSort
from datadog_api_client.v2.model.logs_aggregate_request import LogsAggregateRequest
from datadog_api_client.v2.model.logs_aggregation_function import LogsAggregationFunction
from datadog_api_client.v2.model.logs_compute import LogsCompute
from datadog_api_client.v2.model.logs_compute_type import LogsComputeType
from datadog_api_client.v2.model.logs_group_by import LogsGroupBy
from datadog_api_client.v2.model.logs_aggregate_sort import LogsAggregateSort

from .secrets_provider import get_secret_provider, is_aws_secrets_configured

logger = logging.getLogger(__name__)

# Datadog API configuration
DATADOG_API_URL = "https://api.datadoghq.com"
DATADOG_API_KEY = os.getenv("DD_API_KEY")
DATADOG_APP_KEY = os.getenv("DD_APP_KEY")

# Cookie-based authentication (preferred for MCP)
# Use environment variables if set, otherwise use default paths
DATADOG_COOKIE_FILE = os.getenv("DD_COOKIE_FILE", os.path.expanduser("~/.datadog_cookie"))
DATADOG_CSRF_FILE = os.getenv("DD_CSRF_FILE", os.path.expanduser("~/.datadog_csrf"))

# Load cookies if available
DATADOG_COOKIE = None
DATADOG_CSRF_TOKEN = None

if DATADOG_COOKIE_FILE and os.path.exists(DATADOG_COOKIE_FILE):
    try:
        with open(DATADOG_COOKIE_FILE, 'r') as f:
            DATADOG_COOKIE = f.read().strip()
    except Exception as e:
        logger.warning(f"Failed to load cookie from {DATADOG_COOKIE_FILE}: {e}")

if DATADOG_CSRF_FILE and os.path.exists(DATADOG_CSRF_FILE):
    try:
        with open(DATADOG_CSRF_FILE, 'r') as f:
            DATADOG_CSRF_TOKEN = f.read().strip()
    except Exception as e:
        logger.warning(f"Failed to load CSRF token from {DATADOG_CSRF_FILE}: {e}")

# Datadog API configuration loaded from environment
# Use cookies if available, fall back to API keys
USE_COOKIES = bool(DATADOG_COOKIE and DATADOG_CSRF_TOKEN)

if not USE_COOKIES and (not DATADOG_API_KEY or not DATADOG_APP_KEY):
    logger.error("Either (DD_COOKIE_FILE + DD_CSRF_FILE) or (DD_API_KEY + DD_APP_KEY) must be configured")
    raise ValueError("Datadog API credentials not configured")


def get_datadog_configuration() -> Configuration:
    """Get Datadog API configuration."""
    configuration = Configuration()
    configuration.api_key["apiKeyAuth"] = DATADOG_API_KEY
    configuration.api_key["appKeyAuth"] = DATADOG_APP_KEY
    return configuration


async def get_auth_credentials(include_csrf: bool = False) -> tuple[Dict[str, str], Optional[Dict[str, str]]]:
    """Get authentication credentials with priority: Cookies (if available) > AWS Secrets > Environment Variables.

    Cookies are prioritized because they represent browser authentication with full user permissions.

    Returns:
        Tuple of (headers_dict, cookies_dict_or_none)
        - headers_dict contains auth headers or empty headers for cookie auth
        - cookies_dict_or_none contains cookies if using cookie auth, else None
    """
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
    }

    # Try cookies first - browser auth has full permissions
    if DATADOG_COOKIE and DATADOG_CSRF_TOKEN:
        logger.debug("Using cookie-based authentication (highest priority)")
        if include_csrf:
            headers["x-csrf-token"] = DATADOG_CSRF_TOKEN
        cookies = {"dogweb": DATADOG_COOKIE}
        return headers, cookies

    # Fall back to AWS Secrets Manager
    if is_aws_secrets_configured():
        try:
            provider = await get_secret_provider()
            if provider:
                credentials = await provider.get_credentials()
                headers["DD-API-KEY"] = credentials.api_key
                headers["DD-APPLICATION-KEY"] = credentials.app_key
                logger.debug("Using AWS Secrets Manager for authentication")
                return headers, None  # No cookies needed
        except Exception as e:
            logger.warning(f"Failed to fetch AWS credentials: {e}. Falling back to environment variables.")

    # Fall back to environment variables
    logger.debug("Using environment variable-based authentication")
    headers["DD-API-KEY"] = DATADOG_API_KEY
    headers["DD-APPLICATION-KEY"] = DATADOG_APP_KEY
    return headers, None




async def fetch_ci_pipelines(
    repository: Optional[str] = None,
    pipeline_name: Optional[str] = None,
    days_back: int = 90,
    limit: int = 100,
    cursor: Optional[str] = None,
) -> Dict[str, Any]:
    """Fetch CI pipelines from Datadog API."""
    # Try the v2 CI Visibility endpoint with proper content-type
    url = f"{DATADOG_API_URL}/api/v2/ci/pipelines/events/search"

    headers, cookies = await get_auth_credentials()
    headers.update({
        "Content-Type": "application/json",
        "Accept": "application/json",
    })

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
            response = await client.post(url, headers=headers, json=payload, cookies=cookies)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            # Try alternative endpoint if v2 fails
            if e.response.status_code == 415:
                logger.info(f"CI Pipelines v2 endpoint returned 415, trying v1 endpoint")
                # Fallback to list endpoint if available
                alt_url = f"{DATADOG_API_URL}/api/v2/ci/pipelines"
                try:
                    params = {"page[size]": limit}
                    if cursor:
                        params["page[cursor]"] = cursor
                    response = await client.get(alt_url, headers=headers, params=params, cookies=cookies)
                    response.raise_for_status()
                    return response.json()
                except Exception as alt_e:
                    logger.error(f"Both CI pipeline endpoints failed: {alt_e}")
                    raise e
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
    """Fetch logs from Datadog API with flexible filtering using raw HTTP."""
    try:
        # Build query filter
        query_parts = []

        # Add filters from the filters dictionary
        if filters:
            for key, value in filters.items():
                query_parts.append(f"{key}:{value}")

        # Add free-text query
        if query:
            query_parts.append(query)

        combined_query = " AND ".join(query_parts) if query_parts else "*"

        # Use raw HTTP with proper fallback authentication
        headers, cookies = await get_auth_credentials()
        headers.update({"Content-Type": "application/json"})

        # Build payload for logs list API
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
            "sort": {
                "timestamp": "desc"
            }
        }

        if cursor:
            payload["page"]["cursor"] = cursor

        url = f"{DATADOG_API_URL}/api/v2/logs/events/search"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, headers=headers, json=payload, cookies=cookies)
                response.raise_for_status()
                data = response.json()

                # Normalize response format
                result = {
                    "data": data.get("data", []),
                    "meta": data.get("meta", {}),
                }

                return result
            except httpx.HTTPError as e:
                logger.error(f"HTTP error fetching logs: {e}")
                if hasattr(e, "response"):
                    logger.error(f"Response: {e.response.text}")
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
    try:
        # Build base query
        base_query = query if query else "*"

        # Use raw HTTP for aggregation with proper fallback authentication
        headers, cookies = await get_auth_credentials()
        headers.update({"Content-Type": "application/json"})

        # Build payload for logs aggregation API
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

        url = f"{DATADOG_API_URL}/api/v2/logs/events/aggregate"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, headers=headers, json=payload, cookies=cookies)
                response.raise_for_status()
                data = response.json()

                # Extract field values from buckets
                field_values = []
                if "data" in data and data["data"] and "buckets" in data["data"]:
                    for bucket in data["data"]["buckets"]:
                        if "by" in bucket and field_name in bucket["by"]:
                            field_values.append({
                                "value": bucket["by"][field_name],
                                "count": bucket.get("computes", {}).get("c0", 0) if bucket.get("computes") else 0
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
                if hasattr(e, "response"):
                    logger.error(f"Response: {e.response.text}")
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
    """Fetch teams from Datadog API."""
    url = f"{DATADOG_API_URL}/api/v2/team"

    headers, _ = await get_auth_credentials()
    headers.update({"Content-Type": "application/json"})

    # Add pagination parameters
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
    """Fetch team memberships from Datadog API."""
    url = f"{DATADOG_API_URL}/api/v2/team/{team_id}/memberships"

    headers, _ = await get_auth_credentials()
    headers.update({"Content-Type": "application/json"})

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json().get("data", [])
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
) -> Dict[str, Any]:
    """Fetch metrics from Datadog API with flexible filtering."""

    headers, _ = await get_auth_credentials()
    
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
    
    # Add aggregation_by to the query if specified (after filters)
    if aggregation_by:
        by_clause = ",".join(aggregation_by)
        query_parts.append(f" by {{{by_clause}}}")
    
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
    
    url = f"{DATADOG_API_URL}/api/v1/query"
    
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
    """Fetch list of all available metrics from Datadog API."""

    headers, _ = await get_auth_credentials()
    
    # Use the v2 metrics endpoint to list all metrics
    url = f"{DATADOG_API_URL}/api/v2/metrics"
    
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
    """Fetch available fields/tags for a metric from Datadog API."""

    headers, _ = await get_auth_credentials()
    
    # Use the proper Datadog API endpoint to get all tags for a metric
    url = f"{DATADOG_API_URL}/api/v2/metrics/{metric_name}/all-tags"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            available_fields = set()
            
            # Extract tags from the response
            if "data" in data and "attributes" in data["data"]:
                attributes = data["data"]["attributes"]
                
                # Get tags from the attributes
                if "tags" in attributes:
                    for tag in attributes["tags"]:
                        # Tags are in format "field:value", extract just the field name
                        if ":" in tag:
                            field_name = tag.split(":", 1)[0]
                            available_fields.add(field_name)
            
            return sorted(list(available_fields))
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching metric tags: {e}")
            if hasattr(e, 'response') and e.response.status_code == 404:
                logger.warning(f"Metric {metric_name} not found or has no tags")
                return []
            raise
        except Exception as e:
            logger.error(f"Error fetching metric tags: {e}")
            raise



async def fetch_metric_field_values(
    metric_name: str,
    field_name: str,
) -> List[str]:
    """Fetch all possible values for a specific field of a metric from Datadog API."""

    headers, _ = await get_auth_credentials()
    
    # Use the same endpoint as get_metric_fields but extract values for specific field
    url = f"{DATADOG_API_URL}/api/v2/metrics/{metric_name}/all-tags"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            field_values = set()
            
            # Extract values for the specific field from the tags
            if "data" in data and "attributes" in data["data"]:
                attributes = data["data"]["attributes"]
                
                # Get tags from the attributes
                if "tags" in attributes:
                    for tag in attributes["tags"]:
                        # Tags are in format "field:value", extract values for the specific field
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
    """Fetch service definitions from Datadog API."""

    headers, _ = await get_auth_credentials()
    
    # Use the service definitions endpoint
    url = f"{DATADOG_API_URL}/api/v2/services/definitions"
    
    # Build query parameters
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
    """Fetch a single service definition from Datadog API."""

    headers = await get_auth_headers()
    
    # Use the specific service definition endpoint
    url = f"{DATADOG_API_URL}/api/v2/services/definitions/{service_name}"
    
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
    """Fetch monitors from Datadog API with pagination metadata."""

    headers = await get_auth_headers(include_csrf=False)
    cookies = get_api_cookies()

    # Use the v1 monitors endpoint
    url = f"{DATADOG_API_URL}/api/v1/monitor"

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
            response = await client.get(url, headers=headers, params=params, cookies=cookies)
            response.raise_for_status()
            monitors = response.json()

            # Return structured response with metadata
            return {
                "monitors": monitors,
                "page": page,
                "page_size": page_size,
                "returned": len(monitors),
                "has_more": len(monitors) == page_size,  # If we got full page, assume more exists
                "next_page": page + 1 if len(monitors) == page_size else None,
            }

        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching monitors: {e}")
            raise
        except Exception as e:
            logger.error(f"Error fetching monitors: {e}")
            raise


async def get_monitor(monitor_id: int) -> Dict[str, Any]:
    """Get a specific monitor from Datadog API."""
    url = f"{DATADOG_API_URL}/api/v1/monitor/{monitor_id}"
    cookies = get_api_cookies()
    headers = await get_auth_headers(include_csrf=False)

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, cookies=cookies)
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
    """Create a new monitor in Datadog API."""
    headers = await get_auth_headers(include_csrf=True)
    headers["Content-Type"] = "application/json"

    url = f"{DATADOG_API_URL}/api/v1/monitor"

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

    cookies = get_api_cookies()
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=payload, cookies=cookies)
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
    """Update an existing monitor in Datadog API."""
    headers = await get_auth_headers(include_csrf=True)
    headers["Content-Type"] = "application/json"

    url = f"{DATADOG_API_URL}/api/v1/monitor/{monitor_id}"

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

    cookies = get_api_cookies()
    async with httpx.AsyncClient() as client:
        try:
            response = await client.put(url, headers=headers, json=payload, cookies=cookies)
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"HTTP error updating monitor {monitor_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error updating monitor {monitor_id}: {e}")
            raise


async def delete_monitor(monitor_id: int) -> Dict[str, Any]:
    """Delete a monitor from Datadog API."""
    headers = await get_auth_headers(include_csrf=True)
    cookies = get_api_cookies()

    url = f"{DATADOG_API_URL}/api/v1/monitor/{monitor_id}"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.delete(url, headers=headers, cookies=cookies)
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"HTTP error deleting monitor {monitor_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error deleting monitor {monitor_id}: {e}")
            raise


async def fetch_slos(
    tags: Optional[str] = None,
    query: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """Fetch SLOs from Datadog API."""
    url = f"{DATADOG_API_URL}/api/v1/slo"

    headers = await get_auth_headers()
    headers.update({"Content-Type": "application/json"})
    
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
    url = f"{DATADOG_API_URL}/api/v1/slo/{slo_id}"

    headers = await get_auth_headers()
    headers.update({"Content-Type": "application/json"})
    
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
    url = f"{DATADOG_API_URL}/api/v1/slo/{slo_id}/history"

    headers = await get_auth_headers()
    headers.update({"Content-Type": "application/json"})
    
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


# Notebook Management Functions

async def create_notebook(
    title: str,
    description: Optional[str] = None,
    tags: Optional[List[str]] = None,
    cells: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Create a new Datadog notebook."""
    url = f"{DATADOG_API_URL}/api/v1/notebooks"

    headers = await get_auth_headers(include_csrf=True)
    headers["Content-Type"] = "application/json"

    payload = {
        "data": {
            "type": "notebooks",
            "attributes": {
                "name": title,
                "cells": cells or [],
                "time": {
                    "live_span": "1h"
                }
            }
        }
    }

    if description:
        payload["data"]["attributes"]["description"] = description

    # Note: Datadog API has strict tag format requirements (team key only)
    # Skipping tags for now as they require special formatting

    async with httpx.AsyncClient() as client:
        try:
            cookies = get_api_cookies()
            response = await client.post(url, headers=headers, json=payload, cookies=cookies)
            response.raise_for_status()
            data = response.json()
            return data.get("data", {})
        except httpx.HTTPError as e:
            logger.error(f"HTTP error creating notebook: {e}")
            raise
        except Exception as e:
            logger.error(f"Error creating notebook: {e}")
            raise


async def get_notebook(notebook_id: str) -> Dict[str, Any]:
    """Fetch a specific notebook by ID."""
    url = f"{DATADOG_API_URL}/api/v1/notebooks/{notebook_id}"

    headers = await get_auth_headers()
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
    """Update a notebook's metadata."""
    url = f"{DATADOG_API_URL}/api/v1/notebooks/{notebook_id}"

    headers = await get_auth_headers(include_csrf=True)
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
    """Add a cell to a notebook."""
    url = f"{DATADOG_API_URL}/api/v1/notebooks/{notebook_id}/cells"

    headers = await get_auth_headers(include_csrf=True)
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
    """Update a cell in a notebook."""
    url = f"{DATADOG_API_URL}/api/v1/notebooks/{notebook_id}/cells/{cell_id}"

    headers = await get_auth_headers(include_csrf=True)
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
    """Delete a cell from a notebook."""
    url = f"{DATADOG_API_URL}/api/v1/notebooks/{notebook_id}/cells/{cell_id}"

    headers = await get_auth_headers(include_csrf=True)

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
    """Delete a notebook."""
    url = f"{DATADOG_API_URL}/api/v1/notebooks/{notebook_id}"

    headers = await get_auth_headers(include_csrf=True)

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


async def fetch_metric_formula(
    formula: str,
    queries: Dict[str, Dict[str, Any]],
    time_range: str = "1h",
    filters: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Fetch and calculate metrics using a formula with the Datadog V2 API.

    Args:
        formula: Formula string (e.g., "a / b * 100")
        queries: Dict of query definitions, e.g., {"a": {"metric_name": "errors", "aggregation": "sum"}, "b": {"metric_name": "requests", "aggregation": "sum"}}
        time_range: Time range to query (default: 1h)
        filters: Optional filters to apply to all queries

    Returns:
        Dict containing formula result with timeseries data
    """
    import time

    headers = await get_auth_headers()
    headers.update({"Content-Type": "application/json"})

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

    url = f"{DATADOG_API_URL}/api/v2/query/timeseries"
    cookies = get_api_cookies()

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=payload, cookies=cookies)
            response.raise_for_status()
            return await response.json()
        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching metric formula: {e}")
            raise
        except Exception as e:
            logger.error(f"Error fetching metric formula: {e}")
            raise


async def fetch_traces(
    query: str = "*",
    time_range: str = "1h",
    limit: int = 10,
    include_children: bool = False,
    cursor: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Fetch APM traces from Datadog using the spans search API.

    Args:
        query: Trace query string (e.g., "@duration:>5000000000", "service:web")
        time_range: Time range to look back (default: 1h)
        limit: Maximum number of traces to return (default: 10)
        include_children: Whether to include child spans (not applicable to search, used for filtering)
        cursor: Pagination cursor from previous response

    Returns:
        Dict containing traces/spans data and pagination info
    """
    import time

    headers = await get_auth_headers(include_csrf=False)
    headers["Content-Type"] = "application/json"
    cookies = get_api_cookies()

    # Calculate time range
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

    # Build payload for spans search API
    payload = {
        "filter": {
            "query": query,
            "from": from_timestamp * 1000,  # Convert to milliseconds
            "to": to_timestamp * 1000,
        },
        "options": {
            "timezone": "UTC",
        },
        "page": {
            "limit": limit,
        },
    }

    if cursor:
        payload["page"]["cursor"] = cursor

    url = f"{DATADOG_API_URL}/api/v2/spans/events/search"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=payload, cookies=cookies)
            response.raise_for_status()
            data = response.json()

            # Normalize response format
            result = {
                "data": data.get("data", []),
                "meta": data.get("meta", {}),
                "links": data.get("links", {}),
            }

            return result
        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching traces: {e}")
            if hasattr(e, "response"):
                logger.error(f"Response: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error fetching traces: {e}")
            raise


async def aggregate_traces(
    query: str = "*",
    group_by: Optional[List[str]] = None,
    time_range: str = "1h",
    aggregation: str = "count",
) -> Dict[str, Any]:
    """
    Aggregate APM traces by specified dimensions.

    Args:
        query: Trace query string
        group_by: List of fields to group by (e.g., ["resource_name", "status"])
        time_range: Time range to look back (default: 1h)
        aggregation: Aggregation function (count, avg, max, min, sum)

    Returns:
        Dict containing aggregated trace data
    """
    import time

    headers = await get_auth_headers(include_csrf=False)
    headers["Content-Type"] = "application/json"
    cookies = get_api_cookies()

    # Calculate time range
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

    # Build payload for spans aggregation API
    payload = {
        "filter": {
            "query": query,
            "from": from_timestamp * 1000,  # Convert to milliseconds
            "to": to_timestamp * 1000,
        },
        "compute": [
            {
                "aggregation": aggregation.upper(),
                "metric": "@duration",  # Default to duration metric
            }
        ],
    }

    if group_by:
        payload["group_by"] = [{"facet": field} for field in group_by]

    url = f"{DATADOG_API_URL}/api/v2/spans/events/aggregate"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=payload, cookies=cookies)
            response.raise_for_status()
            data = response.json()

            # Normalize response format
            result = {
                "data": data.get("data", []),
                "meta": data.get("meta", {}),
            }

            return result
        except httpx.HTTPError as e:
            logger.error(f"HTTP error aggregating traces: {e}")
            if hasattr(e, "response"):
                logger.error(f"Response: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error aggregating traces: {e}")
            raise


async def check_deployment_status(
    service: str,
    version_field: str,
    version_value: str,
    environment: Optional[str] = None,
    time_range: str = "1h",
) -> Dict[str, Any]:
    """
    Check if a specific version is deployed to a service by querying logs.

    Args:
        service: Service name to check
        version_field: Field name containing the version (e.g., "git.commit.sha", "version", "dd.version")
        version_value: Version value to search for
        environment: Optional environment filter (e.g., "prod", "staging")
        time_range: Time range to search (default: 1h)

    Returns:
        Dict with deployment status including first_seen, last_seen, log_count
    """

    # Build filters
    filters = {"service": service}
    if environment:
        filters["env"] = environment

    # Build query to search for version field
    # Try both @field format and plain field format for compatibility
    query = f"@{version_field}:{version_value} OR {version_field}:{version_value}"

    try:
        # Fetch logs using existing log function
        response = await fetch_logs(
            time_range=time_range,
            filters=filters,
            query=query,
            limit=100,
        )

        logs = response.get("data", [])

        if not logs:
            return {
                "status": "not_found",
                "service": service,
                "version_field": version_field,
                "version_value": version_value,
                "environment": environment or "all",
                "log_count": 0,
                "first_seen": None,
                "last_seen": None,
                "logs": [],
            }

        # Extract timestamps from logs
        timestamps = []
        for log in logs:
            if "timestamp" in log:
                try:
                    timestamps.append(log["timestamp"])
                except (ValueError, TypeError):
                    pass

        return {
            "status": "deployed",
            "service": service,
            "version_field": version_field,
            "version_value": version_value,
            "environment": environment or "all",
            "log_count": len(logs),
            "first_seen": min(timestamps) if timestamps else None,
            "last_seen": max(timestamps) if timestamps else None,
            "logs": logs[:10],  # Return first 10 logs for verification
        }

    except Exception as e:
        logger.error(f"Error checking deployment status: {e}")
        raise