"""
Services API client for Datadog.

Handles all service definition operations including listing and retrieving service definitions.
"""

from typing import Any, Dict, Optional

from .base_client import DatadogAPIBaseClient


class ServicesClient(DatadogAPIBaseClient):
    """Client for Datadog Services API operations."""

    async def list_service_definitions(
        self,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """List all service definitions.

        Args:
            limit: Maximum number of service definitions to return

        Returns:
            API response containing service definitions list
        """
        endpoint = self.endpoint_resolver.service_definitions_list()
        params = {"limit": limit}
        return await self.http_client.get(endpoint, params=params)

    async def get_service_definition(
        self,
        service_name: str,
        schema_version: str = "v2.2",
    ) -> Dict[str, Any]:
        """Get service definition.

        Args:
            service_name: Service name
            schema_version: Service definition schema version (v2, v2.1, v2.2)

        Returns:
            API response containing service definition
        """
        endpoint = self.endpoint_resolver.service_definition_get(
            service_name, schema_version=schema_version
        )
        return await self.http_client.get(endpoint)
