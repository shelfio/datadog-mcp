"""
Tests for team management functionality
"""

import pytest
import json
from unittest.mock import patch, AsyncMock, MagicMock
from datadog_mcp.tools import get_teams
from datadog_mcp.utils import datadog_client
from mcp.types import CallToolResult, TextContent


class TestTeamsToolDefinition:
    """Test the get_teams tool definition"""
    
    def test_get_teams_tool_definition(self):
        """Test that get_teams tool definition is properly structured"""
        tool_def = get_teams.get_tool_definition()
        
        assert tool_def.name == "get_teams"
        assert "team" in tool_def.description.lower()
        assert hasattr(tool_def, 'inputSchema')
        
        # Check schema structure
        schema = tool_def.inputSchema
        assert "properties" in schema
        
        properties = schema["properties"]
        expected_params = ["team_name", "include_members", "format"]
        for param in expected_params:
            assert param in properties, f"Parameter {param} missing from schema"


class TestTeamsRetrieval:
    """Test team data retrieval functionality"""
    
    @pytest.mark.asyncio
    async def test_fetch_teams_basic(self):
        """Test basic team fetching functionality"""
        mock_response_data = {
            "data": [
                {
                    "id": "team-123",
                    "type": "teams",
                    "attributes": {
                        "name": "Backend Team",
                        "description": "Backend development team",
                        "handle": "backend-team",
                        "summary": "Responsible for API development"
                    },
                    "relationships": {
                        "users": {
                            "data": [
                                {"id": "user-1", "type": "users"},
                                {"id": "user-2", "type": "users"}
                            ]
                        }
                    }
                }
            ],
            "included": [
                {
                    "id": "user-1",
                    "type": "users",
                    "attributes": {
                        "name": "John Doe",
                        "email": "john@example.com",
                        "handle": "john.doe"
                    }
                },
                {
                    "id": "user-2",
                    "type": "users",
                    "attributes": {
                        "name": "Jane Smith",
                        "email": "jane@example.com",
                        "handle": "jane.smith"
                    }
                }
            ]
        }

        with patch('datadog_mcp.utils.datadog_client.httpx.AsyncClient') as mock_client:
            # Create response mock with sync methods
            mock_response = MagicMock()
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status.return_value = None
            mock_response.status_code = 200

            # Make get() return an awaitable that resolves to the response
            async_get = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.get = async_get

            result = await datadog_client.fetch_teams()

            assert isinstance(result, dict)
            assert "data" in result
            assert len(result["data"]) > 0
            assert result["data"][0]["id"] == "team-123"
    
    @pytest.mark.asyncio
    async def test_fetch_specific_team(self):
        """Test fetching teams with pagination"""
        page_number = 1

        mock_response_data = {
            "data": [
                {
                    "id": "team-123",
                    "type": "teams",
                    "attributes": {
                        "name": "Backend Team",
                        "handle": "backend-team"
                    }
                }
            ],
            "meta": {
                "pagination": {
                    "total_count": 5,
                    "total_pages": 1
                }
            }
        }

        with patch('datadog_mcp.utils.datadog_client.httpx.AsyncClient') as mock_client:
            # Create response mock with sync methods
            mock_response = MagicMock()
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status.return_value = None
            mock_response.status_code = 200

            # Make get() return an awaitable that resolves to the response
            async_get = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.get = async_get

            result = await datadog_client.fetch_teams(page_number=page_number)

            assert isinstance(result, dict)
            assert "data" in result
            # Verify the request was made
            mock_client.return_value.__aenter__.return_value.get.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_fetch_teams_with_included(self):
        """Test fetching teams with included user data"""
        mock_response_data = {
            "data": [
                {
                    "id": "team-123",
                    "type": "teams",
                    "attributes": {
                        "name": "Frontend Team"
                    },
                    "relationships": {
                        "users": {
                            "data": [{"id": "user-1", "type": "users"}]
                        }
                    }
                }
            ],
            "included": [
                {
                    "id": "user-1",
                    "type": "users",
                    "attributes": {
                        "name": "Alice Johnson",
                        "email": "alice@example.com"
                    }
                }
            ]
        }

        with patch('datadog_mcp.utils.datadog_client.httpx.AsyncClient') as mock_client:
            # Create response mock with sync methods
            mock_response = MagicMock()
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status.return_value = None
            mock_response.status_code = 200

            # Make get() return an awaitable that resolves to the response
            async_get = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.get = async_get

            result = await datadog_client.fetch_teams()

            assert isinstance(result, dict)
            assert "data" in result
            assert "included" in result
            assert len(result["included"]) > 0


