"""
Datadog API client utilities
"""

import logging
import os
import re
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

logger = logging.getLogger(__name__)

# Default Datadog site (US1) - used as fallback when DD_SITE is not set
DEFAULT_DD_SITE = "datadoghq.com"

# Supported Datadog sites - see https://docs.datadoghq.com/getting_started/site/
VALID_DD_SITES = {
    DEFAULT_DD_SITE,          # US1 (default)
    "us3.datadoghq.com",      # US3
    "us5.datadoghq.com",      # US5
    "datadoghq.eu",           # EU1
    "ap1.datadoghq.com",      # AP1 (Japan)
    "ddog-gov.com",           # US1-FED (GovCloud)
}


def _get_validated_dd_site() -> str:
    """Get and validate DD_SITE environment variable.
    
    Returns:
        Validated Datadog site domain.
        
    Raises:
        ValueError: If DD_SITE is set to an invalid value.
    """
    dd_site = os.getenv("DD_SITE", DEFAULT_DD_SITE)
    
    # Basic validation - reject obviously malformed values
    if not dd_site or not re.match(r"^[a-z0-9.-]+$", dd_site):
        raise ValueError(
            f"Invalid DD_SITE value: '{dd_site}'. "
            f"Must be one of: {', '.join(sorted(VALID_DD_SITES))}"
        )
    
    # Warn if using unknown site (don't block - Datadog may add new regions)
    if dd_site not in VALID_DD_SITES:
        logger.warning(
            f"DD_SITE '{dd_site}' is not a known Datadog site. "
            f"Known sites: {', '.join(sorted(VALID_DD_SITES))}. "
            "Proceeding anyway in case this is a new region."
        )
    
    return dd_site


# Datadog API configuration
DD_SITE = _get_validated_dd_site()
DATADOG_API_URL = f"https://api.{DD_SITE}"
DATADOG_API_KEY = os.getenv("DD_API_KEY")
DATADOG_APP_KEY = os.getenv("DD_APP_KEY")

# Datadog API configuration loaded from environment

if not DATADOG_API_KEY or not DATADOG_APP_KEY:
    logger.error("DD_API_KEY and DD_APP_KEY environment variables must be set")
    raise ValueError("Datadog API credentials not configured")


def get_datadog_configuration() -> Configuration:
    """Get Datadog API configuration."""
    configuration = Configuration()
    configuration.api_key["apiKeyAuth"] = DATADOG_API_KEY
    configuration.api_key["appKeyAuth"] = DATADOG_APP_KEY
    # Configure SDK to use the correct regional server
    configuration.server_variables["site"] = DD_SITE
    return configuration


