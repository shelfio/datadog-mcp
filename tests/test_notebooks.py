"""
Tests for Datadog notebook management tools
"""

import pytest
from unittest.mock import AsyncMock, patch
from datadog_mcp.tools import (
    create_notebook,
    get_notebook,
    update_notebook,
    add_notebook_cell,
    update_notebook_cell,
    delete_notebook_cell,
    delete_notebook,
)


SAMPLE_NOTEBOOK_ID = "notebook-abc123xyz789"

SAMPLE_NOTEBOOK_RESPONSE = {
    "id": SAMPLE_NOTEBOOK_ID,
    "type": "notebook",
    "attributes": {
        "name": "Test Investigation",
        "description": "Testing notebook management",
        "author": "test@example.com",
        "created": "2026-02-05T10:00:00Z",
        "updated": "2026-02-05T10:30:00Z",
        "tags": ["investigation", "test"],
        "cells": [
            {
                "id": "cell-001",
                "type": "notebook_cells",
                "attributes": {
                    "definition": {
                        "type": "markdown",
                        "text": "# RCA Investigation\n\nInitial findings...",
                    }
                },
            },
            {
                "id": "cell-002",
                "type": "notebook_cells",
                "attributes": {
                    "definition": {
                        "type": "timeseries",
                        "title": "Error Rate",
                        "requests": [
                            {
                                "queries": [
                                    {
                                        "query": "avg:trace.web.request.errors{*}",
                                    }
                                ],
                                "display_type": "line_chart",
                            }
                        ],
                    }
                },
            },
        ],
    },
}

SAMPLE_EMPTY_NOTEBOOK = {
    "id": SAMPLE_NOTEBOOK_ID,
    "type": "notebook",
    "attributes": {
        "name": "New Notebook",
        "description": None,
        "author": "test@example.com",
        "created": "2026-02-05T10:00:00Z",
        "updated": "2026-02-05T10:00:00Z",
        "tags": [],
        "cells": [],
    },
}


class TestCreateNotebook:
    """Tests for create_notebook tool"""

    def test_create_notebook_definition(self):
        """Test create_notebook tool definition structure"""
        tool_def = create_notebook.get_tool_definition()
        assert tool_def.name == "create_notebook"
        assert "notebook" in tool_def.description.lower()
        assert "title" in tool_def.inputSchema["properties"]
        assert "title" in tool_def.inputSchema["required"]
        assert tool_def.inputSchema["properties"]["description"]["type"] == "string"
        assert tool_def.inputSchema["properties"]["tags"]["type"] == "array"

    @pytest.mark.asyncio
    async def test_create_notebook_success(self, sample_request, mock_env_credentials):
        """Test successful notebook creation"""
        sample_request.arguments = {
            "title": "RCA Investigation - 2026-02-05",
            "description": "Investigation of detection stack issue",
            "tags": ["incident:p0", "rca"],
            "cells": [
                {
                    "type": "markdown",
                    "title": "Timeline",
                    "content": "# Timeline\n\n- 10:00 UTC: Issue detected",
                }
            ],
        }

        with patch(
            "datadog_mcp.tools.create_notebook.client_create_notebook",
            new_callable=AsyncMock,
        ) as mock_create:
            mock_create.return_value = SAMPLE_NOTEBOOK_RESPONSE

            result = await create_notebook.handle_call(sample_request)

            assert len(result.content) > 0
            assert "Notebook Created" in result.content[0].text
            assert SAMPLE_NOTEBOOK_ID in result.content[0].text
            assert "Test Investigation" in result.content[0].text  # Mock returns sample data

    @pytest.mark.asyncio
    async def test_create_notebook_error(self, sample_request, mock_env_credentials):
        """Test notebook creation error handling"""
        sample_request.arguments = {"title": "Test Notebook"}

        with patch(
            "datadog_mcp.tools.create_notebook.client_create_notebook",
            new_callable=AsyncMock,
        ) as mock_create:
            mock_create.side_effect = Exception("API error: Invalid token")

            result = await create_notebook.handle_call(sample_request)

            assert len(result.content) > 0
            assert "Error creating notebook" in result.content[0].text
            assert "Invalid token" in result.content[0].text


