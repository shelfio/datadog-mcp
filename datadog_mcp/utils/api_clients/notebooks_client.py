"""
Notebooks API client for Datadog.

Handles all notebook management operations including creation, update, deletion, and listing.
"""

from typing import Any, Dict, List, Optional, Union

from .base_client import DatadogAPIBaseClient


class NotebooksClient(DatadogAPIBaseClient):
    """Client for Datadog Notebooks API operations."""

    async def list_notebooks(self, limit: int = 50) -> Dict[str, Any]:
        """List all notebooks.

        Args:
            limit: Maximum number of notebooks to return

        Returns:
            API response containing notebooks list
        """
        endpoint = self.endpoint_resolver.notebooks_list()
        params = {"limit": limit}
        return await self.http_client.get(endpoint, params=params)

    async def get_notebook(self, notebook_id: Union[str, int]) -> Dict[str, Any]:
        """Get specific notebook by ID.

        Args:
            notebook_id: Notebook ID

        Returns:
            API response containing notebook details
        """
        endpoint = self.endpoint_resolver.notebook_get(notebook_id)
        return await self.http_client.get(endpoint)

    async def create_notebook(
        self,
        title: str,
        content: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new notebook.

        Args:
            title: Notebook title
            content: Optional notebook content

        Returns:
            API response containing created notebook
        """
        endpoint = self.endpoint_resolver.notebook_create()
        payload = {
            "data": {
                "type": "notebooks",
                "attributes": {
                    "name": title,
                },
            }
        }

        if content:
            payload["data"]["attributes"]["content"] = content

        return await self.http_client.post(
            endpoint, json=payload, expected_status=(200, 201)
        )

    async def update_notebook(
        self,
        notebook_id: Union[str, int],
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Update existing notebook.

        Args:
            notebook_id: Notebook ID to update
            **kwargs: Fields to update (name, content, etc.)

        Returns:
            API response containing updated notebook
        """
        endpoint = self.endpoint_resolver.notebook_update(notebook_id)
        payload = {
            "data": {
                "type": "notebooks",
                "id": str(notebook_id),
                "attributes": kwargs,
            }
        }
        return await self.http_client.put(endpoint, json=payload)

    async def delete_notebook(self, notebook_id: Union[str, int]) -> Optional[Dict[str, Any]]:
        """Delete a notebook.

        Args:
            notebook_id: Notebook ID to delete

        Returns:
            API response (typically empty on success)
        """
        endpoint = self.endpoint_resolver.notebook_delete(notebook_id)
        return await self.http_client.delete(endpoint)