async def fetch_ci_pipelines(
    repository: Optional[str] = None,
    pipeline_name: Optional[str] = None,
    days_back: int = 90,
    limit: int = 100,
    cursor: Optional[str] = None,
) -> Dict[str, Any]:
    """Fetch CI pipelines from Datadog API."""
    url = f"{DATADOG_API_URL}/api/v2/ci/pipelines/events/search"
    
    headers = {
        "Content-Type": "application/json",
        "DD-API-KEY": DATADOG_API_KEY,
        "DD-APPLICATION-KEY": DATADOG_APP_KEY,
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
    """Fetch logs from Datadog API with flexible filtering using SDK."""
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
        
        # Create request body
        body = LogsListRequest(
            filter=LogsQueryFilter(
                query=combined_query,
                _from=f"now-{time_range}",
                to="now",
            ),
            options=LogsQueryOptions(
                timezone="GMT",
            ),
            page=LogsListRequestPage(
                limit=limit,
                cursor=cursor,
            ),
            sort=LogsSort.TIMESTAMP_DESCENDING,  # Most recent first
        )
        
        configuration = get_datadog_configuration()
        with ApiClient(configuration) as api_client:
            api_instance = LogsApi(api_client)
            response = api_instance.list_logs(body=body)
            
            # Convert to dict format for backward compatibility
            result = {
                "data": [log.to_dict() for log in response.data] if response.data else [],
                "meta": response.meta.to_dict() if response.meta else {},
                "links": response.links.to_dict() if response.links else {},
            }
            
            return result
    
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
        
        # Create aggregation request to group by the specified field
        body = LogsAggregateRequest(
            compute=[
                LogsCompute(
                    aggregation=LogsAggregationFunction.COUNT,
                    type=LogsComputeType.TOTAL,
                ),
            ],
            filter=LogsQueryFilter(
                query=base_query,
                _from=f"now-{time_range}",
                to="now",
            ),
            group_by=[
                LogsGroupBy(
                    facet=field_name,
                    limit=limit,
                ),
            ],
        )
        
        configuration = get_datadog_configuration()
        with ApiClient(configuration) as api_client:
            api_instance = LogsApi(api_client)
            response = api_instance.aggregate_logs(body=body)
            
            # Extract field values from buckets
            field_values = []
            if response.data and response.data.buckets:
                for bucket in response.data.buckets:
                    if bucket.by and field_name in bucket.by:
                        field_values.append({
                            "value": bucket.by[field_name],
                            "count": bucket.computes.get("c0", 0) if bucket.computes else 0
                        })
            
            # Sort by count descending
            field_values.sort(key=lambda x: x["count"], reverse=True)
            
            return {
                "field": field_name,
                "time_range": time_range,
                "values": field_values,
                "total_values": len(field_values),
            }
    
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
    
    headers = {
        "Content-Type": "application/json",
        "DD-API-KEY": DATADOG_API_KEY,
        "DD-APPLICATION-KEY": DATADOG_APP_KEY,
    }
    
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
    
    headers = {
        "Content-Type": "application/json",
        "DD-API-KEY": DATADOG_API_KEY,
        "DD-APPLICATION-KEY": DATADOG_APP_KEY,
    }
    
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
    
    headers = {
        "DD-API-KEY": DATADOG_API_KEY,
        "DD-APPLICATION-KEY": DATADOG_APP_KEY,
    }
    
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
    
    headers = {
        "DD-API-KEY": DATADOG_API_KEY,
        "DD-APPLICATION-KEY": DATADOG_APP_KEY,
    }
    
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
    
    headers = {
        "DD-API-KEY": DATADOG_API_KEY,
        "DD-APPLICATION-KEY": DATADOG_APP_KEY,
    }
    
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
    
    headers = {
        "DD-API-KEY": DATADOG_API_KEY,
        "DD-APPLICATION-KEY": DATADOG_APP_KEY,
    }
    
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
    
    headers = {
        "DD-API-KEY": DATADOG_API_KEY,
        "DD-APPLICATION-KEY": DATADOG_APP_KEY,
    }
    
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
    
    headers = {
        "DD-API-KEY": DATADOG_API_KEY,
        "DD-APPLICATION-KEY": DATADOG_APP_KEY,
    }
    
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
) -> List[Dict[str, Any]]:
    """Fetch monitors from Datadog API."""
    
    headers = {
        "DD-API-KEY": DATADOG_API_KEY,
        "DD-APPLICATION-KEY": DATADOG_APP_KEY,
    }
    
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
    url = f"{DATADOG_API_URL}/api/v1/slo"
    
    headers = {
        "Content-Type": "application/json",
        "DD-API-KEY": DATADOG_API_KEY,
        "DD-APPLICATION-KEY": DATADOG_APP_KEY,
    }
    
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
    
    headers = {
        "Content-Type": "application/json",
        "DD-API-KEY": DATADOG_API_KEY,
        "DD-APPLICATION-KEY": DATADOG_APP_KEY,
    }
    
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
    
    headers = {
        "Content-Type": "application/json",
        "DD-API-KEY": DATADOG_API_KEY,
        "DD-APPLICATION-KEY": DATADOG_APP_KEY,
    }
    
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