class TestGetNotebook:
    """Tests for get_notebook tool"""

    def test_get_notebook_definition(self):
        """Test get_notebook tool definition structure"""
        tool_def = get_notebook.get_tool_definition()
        assert tool_def.name == "get_notebook"
        assert "retrieve" in tool_def.description.lower()
        assert "notebook_id" in tool_def.inputSchema["properties"]
        assert "notebook_id" in tool_def.inputSchema["required"]

    @pytest.mark.asyncio
    async def test_get_notebook_success(self, sample_request, mock_env_credentials):
        """Test successful notebook retrieval"""
        sample_request.arguments = {"notebook_id": SAMPLE_NOTEBOOK_ID}

        with patch(
            "datadog_mcp.tools.get_notebook.client_get_notebook", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = SAMPLE_NOTEBOOK_RESPONSE

            result = await get_notebook.handle_call(sample_request)

            assert len(result.content) > 0
            assert "Notebook Details" in result.content[0].text
            assert SAMPLE_NOTEBOOK_ID in result.content[0].text
            assert "Test Investigation" in result.content[0].text
            assert "markdown" in result.content[0].text
            assert "timeseries" in result.content[0].text
            assert "2" in result.content[0].text and "Cells" in result.content[0].text

    @pytest.mark.asyncio
    async def test_get_notebook_includes_cell_content(self, sample_request, mock_env_credentials):
        """Test that cell content (queries, markdown) is included in output"""
        sample_request.arguments = {"notebook_id": SAMPLE_NOTEBOOK_ID}

        with patch(
            "datadog_mcp.tools.get_notebook.client_get_notebook", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = SAMPLE_NOTEBOOK_RESPONSE

            result = await get_notebook.handle_call(sample_request)

            output_text = result.content[0].text
            # Verify markdown cell content is included
            assert "# RCA Investigation" in output_text
            assert "Initial findings..." in output_text
            # Verify timeseries cell query is included
            assert "Error Rate" in output_text
            assert "avg:trace.web.request.errors{*}" in output_text
            assert "line_chart" in output_text

    @pytest.mark.asyncio
    async def test_get_notebook_empty(self, sample_request, mock_env_credentials):
        """Test retrieving empty notebook"""
        sample_request.arguments = {"notebook_id": SAMPLE_NOTEBOOK_ID}

        with patch(
            "datadog_mcp.tools.get_notebook.client_get_notebook", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = SAMPLE_EMPTY_NOTEBOOK

            result = await get_notebook.handle_call(sample_request)

            assert len(result.content) > 0
            assert "Notebook Details" in result.content[0].text
            assert "0" in result.content[0].text and "Cells" in result.content[0].text

    @pytest.mark.asyncio
    async def test_get_notebook_not_found(self, sample_request, mock_env_credentials):
        """Test getting non-existent notebook"""
        sample_request.arguments = {"notebook_id": "notebook-nonexistent"}

        with patch(
            "datadog_mcp.tools.get_notebook.client_get_notebook", new_callable=AsyncMock
        ) as mock_get:
            mock_get.side_effect = Exception("404 Not Found")

            result = await get_notebook.handle_call(sample_request)

            assert len(result.content) > 0
            assert "Error fetching notebook" in result.content[0].text

    @pytest.mark.asyncio
    async def test_get_notebook_with_none_tags(self, sample_request, mock_env_credentials):
        """Test retrieving notebook when tags is None (API response variance)"""
        sample_request.arguments = {"notebook_id": SAMPLE_NOTEBOOK_ID}

        notebook_with_none_tags = {
            "id": SAMPLE_NOTEBOOK_ID,
            "type": "notebook",
            "attributes": {
                "name": "Test Notebook",
                "description": "Testing",
                "author": "test@example.com",
                "created": "2026-02-05T10:00:00Z",
                "updated": "2026-02-05T10:00:00Z",
                "tags": None,  # API sometimes returns None instead of []
                "cells": [],
            },
        }

        with patch(
            "datadog_mcp.tools.get_notebook.client_get_notebook", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = notebook_with_none_tags

            result = await get_notebook.handle_call(sample_request)

            assert len(result.content) > 0
            assert "Notebook Details" in result.content[0].text
            assert "Error" not in result.content[0].text  # Should not error on None tags


class TestUpdateNotebook:
    """Tests for update_notebook tool"""

    def test_update_notebook_definition(self):
        """Test update_notebook tool definition structure"""
        tool_def = update_notebook.get_tool_definition()
        assert tool_def.name == "update_notebook"
        assert "update" in tool_def.description.lower()
        assert "notebook_id" in tool_def.inputSchema["properties"]
        assert "notebook_id" in tool_def.inputSchema["required"]

    @pytest.mark.asyncio
    async def test_update_notebook_success(self, sample_request, mock_env_credentials):
        """Test successful notebook update"""
        sample_request.arguments = {
            "notebook_id": SAMPLE_NOTEBOOK_ID,
            "title": "Updated Investigation Title",
            "description": "New description",
            "tags": ["updated", "investigation"],
        }

        updated_response = {**SAMPLE_NOTEBOOK_RESPONSE}
        updated_response["attributes"]["name"] = "Updated Investigation Title"
        updated_response["attributes"]["description"] = "New description"
        updated_response["attributes"]["tags"] = ["updated", "investigation"]

        with patch(
            "datadog_mcp.tools.update_notebook.client_update_notebook",
            new_callable=AsyncMock,
        ) as mock_update:
            mock_update.return_value = updated_response

            result = await update_notebook.handle_call(sample_request)

            assert len(result.content) > 0
            assert "Notebook Updated" in result.content[0].text
            assert "Updated Investigation Title" in result.content[0].text
            assert "New description" in result.content[0].text

    @pytest.mark.asyncio
    async def test_update_notebook_partial(self, sample_request, mock_env_credentials):
        """Test updating only some notebook fields"""
        sample_request.arguments = {
            "notebook_id": SAMPLE_NOTEBOOK_ID,
            "title": "New Title Only",
        }

        with patch(
            "datadog_mcp.tools.update_notebook.client_update_notebook",
            new_callable=AsyncMock,
        ) as mock_update:
            mock_update.return_value = SAMPLE_NOTEBOOK_RESPONSE

            result = await update_notebook.handle_call(sample_request)

            assert len(result.content) > 0
            assert "Notebook Updated" in result.content[0].text

    @pytest.mark.asyncio
    async def test_update_notebook_bad_request(self, sample_request, mock_env_credentials):
        """Test handling 400 Bad Request error when updating notebook"""
        sample_request.arguments = {
            "notebook_id": SAMPLE_NOTEBOOK_ID,
            "title": "Updated Title",
        }

        with patch(
            "datadog_mcp.tools.update_notebook.client_update_notebook",
            new_callable=AsyncMock,
        ) as mock_update:
            # Simulate 400 Bad Request error from API
            mock_update.side_effect = Exception("400 Bad Request: Invalid request body")

            result = await update_notebook.handle_call(sample_request)

            assert len(result.content) > 0
            assert "Error updating notebook" in result.content[0].text
            assert "400" in result.content[0].text or "Bad Request" in result.content[0].text


class TestAddNotebookCell:
    """Tests for add_notebook_cell tool"""

    def test_add_notebook_cell_definition(self):
        """Test add_notebook_cell tool definition structure"""
        tool_def = add_notebook_cell.get_tool_definition()
        assert tool_def.name == "add_notebook_cell"
        assert "add" in tool_def.description.lower()
        assert "notebook_id" in tool_def.inputSchema["properties"]
        assert "cell_type" in tool_def.inputSchema["properties"]
        assert "position" in tool_def.inputSchema["properties"]
        assert set(tool_def.inputSchema["required"]) == {
            "notebook_id",
            "cell_type",
        }

    @pytest.mark.asyncio
    async def test_add_markdown_cell(self, sample_request, mock_env_credentials):
        """Test adding markdown cell"""
        sample_request.arguments = {
            "notebook_id": SAMPLE_NOTEBOOK_ID,
            "cell_type": "markdown",
            "position": 0,
            "title": "Analysis",
            "content": "# Root Cause\n\nThe issue was caused by...",
        }

        updated_notebook = {**SAMPLE_NOTEBOOK_RESPONSE}
        updated_notebook["attributes"]["cells"].insert(0, {
            "id": "cell-new",
            "type": "markdown",
            "title": "Analysis",
        })

        with patch(
            "datadog_mcp.tools.add_notebook_cell.client_add_notebook_cell",
            new_callable=AsyncMock,
        ) as mock_add:
            mock_add.return_value = updated_notebook

            result = await add_notebook_cell.handle_call(sample_request)

            assert len(result.content) > 0
            assert "Cell Added to Notebook" in result.content[0].text
            assert "markdown" in result.content[0].text
            assert "position" in result.content[0].text.lower() and "0" in result.content[0].text

    @pytest.mark.asyncio
    async def test_add_timeseries_cell(self, sample_request, mock_env_credentials):
        """Test adding timeseries cell"""
        sample_request.arguments = {
            "notebook_id": SAMPLE_NOTEBOOK_ID,
            "cell_type": "timeseries",
            "position": 1,
            "title": "Request Latency",
            "query": "avg:trace.web.request.duration{*}",
            "visualization": "line_chart",
        }

        with patch(
            "datadog_mcp.tools.add_notebook_cell.client_add_notebook_cell",
            new_callable=AsyncMock,
        ) as mock_add:
            mock_add.return_value = SAMPLE_NOTEBOOK_RESPONSE

            result = await add_notebook_cell.handle_call(sample_request)

            assert len(result.content) > 0
            assert "Cell Added to Notebook" in result.content[0].text
            assert "timeseries" in result.content[0].text

    @pytest.mark.asyncio
    async def test_add_cell_error(self, sample_request, mock_env_credentials):
        """Test error adding cell"""
        sample_request.arguments = {
            "notebook_id": SAMPLE_NOTEBOOK_ID,
            "cell_type": "invalid_type",
            "position": 0,
        }

        with patch(
            "datadog_mcp.tools.add_notebook_cell.client_add_notebook_cell", new_callable=AsyncMock
        ) as mock_add:
            mock_add.side_effect = Exception("Invalid cell type")

            result = await add_notebook_cell.handle_call(sample_request)

            assert len(result.content) > 0
            assert "Error adding cell" in result.content[0].text

    @pytest.mark.asyncio
    async def test_add_cell_notebook_not_found(self, sample_request, mock_env_credentials):
        """Test adding cell to non-existent notebook"""
        sample_request.arguments = {
            "notebook_id": "notebook-doesnotexist",
            "cell_type": "markdown",
            "position": 0,
            "title": "Test",
            "content": "Test content",
        }

        with patch(
            "datadog_mcp.tools.add_notebook_cell.client_add_notebook_cell",
            new_callable=AsyncMock,
        ) as mock_add:
            # Simulate the error that occurs in production when notebook doesn't exist
            mock_add.side_effect = Exception("Notebook not found")

            result = await add_notebook_cell.handle_call(sample_request)

            assert len(result.content) > 0
            assert "Error adding cell" in result.content[0].text
            assert "Notebook not found" in result.content[0].text


class TestUpdateNotebookCell:
    """Tests for update_notebook_cell tool"""

    def test_update_notebook_cell_definition(self):
        """Test update_notebook_cell tool definition structure"""
        tool_def = update_notebook_cell.get_tool_definition()
        assert tool_def.name == "update_notebook_cell"
        assert "update" in tool_def.description.lower()
        assert "notebook_id" in tool_def.inputSchema["properties"]
        assert "cell_id" in tool_def.inputSchema["properties"]

    @pytest.mark.asyncio
    async def test_update_cell_content(self, sample_request, mock_env_credentials):
        """Test updating cell content"""
        sample_request.arguments = {
            "notebook_id": SAMPLE_NOTEBOOK_ID,
            "cell_id": "cell-001",
            "title": "Updated Title",
            "content": "# Updated Content\n\nNew analysis...",
        }

        with patch(
            "datadog_mcp.tools.update_notebook_cell.client_update_notebook_cell",
            new_callable=AsyncMock,
        ) as mock_update:
            mock_update.return_value = SAMPLE_NOTEBOOK_RESPONSE

            result = await update_notebook_cell.handle_call(sample_request)

            assert len(result.content) > 0
            assert "Notebook Cell Updated" in result.content[0].text
            assert "Updated Title" in result.content[0].text

    @pytest.mark.asyncio
    async def test_update_cell_query(self, sample_request, mock_env_credentials):
        """Test updating cell query"""
        sample_request.arguments = {
            "notebook_id": SAMPLE_NOTEBOOK_ID,
            "cell_id": "cell-002",
            "query": "avg:trace.web.request.errors{service:*}",
            "visualization": "bar",
        }

        with patch(
            "datadog_mcp.tools.update_notebook_cell.client_update_notebook_cell",
            new_callable=AsyncMock,
        ) as mock_update:
            mock_update.return_value = SAMPLE_NOTEBOOK_RESPONSE

            result = await update_notebook_cell.handle_call(sample_request)

            assert len(result.content) > 0
            assert "Notebook Cell Updated" in result.content[0].text


class TestDeleteNotebookCell:
    """Tests for delete_notebook_cell tool"""

    def test_delete_notebook_cell_definition(self):
        """Test delete_notebook_cell tool definition structure"""
        tool_def = delete_notebook_cell.get_tool_definition()
        assert tool_def.name == "delete_notebook_cell"
        assert "delete" in tool_def.description.lower()
        assert "notebook_id" in tool_def.inputSchema["properties"]
        assert "cell_id" in tool_def.inputSchema["properties"]

    @pytest.mark.asyncio
    async def test_delete_cell_success(self, sample_request, mock_env_credentials):
        """Test successful cell deletion"""
        sample_request.arguments = {
            "notebook_id": SAMPLE_NOTEBOOK_ID,
            "cell_id": "cell-001",
        }

        deleted_notebook = {
            "id": SAMPLE_NOTEBOOK_ID,
            "type": "notebook",
            "attributes": {
                **SAMPLE_NOTEBOOK_RESPONSE["attributes"],
                "cells": SAMPLE_NOTEBOOK_RESPONSE["attributes"]["cells"][1:],
            },
        }

        with patch(
            "datadog_mcp.tools.delete_notebook_cell.client_delete_notebook_cell",
            new_callable=AsyncMock,
        ) as mock_delete:
            mock_delete.return_value = deleted_notebook

            result = await delete_notebook_cell.handle_call(sample_request)

            assert len(result.content) > 0
            assert "Cell Deleted from Notebook" in result.content[0].text
            assert "cell-001" in result.content[0].text
            assert "Remaining Cells" in result.content[0].text

    @pytest.mark.asyncio
    async def test_delete_cell_not_found(self, sample_request, mock_env_credentials):
        """Test deleting non-existent cell"""
        sample_request.arguments = {
            "notebook_id": SAMPLE_NOTEBOOK_ID,
            "cell_id": "cell-nonexistent",
        }

        with patch(
            "datadog_mcp.tools.delete_notebook_cell.client_delete_notebook_cell",
            new_callable=AsyncMock,
        ) as mock_delete:
            mock_delete.side_effect = Exception("Cell not found")

            result = await delete_notebook_cell.handle_call(sample_request)

            assert len(result.content) > 0
            assert "Error deleting notebook cell" in result.content[0].text


class TestDeleteNotebook:
    """Tests for delete_notebook tool"""

    def test_delete_notebook_definition(self):
        """Test delete_notebook tool definition structure"""
        tool_def = delete_notebook.get_tool_definition()
        assert tool_def.name == "delete_notebook"
        assert "delete" in tool_def.description.lower()
        assert "notebook_id" in tool_def.inputSchema["properties"]
        assert "notebook_id" in tool_def.inputSchema["required"]

    @pytest.mark.asyncio
    async def test_delete_notebook_success(self, sample_request, mock_env_credentials):
        """Test successful notebook deletion"""
        sample_request.arguments = {"notebook_id": SAMPLE_NOTEBOOK_ID}

        with patch(
            "datadog_mcp.tools.delete_notebook.client_delete_notebook", new_callable=AsyncMock
        ) as mock_delete:
            mock_delete.return_value = {}

            result = await delete_notebook.handle_call(sample_request)

            assert len(result.content) > 0
            assert "Notebook Deleted" in result.content[0].text
            assert SAMPLE_NOTEBOOK_ID in result.content[0].text
            assert "Successfully deleted" in result.content[0].text

    @pytest.mark.asyncio
    async def test_delete_notebook_not_found(self, sample_request, mock_env_credentials):
        """Test deleting non-existent notebook"""
        sample_request.arguments = {"notebook_id": "notebook-nonexistent"}

        with patch(
            "datadog_mcp.tools.delete_notebook.client_delete_notebook", new_callable=AsyncMock
        ) as mock_delete:
            mock_delete.side_effect = Exception("404 Not Found")

            result = await delete_notebook.handle_call(sample_request)

            assert len(result.content) > 0
            assert "Error deleting notebook" in result.content[0].text