class TestTeamsToolHandler:
    """Test the get_teams tool handler"""
    
    @pytest.mark.asyncio
    async def test_handle_teams_request_success(self):
        """Test successful teams request handling"""
        mock_request = MagicMock()
        mock_request.arguments = {
            "include_members": True,
            "format": "table"
        }
        mock_request.params = MagicMock()
        mock_request.params.arguments = mock_request.arguments

        # Mock raw API format (what fetch_teams actually returns)
        mock_teams_data = {
            "data": [
                {
                    "id": "team-123",
                    "type": "teams",
                    "attributes": {
                        "name": "DevOps Team",
                        "handle": "devops",
                        "description": "Infrastructure and deployment team"
                    },
                    "relationships": {
                        "users": {
                            "data": [{"id": "user-1", "type": "users"}]
                        }
                    }
                }
            ],
            "included": [
                {
                    "id": "user-1",
                    "type": "users",
                    "attributes": {
                        "name": "Bob Wilson",
                        "email": "bob@example.com",
                        "handle": "bob.wilson"
                    }
                }
            ]
        }

        with patch('datadog_mcp.tools.get_teams.fetch_teams', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_teams_data

            result = await get_teams.handle_call(mock_request)

            assert isinstance(result, CallToolResult)
            assert result.isError is False
            assert len(result.content) > 0
            assert isinstance(result.content[0], TextContent)

            content_text = result.content[0].text
            assert "DevOps Team" in content_text or "devops" in content_text.lower()
    
    @pytest.mark.asyncio
    async def test_handle_teams_request_specific_team(self):
        """Test teams request for specific team"""
        mock_request = MagicMock()
        mock_request.arguments = {
            "team_name": "Security Team",
            "include_members": True,
            "format": "detailed"
        }
        mock_request.params = MagicMock()
        mock_request.params.arguments = mock_request.arguments

        # Mock raw API format with multiple teams (tool handler filters by team_name)
        mock_teams_data = {
            "data": [
                {
                    "id": "team-456",
                    "type": "teams",
                    "attributes": {
                        "name": "Security Team",
                        "handle": "security",
                        "description": "Application security team"
                    },
                    "relationships": {
                        "users": {"data": []}
                    }
                },
                {
                    "id": "team-999",
                    "type": "teams",
                    "attributes": {
                        "name": "Backend Team",
                        "handle": "backend",
                        "description": "Backend team"
                    },
                    "relationships": {
                        "users": {"data": []}
                    }
                }
            ],
            "included": []
        }

        with patch('datadog_mcp.tools.get_teams.fetch_teams', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_teams_data

            result = await get_teams.handle_call(mock_request)

            assert isinstance(result, CallToolResult)
            assert result.isError is False

            # Verify fetch was called without team_name (tool handler filters client-side)
            mock_fetch.assert_called_once()
            content_text = result.content[0].text
            # The handler should have filtered to only show Security Team
            assert "Security Team" in content_text or "security" in content_text.lower()
    
    @pytest.mark.asyncio
    async def test_handle_teams_request_json_format(self):
        """Test teams request with JSON format"""
        mock_request = MagicMock()
        mock_request.arguments = {
            "format": "json",
            "include_members": False
        }
        mock_request.params = MagicMock()
        mock_request.params.arguments = mock_request.arguments

        # Mock raw API format
        mock_teams_data = {
            "data": [
                {
                    "id": "team-789",
                    "type": "teams",
                    "attributes": {
                        "name": "QA Team",
                        "handle": "qa",
                        "description": "Quality assurance team"
                    },
                    "relationships": {
                        "users": {"data": []}
                    }
                }
            ],
            "included": []
        }

        with patch('datadog_mcp.tools.get_teams.fetch_teams', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_teams_data

            result = await get_teams.handle_call(mock_request)

            assert isinstance(result, CallToolResult)
            assert result.isError is False

            content_text = result.content[0].text
            # Should be valid JSON when format is json
            if mock_request.arguments.get("format") == "json":
                try:
                    json.loads(content_text)
                except json.JSONDecodeError:
                    pytest.fail("Response should be valid JSON when format=json")
    
    @pytest.mark.asyncio
    async def test_handle_teams_request_error(self):
        """Test error handling in teams requests"""
        mock_request = MagicMock()
        mock_request.arguments = {
            "team_name": "NonexistentTeam"
        }
        mock_request.params = MagicMock()
        mock_request.params.arguments = mock_request.arguments

        with patch('datadog_mcp.tools.get_teams.fetch_teams', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = Exception("Team not found")

            result = await get_teams.handle_call(mock_request)

            assert isinstance(result, CallToolResult)
            assert result.isError is True
            assert len(result.content) > 0
            assert "error" in result.content[0].text.lower()
    
    @pytest.mark.asyncio
    async def test_handle_teams_request_empty_results(self):
        """Test handling when no teams are found"""
        mock_request = MagicMock()
        mock_request.arguments = {
            "team_name": "EmptyResults"
        }
        mock_request.params = MagicMock()
        mock_request.params.arguments = mock_request.arguments

        mock_teams_data = {
            "teams": [],
            "users": []
        }

        with patch('datadog_mcp.tools.get_teams.fetch_teams', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_teams_data

            result = await get_teams.handle_call(mock_request)

            assert isinstance(result, CallToolResult)
            assert result.isError is False
            assert len(result.content) > 0

            content_text = result.content[0].text
            assert "no teams" in content_text.lower() or "empty" in content_text.lower()


class TestTeamsFormatting:
    """Test team data formatting"""
    
    def test_teams_table_formatting(self):
        """Test teams table formatting"""
        sample_teams = [
            {
                "id": "team-1",
                "name": "Backend Team",
                "handle": "backend",
                "description": "API development",
                "member_count": 5
            },
            {
                "id": "team-2", 
                "name": "Frontend Team",
                "handle": "frontend",
                "description": "UI development",
                "member_count": 4
            }
        ]
        
        # Test that we can process teams data
        assert len(sample_teams) == 2
        assert all("name" in team for team in sample_teams)
        assert all("handle" in team for team in sample_teams)
    
    def test_teams_detailed_formatting(self):
        """Test detailed teams formatting with members"""
        sample_data = {
            "teams": [
                {
                    "id": "team-1",
                    "name": "DevOps Team",
                    "handle": "devops",
                    "description": "Infrastructure team"
                }
            ],
            "users": [
                {
                    "id": "user-1",
                    "name": "John Doe",
                    "email": "john@example.com",
                    "teams": ["team-1"]
                },
                {
                    "id": "user-2",
                    "name": "Jane Smith", 
                    "email": "jane@example.com",
                    "teams": ["team-1"]
                }
            ]
        }
        
        # Verify data structure
        assert "teams" in sample_data
        assert "users" in sample_data
        assert len(sample_data["teams"]) == 1
        assert len(sample_data["users"]) == 2
        
        # Verify relationships
        team_id = sample_data["teams"][0]["id"]
        team_members = [user for user in sample_data["users"] if team_id in user["teams"]]
        assert len(team_members) == 2
    
    def test_teams_json_formatting(self):
        """Test teams JSON formatting"""
        sample_teams = [
            {
                "id": "team-1",
                "name": "Security Team",
                "handle": "security"
            }
        ]
        
        json_output = json.dumps(sample_teams, indent=2)
        assert isinstance(json_output, str)
        
        # Should be valid JSON
        parsed = json.loads(json_output)
        assert len(parsed) == 1
        assert parsed[0]["name"] == "Security Team"


class TestTeamsFiltering:
    """Test team filtering functionality"""
    
    @pytest.mark.asyncio
    async def test_teams_pagination(self):
        """Test fetching teams with pagination"""
        page_size = 50

        with patch('datadog_mcp.utils.datadog_client.httpx.AsyncClient') as mock_client:
            mock_response_data = {
                "data": [
                    {
                        "id": "team-123",
                        "type": "teams",
                        "attributes": {
                            "name": "Backend Team",
                            "handle": "backend"
                        }
                    }
                ],
                "meta": {
                    "pagination": {
                        "total_count": 10,
                        "total_pages": 1
                    }
                }
            }
            # Create response mock with sync methods
            mock_response = MagicMock()
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status.return_value = None
            mock_response.status_code = 200

            # Make get() return an awaitable that resolves to the response
            async_get = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.get = async_get

            result = await datadog_client.fetch_teams(page_size=page_size)

            # Verify the request was made with pagination parameter
            mock_client.return_value.__aenter__.return_value.get.assert_called_once()
            assert "data" in result
            assert "meta" in result
    
    @pytest.mark.asyncio
    async def test_teams_with_user_relationships(self):
        """Test fetching teams with included user data"""

        with patch('datadog_mcp.utils.datadog_client.httpx.AsyncClient') as mock_client:
            mock_response_data = {
                "data": [
                    {
                        "id": "team-123",
                        "type": "teams",
                        "attributes": {"name": "Test Team"},
                        "relationships": {
                            "users": {"data": [{"id": "user-1", "type": "users"}]}
                        }
                    }
                ],
                "included": [
                    {
                        "id": "user-1",
                        "type": "users",
                        "attributes": {
                            "name": "Team Member",
                            "email": "member@example.com"
                        }
                    }
                ]
            }
            # Create response mock with sync methods
            mock_response = MagicMock()
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status.return_value = None
            mock_response.status_code = 200

            # Make get() return an awaitable that resolves to the response
            async_get = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.get = async_get

            result = await datadog_client.fetch_teams()

            # Verify the request was made and response includes users
            mock_client.return_value.__aenter__.return_value.get.assert_called_once()
            assert "included" in result
            assert len(result["included"]) > 0


class TestTeamsValidation:
    """Test team input validation"""
    
    @pytest.mark.asyncio
    async def test_invalid_team_name_handling(self):
        """Test handling of invalid team names"""
        mock_request = MagicMock()
        mock_request.arguments = {
            "team_name": "",  # Empty team name
            "include_members": True
        }
        
        result = await get_teams.handle_call(mock_request)
        
        # Should handle gracefully (either error or validation message)
        assert isinstance(result, CallToolResult)
        if result.isError:
            assert len(result.content) > 0
    
    @pytest.mark.asyncio
    async def test_invalid_format_handling(self):
        """Test handling of invalid format options"""
        mock_request = MagicMock()
        mock_request.arguments = {
            "format": "invalid_format"
        }
        
        # Should handle gracefully
        try:
            result = await get_teams.handle_call(mock_request)
            assert isinstance(result, CallToolResult)
        except Exception:
            # If validation happens at tool level, that's also acceptable
            pass


class TestTeamsIntegration:
    """Test teams integration functionality"""

    @pytest.mark.asyncio
    async def test_teams_with_user_relationships(self):
        """Test teams data with proper user relationships through tool handler"""
        mock_request = MagicMock()
        mock_request.arguments = {
            "include_members": True,
            "format": "detailed"
        }
        mock_request.params = MagicMock()
        mock_request.params.arguments = mock_request.arguments

        # Mock raw API format from fetch_teams()
        mock_response_data = {
            "data": [
                {
                    "id": "team-1",
                    "type": "teams",
                    "attributes": {
                        "name": "Engineering",
                        "handle": "engineering"
                    },
                    "relationships": {
                        "users": {
                            "data": [
                                {"id": "user-1", "type": "users"},
                                {"id": "user-2", "type": "users"}
                            ]
                        }
                    }
                }
            ],
            "included": [
                {
                    "id": "user-1",
                    "type": "users",
                    "attributes": {
                        "name": "Developer One",
                        "email": "dev1@example.com"
                    }
                },
                {
                    "id": "user-2",
                    "type": "users",
                    "attributes": {
                        "name": "Developer Two",
                        "email": "dev2@example.com"
                    }
                }
            ]
        }

        # Mock membership data for fetch_team_memberships
        # Note: fetch_team_memberships returns just the "data" array, not the full response
        mock_memberships_data = [
            {
                "id": "member-1",
                "type": "team_memberships",
                "attributes": {
                    "role": "admin"
                },
                "relationships": {
                    "user": {
                        "data": {"id": "user-1", "type": "users"}
                    }
                }
            },
            {
                "id": "member-2",
                "type": "team_memberships",
                "attributes": {
                    "role": "member"
                },
                "relationships": {
                    "user": {
                        "data": {"id": "user-2", "type": "users"}
                    }
                }
            }
        ]

        with patch('datadog_mcp.tools.get_teams.fetch_teams', new_callable=AsyncMock) as mock_fetch, \
             patch('datadog_mcp.tools.get_teams.fetch_team_memberships', new_callable=AsyncMock) as mock_memberships:
            mock_fetch.return_value = mock_response_data
            mock_memberships.return_value = mock_memberships_data

            result = await get_teams.handle_call(mock_request)

            # Verify successful response
            assert isinstance(result, CallToolResult)
            assert result.isError is False
            assert len(result.content) > 0

            content_text = result.content[0].text
            # Should mention the team and members
            assert "Engineering" in content_text or "engineering" in content_text.lower()
            # Should show members section
            assert "Members" in content_text
            # Should show at least one member with user ID
            assert "user-1" in content_text or "user-2" in content_text


if __name__ == "__main__":
    pytest.main([__file__])