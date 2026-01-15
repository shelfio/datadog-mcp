# Datadog MCP Server

[![CircleCI](https://img.shields.io/circleci/build/github/shelfio/datadog-mcp/main?style=flat&logo=circleci)](https://circleci.com/gh/shelfio/datadog-mcp/tree/main)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://python.org)
[![UV](https://img.shields.io/badge/uv-package%20manager-blue)](https://github.com/astral-sh/uv)
[![Podman](https://img.shields.io/badge/podman-892CA0?style=flat&logo=podman&logoColor=white)](https://podman.io)
[![GitHub release](https://img.shields.io/github/v/release/shelfio/datadog-mcp)](https://github.com/shelfio/datadog-mcp/releases)

A Model Context Protocol (MCP) server that provides comprehensive Datadog monitoring capabilities through Claude Desktop and other MCP clients.

## Features

This MCP server enables Claude to:

- **CI/CD Pipeline Management**: List CI pipelines, extract fingerprints
- **Service Logs Analysis**: Retrieve and analyze service logs with environment and time filtering
- **Metrics Monitoring**: Query any Datadog metric with flexible filtering, aggregation, and field discovery
- **Monitoring & Alerting**: List and manage Datadog monitors and Service Level Objectives (SLOs)
- **Service Definitions**: List and retrieve detailed service definitions with metadata, ownership, and configuration
- **Dashboard Management**: Update dashboard titles and properties
- **Team Management**: List teams, view member details, and manage team information

## Quick Start

Choose your preferred method to run the Datadog MCP server:

### 🚀 UVX Direct Run (Recommended)
```bash
export DD_API_KEY="your-datadog-api-key" DD_APP_KEY="your-datadog-application-key"

# Latest version (HEAD)
uvx --from git+https://github.com/shelfio/datadog-mcp.git datadog-mcp

# Specific version (recommended for production)
uvx --from git+https://github.com/shelfio/datadog-mcp.git@v0.0.5 datadog-mcp

# Specific branch
uvx --from git+https://github.com/shelfio/datadog-mcp.git@main datadog-mcp
```

### 🔧 UV Quick Run (Development)
```bash
export DD_API_KEY="your-datadog-api-key" DD_APP_KEY="your-datadog-application-key"
git clone https://github.com/shelfio/datadog-mcp.git /tmp/datadog-mcp && cd /tmp/datadog-mcp && uv run ddmcp/server.py
```

### 🐳 Podman (Optional)
```bash
podman run -e DD_API_KEY="your-datadog-api-key" -e DD_APP_KEY="your-datadog-application-key" -i $(podman build -q https://github.com/shelfio/datadog-mcp.git)
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
- **Latest**: `git+https://github.com/shelfio/datadog-mcp.git` (HEAD)
- **Specific Tag**: `git+https://github.com/shelfio/datadog-mcp.git@v0.0.5`
- **Branch**: `git+https://github.com/shelfio/datadog-mcp.git@main`
- **Commit Hash**: `git+https://github.com/shelfio/datadog-mcp.git@59f0c15`

### Recommendations
- **Production**: Use specific tags (e.g., `@v0.0.5`) for stability
- **Development**: Use latest or specific branch for newest features
- **Testing**: Use commit hashes for exact reproducibility

See [GitHub releases](https://github.com/shelfio/datadog-mcp/releases) for all available versions.

## Claude Desktop Integration

### Using UVX (Recommended)

Add to Claude Desktop configuration:

**Latest version (bleeding edge)**:
```json
{
  "mcpServers": {
    "datadog": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/shelfio/datadog-mcp.git", "datadog-mcp"],
      "env": {
        "DD_API_KEY": "your-datadog-api-key",
        "DD_APP_KEY": "your-datadog-application-key"
      }
    }
  }
}
```

**Specific version (recommended for production)**:
```json
{
  "mcpServers": {
    "datadog": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/shelfio/datadog-mcp.git@v0.0.5", "datadog-mcp"],
      "env": {
        "DD_API_KEY": "your-datadog-api-key",
        "DD_APP_KEY": "your-datadog-application-key"
      }
    }
  }
}
```

**For EU region** (see [Multi-Region Support](#multi-region-support) for other regions):
```json
{
  "mcpServers": {
    "datadog": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/shelfio/datadog-mcp.git", "datadog-mcp"],
      "env": {
        "DD_API_KEY": "your-datadog-api-key",
        "DD_APP_KEY": "your-datadog-application-key",
        "DD_SITE": "datadoghq.eu"
      }
    }
  }
}
```

### Using Local Development Setup

For development with local cloned repository:
```bash
git clone https://github.com/shelfio/datadog-mcp.git
cd datadog-mcp
```

Add to Claude Desktop configuration:
```json
{
  "mcpServers": {
    "datadog": {
      "command": "uv",
      "args": ["run", "ddmcp/server.py"],
      "cwd": "/path/to/datadog-mcp",
      "env": {
        "DD_API_KEY": "your-datadog-api-key",
        "DD_APP_KEY": "your-datadog-application-key"
      }
    }
  }
}
```

## Installation Options

### UVX Installation (Recommended)

Install and run directly from GitHub without cloning:

```bash
export DD_API_KEY="your-datadog-api-key"
export DD_APP_KEY="your-datadog-application-key"

# Latest version
uvx --from git+https://github.com/shelfio/datadog-mcp.git datadog-mcp

# Specific version (recommended for production)
uvx --from git+https://github.com/shelfio/datadog-mcp.git@v0.0.5 datadog-mcp
```

### Development Installation

For local development and testing:

1. **Clone the repository:**
   ```bash
   git clone https://github.com/shelfio/datadog-mcp.git
   cd datadog-mcp
   ```

2. **Install dependencies:**
   ```bash
   uv sync
   ```

3. **Run the server:**
   ```bash
   export DD_API_KEY="your-datadog-api-key"
   export DD_APP_KEY="your-datadog-application-key"
   uv run ddmcp/server.py
   ```

### Podman Installation (Optional)

For containerized environments:

```bash
podman run -e DD_API_KEY="your-key" -e DD_APP_KEY="your-app-key" -i $(podman build -q https://github.com/shelfio/datadog-mcp.git)
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

### `dashboard_update_title`
Updates the title of an existing Datadog dashboard.

**Arguments:**
- `dashboard_id` (required): The ID of the dashboard to update (e.g., 'giw-w7a-maj'). Can be found in the dashboard URL.
- `new_title` (required): The new title for the dashboard.

### `get_teams`
Lists teams and their members.

**Arguments:**
- `team_name` (optional): Filter by team name
- `include_members` (optional): Include member details (default: false)
- `format` (optional): "table", "json", "summary"

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

"Update the title of dashboard giw-w7a-maj to 'Production Overview'"
```

## Configuration

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `DD_API_KEY` | Datadog API Key | Yes | - |
| `DD_APP_KEY` | Datadog Application Key | Yes | - |
| `DD_SITE` | Datadog site/region (see table below) | No | `datadoghq.com` |

### Multi-Region Support

Datadog operates in multiple regions. Set the `DD_SITE` environment variable to connect to your Datadog region:

| Region | DD_SITE Value | Description |
|--------|---------------|-------------|
| US1 | `datadoghq.com` | US (default) |
| US3 | `us3.datadoghq.com` | US3 |
| US5 | `us5.datadoghq.com` | US5 |
| EU1 | `datadoghq.eu` | Europe |
| AP1 | `ap1.datadoghq.com` | Asia Pacific (Japan) |
| US1-FED | `ddog-gov.com` | US Government |

**Example for EU region:**
```bash
export DD_SITE="datadoghq.eu"
export DD_API_KEY="your-api-key"
export DD_APP_KEY="your-app-key"
uvx --from git+https://github.com/shelfio/datadog-mcp.git datadog-mcp
```

See [Datadog's Getting Started with Sites](https://docs.datadoghq.com/getting_started/site/) for more information.

### Obtaining Datadog Credentials

1. Log in to your Datadog account
2. Go to **Organization Settings** → **API Keys**
3. Create or copy your **API Key** (this is your `DD_API_KEY`)
4. Go to **Organization Settings** → **Application Keys**
5. Create or copy your **Application Key** (this is your `DD_APP_KEY`)

**Note:** These are two different keys:
- **API Key**: Used for authentication with Datadog's API
- **Application Key**: Used for authorization and is tied to a specific user account
