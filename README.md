# Datadog MCP Server

[![CircleCI](https://img.shields.io/circleci/build/github/hacctarr/datadog-mcp/main?style=flat&logo=circleci)](https://circleci.com/gh/hacctarr/datadog-mcp/tree/main)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://python.org)
[![UV](https://img.shields.io/badge/uv-package%20manager-blue)](https://github.com/astral-sh/uv)
[![Podman](https://img.shields.io/badge/podman-892CA0?style=flat&logo=podman&logoColor=white)](https://podman.io)
[![GitHub release](https://img.shields.io/github/v/release/hacctarr/datadog-mcp)](https://github.com/hacctarr/datadog-mcp/releases)

A Model Context Protocol (MCP) server that provides comprehensive Datadog monitoring capabilities through Claude Desktop and other MCP clients.

## Features

This MCP server enables Claude to:

- **CI/CD Pipeline Management**: List CI pipelines, extract fingerprints
- **Service Logs Analysis**: Retrieve and analyze service logs with environment and time filtering  
- **Metrics Monitoring**: Query any Datadog metric with flexible filtering, aggregation, and field discovery
- **Monitoring & Alerting**: List and manage Datadog monitors and Service Level Objectives (SLOs)
- **Service Definitions**: List and retrieve detailed service definitions with metadata, ownership, and configuration
- **Team Management**: List teams, view member details, and manage team information

## Installation

Choose your preferred method to run the Datadog MCP server:

### 🚀 UVX Direct Run (Recommended)

Install and run directly from GitHub without cloning:

```bash
export DD_API_KEY="your-datadog-api-key" DD_APP_KEY="your-datadog-application-key"

# Latest version (HEAD)
uvx --from git+https://github.com/hacctarr/datadog-mcp.git datadog-mcp

# Specific version (recommended for production)
# Replace LATEST_VERSION with actual version from https://github.com/hacctarr/datadog-mcp/releases
uvx --from git+https://github.com/hacctarr/datadog-mcp.git@LATEST_VERSION datadog-mcp

# Specific branch
uvx --from git+https://github.com/hacctarr/datadog-mcp.git@main datadog-mcp
```

### 🔧 UV Quick Run (Development)

For local development and testing:

```bash
git clone https://github.com/hacctarr/datadog-mcp.git
cd datadog-mcp
uv sync
export DD_API_KEY="your-datadog-api-key"
export DD_APP_KEY="your-datadog-application-key"
uv run datadog_mcp/server.py
```

### 🐳 Podman (Optional)

For containerized environments:

```bash
podman run -e DD_API_KEY="your-datadog-api-key" -e DD_APP_KEY="your-datadog-application-key" -i $(podman build -q https://github.com/hacctarr/datadog-mcp.git)
```

**Method Comparison:**

| Method | Speed | Latest Code | Setup | Best For |
|--------|-------|-------------|-------|----------|
| 🚀 UVX Direct Run | ⚡⚡⚡ | ✅ (versioned) | Minimal | Production, Claude Desktop |
| 🔧 UV Quick Run | ⚡⚡ | ✅ (bleeding edge) | Clone Required | Development, Testing |
| 🐳 Podman | ⚡ | ✅ (bleeding edge) | Podman Required | Containerized Environments |

## Requirements

### For UVX/UV Methods  
- Python 3.13+
- UV package manager (includes uvx)
- Datadog API Key and Application Key

### For Podman Method
- Podman
- Datadog API Key and Application Key

## Version Management

When using UVX, you can specify exact versions for reproducible deployments:

### Version Formats
- **Latest**: `git+https://github.com/hacctarr/datadog-mcp.git` (HEAD)
- **Specific Tag**: `git+https://github.com/hacctarr/datadog-mcp.git@LATEST_VERSION` (e.g., `@v0.3.3`)
- **Branch**: `git+https://github.com/hacctarr/datadog-mcp.git@main`
- **Commit Hash**: `git+https://github.com/hacctarr/datadog-mcp.git@COMMIT_HASH`

### Recommendations
- **Production**: Use specific tags (e.g., `@v0.3.0`) for stability
- **Development**: Use latest or specific branch for newest features
- **Testing**: Use commit hashes for exact reproducibility

See [GitHub releases](https://github.com/hacctarr/datadog-mcp/releases) for all available versions.

## Claude Desktop Integration

Add to your Claude Desktop configuration (usually `~/.claude/claude_desktop_config.json`):

**Using UVX (Recommended for production)**:
```json
{
  "mcpServers": {
    "datadog": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/hacctarr/datadog-mcp.git@LATEST_VERSION", "datadog-mcp"],
      "env": {
        "DD_API_KEY": "your-datadog-api-key",
        "DD_APP_KEY": "your-datadog-application-key"
      }
    }
  }
}
```

Replace `LATEST_VERSION` with the version from [GitHub releases](https://github.com/hacctarr/datadog-mcp/releases) (e.g., `v0.3.3`).

**Using local development setup**:
```json
{
  "mcpServers": {
    "datadog": {
      "command": "uv",
      "args": ["run", "datadog_mcp/server.py"],
      "cwd": "/path/to/datadog-mcp",
      "env": {
        "DD_API_KEY": "your-datadog-api-key",
        "DD_APP_KEY": "your-datadog-application-key"
      }
    }
  }
}
```

## Tools

The server provides these tools to Claude:

### `list_ci_pipelines`
Lists all CI pipelines registered in Datadog with filtering options.

**Arguments:**
- `repository` (optional): Filter by repository name
- `pipeline_name` (optional): Filter by pipeline name  
- `format` (optional): Output format - "table", "json", or "summary"

### `get_pipeline_fingerprints` 
Extracts pipeline fingerprints for use in Terraform service definitions.

**Arguments:**
- `repository` (optional): Filter by repository name
- `pipeline_name` (optional): Filter by pipeline name
- `format` (optional): Output format - "table", "json", or "summary"

### `list_metrics`
Lists all available metrics from Datadog for metric discovery.

**Arguments:**
- `filter` (optional): Filter to search for metrics by tags (e.g., 'aws:*', 'env:*', 'service:web')
- `limit` (optional): Maximum number of metrics to return (default: 100, max: 10000)

### `get_metrics`
Queries any Datadog metric with flexible filtering and aggregation.

**Arguments:**
- `metric_name` (required): The metric name to query (e.g., 'aws.apigateway.count', 'system.cpu.user')
- `time_range` (optional): "1h", "4h", "8h", "1d", "7d", "14d", "30d"
- `aggregation` (optional): "avg", "sum", "min", "max", "count"
- `filters` (optional): Dictionary of filters to apply (e.g., {'service': 'web', 'env': 'prod'})
- `aggregation_by` (optional): List of fields to group results by
- `format` (optional): "table", "summary", "json", "timeseries"

### `get_metric_fields`
Retrieves all available fields (tags) for a specific metric.

**Arguments:**
- `metric_name` (required): The metric name to get fields for
- `time_range` (optional): "1h", "4h", "8h", "1d", "7d", "14d", "30d"

### `get_metric_field_values`
Retrieves all values for a specific field of a metric.

**Arguments:**
- `metric_name` (required): The metric name
- `field_name` (required): The field name to get values for
- `time_range` (optional): "1h", "4h", "8h", "1d", "7d", "14d", "30d"

### `list_service_definitions`
Lists all service definitions from Datadog with pagination and filtering.

**Arguments:**
- `page_size` (optional): Number of service definitions per page (default: 10, max: 100)
- `page_number` (optional): Page number for pagination (0-indexed, default: 0)
- `schema_version` (optional): Filter by schema version (e.g., 'v2', 'v2.1', 'v2.2')
- `format` (optional): Output format - "table", "json", or "summary"

### `get_service_definition`
Retrieves the definition of a specific service with detailed metadata.

**Arguments:**
- `service_name` (required): Name of the service to retrieve
- `schema_version` (optional): Schema version to retrieve (default: "v2.2", options: "v1", "v2", "v2.1", "v2.2")
- `format` (optional): Output format - "formatted", "json", or "yaml"

### `get_service_logs`
Retrieves service logs with comprehensive filtering capabilities.

**Arguments:**
- `service_name` (required): Name of the service
- `time_range` (required): "1h", "4h", "8h", "1d", "7d", "14d", "30d"
- `environment` (optional): "prod", "staging", "backoffice"
- `log_level` (optional): "INFO", "ERROR", "WARN", "DEBUG"
- `format` (optional): "table", "text", "json", "summary"

### `list_monitors`
Lists all Datadog monitors with comprehensive filtering options.

**Arguments:**
- `name` (optional): Filter monitors by name (substring match)
- `tags` (optional): Filter monitors by tags (e.g., 'env:prod,service:web')
- `monitor_tags` (optional): Filter monitors by monitor tags (e.g., 'team:backend')
- `page_size` (optional): Number of monitors per page (default: 50, max: 1000)
- `page` (optional): Page number (0-indexed, default: 0)
- `format` (optional): Output format - "table", "json", or "summary"

### `list_slos`
Lists Service Level Objectives (SLOs) from Datadog with filtering capabilities.

**Arguments:**
- `query` (optional): Filter SLOs by name or description (substring match)
- `tags` (optional): Filter SLOs by tags (e.g., 'team:backend,env:prod')
- `limit` (optional): Maximum number of SLOs to return (default: 50, max: 1000)
- `offset` (optional): Number of SLOs to skip (default: 0)
- `format` (optional): Output format - "table", "json", or "summary"

### `get_teams`
Lists teams and their members.

**Arguments:**
- `team_name` (optional): Filter by team name
- `include_members` (optional): Include member details (default: false)
- `format` (optional): "table", "json", "summary"

### `get_logs`
Retrieves logs from Datadog with flexible filtering.

**Arguments:**
- `query` (optional): Free-text search query (e.g., 'error OR exception')
- `filters` (optional): Dictionary of filters (e.g., {'service': 'web', 'status': 'error'})
- `time_range` (optional): "1h", "4h", "8h", "1d", "7d", "14d", "30d"
- `limit` (optional): Maximum number of log entries (default: 50, max: 1000)
- `format` (optional): "table", "text", "json"

### `query_metric_formula`
Execute metric formulas for comparing/calculating multiple metrics.

**Arguments:**
- `formula` (required): Formula string using query variables (e.g., 'a / b * 100')
- `queries` (required): Dictionary of metric queries with aggregation options
- `filters` (optional): Filters to apply to all queries
- `time_range` (optional): "1h", "4h", "8h", "1d", "7d", "14d", "30d"
- `format` (optional): "summary", "timeseries", "json"

### `check_deployment`
Verify if a specific version is deployed to a service.

**Arguments:**
- `service` (required): Service name to check
- `version_field` (required): Field name containing version info
- `version_value` (required): Version value to search for
- `environment` (optional): Environment filter (e.g., 'prod', 'staging')
- `time_range` (optional): "1h", "4h", "8h", "1d", "7d", "14d", "30d"
- `format` (optional): "summary", "detailed", "json"

### `get_traces`
Search and retrieve APM traces from Datadog.

**Arguments:**
- `query` (optional): Trace query string (e.g., '@duration:>5000000000')
- `time_range` (optional): "1h", "4h", "8h", "1d", "7d", "14d", "30d"
- `limit` (optional): Maximum number of traces (default: 10, max: 100)
- `include_children` (optional): Include child spans (default: false)
- `format` (optional): "table", "text", "json"

### `aggregate_traces`
Aggregate APM traces by grouping by specified dimensions.

**Arguments:**
- `query` (optional): Trace query string
- `group_by` (optional): Fields to group by (e.g., ['service.name'])
- `aggregation` (optional): Aggregation function - "count", "avg", "min", "max", "sum", "percentile"
- `time_range` (optional): "1h", "4h", "8h", "1d", "7d", "14d", "30d"
- `format` (optional): "table", "text", "json"

### `list_notebooks`
List all Datadog notebooks for organizing analysis and investigations.

**Arguments:**
- `limit` (optional): Maximum number of notebooks (default: 20, max: 100)
- `offset` (optional): Offset for pagination (default: 0)
- `format` (optional): "table", "json", "summary"

### `get_notebook`
Retrieve a specific notebook by ID with all cells and metadata.

**Arguments:**
- `notebook_id` (required): The notebook ID to retrieve

### `create_notebook`
Create a new notebook for analysis and investigations.

**Arguments:**
- `title` (required): Title of the notebook
- `description` (optional): Description of the notebook's purpose
- `cells` (optional): Initial cells for the notebook
- `tags` (optional): Tags for organizing notebooks

### `update_notebook`
Update an existing notebook's metadata.

**Arguments:**
- `notebook_id` (required): The notebook ID to update
- `title` (optional): New title for the notebook
- `description` (optional): New description
- `tags` (optional): New tags for the notebook

### `add_notebook_cell`
Add a new cell to a notebook.

**Arguments:**
- `notebook_id` (required): The notebook ID
- `cell_type` (required): Type of cell - "markdown", "timeseries", "log_stream", "trace_list", "query_value"
- `content` (optional): Content for markdown cells
- `query` (optional): Query for metric/log/APM cells
- `title` (optional): Title for the cell
- `visualization` (optional): Visualization type for timeseries cells
- `position` (optional): Position in the notebook

### `update_notebook_cell`
Update an existing cell in a notebook.

**Arguments:**
- `notebook_id` (required): The notebook ID containing the cell
- `cell_id` (required): The cell ID to update
- `content` (optional): New content for markdown cells
- `query` (optional): New query for metric/log/APM cells
- `title` (optional): New title
- `visualization` (optional): New visualization type
- `position` (optional): New position in notebook

### `delete_notebook_cell`
Delete a cell from a notebook.

**Arguments:**
- `notebook_id` (required): The notebook ID
- `cell_id` (required): The cell ID to delete

### `delete_notebook`
Delete a notebook by ID.

**Arguments:**
- `notebook_id` (required): The notebook ID to delete

### `setup_auth`
Setup or verify Datadog authentication.

**Arguments:**
- `action` (optional): Action to perform - "detect", "configure_cookie", "configure_token", "verify", "status"
- `api_key` (optional): Datadog API key (for configure_token)
- `app_key` (optional): Datadog application key (for configure_token)
- `cookie_value` (optional): Cookie value (for configure_cookie)
- `csrf_token` (optional): CSRF token (for configure_cookie)

## Examples

Ask Claude to help you with:

```
"Show me all CI pipelines for the shelf-api repository"

"Get error logs for the content service in the last 4 hours"

"List all available AWS metrics"

"What are the latest metrics for aws.apigateway.count grouped by account?"

"Get all available fields for the system.cpu.user metric"

"List all service definitions in my organization"

"Get the definition for the user-api service"

"List all teams and their members"

"Show all monitors for the web service"

"List SLOs with less than 99% uptime"

"Extract pipeline fingerprints for Terraform configuration"
```

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DD_API_KEY` | Datadog API Key | Yes |
| `DD_APP_KEY` | Datadog Application Key | Yes |

### Obtaining Datadog Credentials

1. Log in to your Datadog account
2. Go to **Organization Settings** → **API Keys**
3. Create or copy your **API Key** (this is your `DD_API_KEY`)
4. Go to **Organization Settings** → **Application Keys**
5. Create or copy your **Application Key** (this is your `DD_APP_KEY`)

**Note:** These are two different keys:
- **API Key**: Used for authentication with Datadog's API
- **Application Key**: Used for authorization and is tied to a specific user account
