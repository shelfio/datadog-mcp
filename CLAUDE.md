# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Workflow (CRITICAL)

### ⚠️ REPOSITORY WARNING (READ THIS FIRST)
**This repository has multiple GitHub mirrors. Use ONLY the canonical repository:**

| Repository | Purpose | PR Action |
|------------|---------|-----------|
| `hacctarr/datadog-mcp` | **Canonical** (use this) | ✅ Create PRs here |
| `andreidore/datadog-mcp` | Read-only upstream reference | ❌ NEVER create PRs |
| `shelfio/datadog-mcp` | Original source repository | ❌ NEVER create PRs |
| `cobalt-robotics/datadog-mcp` | Internal fork (mirror only) | ❌ NEVER create PRs |

**If you accidentally create a PR on andreidore or shelfio, it will be rejected. Always target hacctarr/datadog-mcp.**

### CREATE FEATURE BRANCH FIRST (DO THIS BEFORE ANY CODE CHANGES)
**BEFORE making ANY edits:**
1. `git checkout main && git pull origin main` - Start from latest main
2. `git checkout -b fix/feature-name` OR `git checkout -b feat/feature-name` - Create feature branch
3. ONLY THEN make code changes

**DO NOT:**
- ❌ Make changes on main branch
- ❌ Make changes and then create branch
- ❌ Commit to main directly
- ❌ Create branch after editing files

**CORRECT SEQUENCE:**
```
git checkout main
git pull origin main
git checkout -b fix/your-feature-name  ← CREATE BRANCH FIRST
# NOW you can edit files
# THEN commit and push
```

**IMPORTANT**: Always write tests FIRST before implementing code. This is non-negotiable.

**Test-First Development:**
1. Write test file for your feature (e.g., `tests/test_create_monitor.py`)
2. Run tests - they will fail (RED)
3. Implement tool/client code to make tests pass (GREEN)
4. Run full test suite before submitting PR

### Pre-PR Checklist (Required Before Every PR)
1. ⚠️ **CRITICAL**: Verify the PR target is `hacctarr/datadog-mcp` main (see Repository Warning above)
2. `uv run pytest tests/` - All tests pass
3. `uv run python -m py_compile datadog_mcp/server.py` - No syntax errors
4. Verify NO manual edits to: `pyproject.toml` version, `.release-please-manifest.json`, `CHANGELOG.md`
5. Confirm commit messages use conventional commit format: `fix:`, `feat:`, `chore:`, `docs:`, `refactor:`

### Development Commands

#### Building and Running
- `uv sync` - Install dependencies using UV package manager
- `uv run datadog_mcp/server.py` - Run the MCP server locally
- `podman build -t datadog-mcp .` - Build Podman image
- `podman-compose up` - Run with Podman Compose (requires DD_API_KEY and DD_APP_KEY env vars)

#### Testing (Required before every PR)
- `uv run pytest tests/test_integration.py` - Test core server functionality (no API required)
- `uv run pytest tests/test_tools_working.py` - Test tool functionality (no API required)
- `uv run pytest tests/` - Run all tests (REQUIRED before PR submission)
- Most tests use mocking and don't require real Datadog API credentials
- For integration tests with real API, set DD_API_KEY and DD_APP_KEY environment variables

#### Syntax Checking
- `uv run python -m py_compile datadog_mcp/server.py` - Check main server syntax
- `uv run python -m py_compile datadog_mcp/tools/*.py` - Check all tool implementations
- `uv run python -m py_compile datadog_mcp/utils/*.py` - Check utility modules

## Release Workflow (CRITICAL - Automated via release-please)

### Files Claude Must NEVER Edit for Release Purposes
- `pyproject.toml` version field - owned by release-please
- `.release-please-manifest.json` - owned by release-please
- `CHANGELOG.md` - owned by release-please
- Git tags - created automatically by release-please

### How Releases Work (Two-Phase Process)

**Phase 1: Feature Development**
1. Create feature branch off `main`
2. Write commits using conventional commit format:
   - `fix: description` - patch version bump (0.0.x)
   - `feat: description` - minor version bump (0.x.0)
   - `feat!: description` or `BREAKING CHANGE:` footer - major bump (x.0.0)
   - `chore:`, `docs:`, `refactor:` - no version bump, included in changelog
3. Push branch, create PR to `hacctarr/datadog-mcp` main
4. Merge PR to main

**Phase 2: Automated Release (DO NOT INTERVENE)**
5. release-please GitHub Action detects new conventional commits on main
6. release-please creates/updates a "Release PR" that bumps version in:
   - `pyproject.toml`
   - `.release-please-manifest.json`
   - `CHANGELOG.md`
7. Merge the Release PR (review to ensure version is correct)
8. Merge triggers the `publish` job: builds, tests, uploads to GitHub Releases, publishes to PyPI
9. Done - no manual steps after Release PR merge

### When to Intervene vs Trust Automation
| Situation | Action |
|-----------|--------|
| Want to release new version | Merge feature PRs to main, wait for release-please PR |
| release-please PR has wrong version | Review release config, don't edit version manually |
| Need to skip a release | Don't merge the release-please PR |
| PyPI publish failed | Re-run workflow or use manual dispatch |
| Version in pyproject.toml is wrong | Let release-please fix it; do NOT edit manually |

## MCP Testing & Validation (CRITICAL)

### Test MCP Changes Using Claude Code MCP Tools Only
**NEVER test MCP changes by writing Python scripts.** Instead:

1. **Use Claude Code Tasks**: Launch Claude Code task agents with MCP tool tests
2. **Configure MCP**: Ensure datadog-mcp server is running locally
3. **Verify Auth**: Use `mcp__datadog__setup_auth` to configure Datadog credentials
4. **Test via MCP Tools**: Use the actual MCP tool functions (e.g., `mcp__datadog__get_logs`, `mcp__datadog__list_notebooks`)
5. **Validate Output**: Check that tool outputs are correctly formatted and match expectations
6. **Document Results**: Record comprehensive test results in baseline files or commit messages

### Why This Matters
- Tests via MCP tools validate the entire stack (including formatters, serialization)
- Writing Python scripts bypasses the MCP interface and misses real integration issues
- Claude Code using MCP tools mirrors actual user experience
- MCP tool testing provides production-ready validation of all changes

### Testing Baseline Improvements
When testing improvements to the baseline:
1. **Do NOT use Python scripts or code execution**
2. **Use Claude Code MCP tools exclusively** (mcp__datadog__*)
3. **Run comprehensive tests** covering all affected features
4. **Document before/after** comparisons showing improvements
5. **Verify edge cases** identified in previous baseline runs

### Pre-Release MCP Testing Checklist
Before merging any MCP tool changes:
- [ ] Tool executes without errors via MCP interface
- [ ] Output is correctly formatted (table, JSON, text)
- [ ] Edge cases work (empty results, special characters, large datasets)
- [ ] Error messages are clear and helpful
- [ ] No data loss or corruption in formatting
- [ ] All tests use Claude Code MCP tools, not scripts

## Architecture Overview

This is a **Model Context Protocol (MCP) server** that provides Datadog monitoring capabilities to Claude Desktop. The architecture follows a modular tool-based pattern:

### Core Components

**`datadog_mcp/server.py`** - Main MCP server orchestrator that:
- Registers all available tools in the TOOLS dictionary
- Routes tool calls to appropriate handlers
- Manages async server lifecycle using stdio transport
- Handles authentication via environment variables

**`datadog_mcp/tools/`** - Individual MCP tool implementations, each with:
- `get_tool_definition()` - Returns MCP Tool schema with input validation
- `handle_call()` - Processes requests and returns formatted responses
- Consistent error handling and parameter validation patterns

**`datadog_mcp/utils/datadog_client.py`** - Centralized Datadog API client that:
- Manages authentication headers (DD_API_KEY, DD_APP_KEY)
- Implements all API endpoints (pipelines, logs, metrics, teams)
- Handles multiple environments via array parameters
- Supports aggregation_by for grouping metrics
- Uses proper Datadog API endpoints (e.g., `/api/v2/metrics/{metric_name}/all-tags` for field discovery)
- Constructs metric queries in Datadog format: `aggregation:metric{filters} by {fields}`

**`datadog_mcp/utils/formatters.py`** - Data transformation layer providing:
- Multiple output formats (table, JSON, summary, timeseries)
- Statistical analysis for metrics
- Consistent data presentation across tools

### Tool Registration Pattern
```python
TOOLS = {
    "list_metrics": {
        "definition": list_metrics.get_tool_definition,
        "handler": list_metrics.handle_call,
    },
    "get_metrics": {
        "definition": get_metrics.get_tool_definition,
        "handler": get_metrics.handle_call,
    },
    "get_metric_fields": {
        "definition": get_metric_fields.get_tool_definition,
        "handler": get_metric_fields.handle_call,
    },
    "get_metric_field_values": {
        "definition": get_metric_field_values.get_tool_definition,
        "handler": get_metric_field_values.handle_call,
    },
    # ... other tools
}
```

### Environment Parameter Handling
Environment parameters now accept arrays for multi-environment queries:
- Single: `["prod"]` (default)
- Multiple: `["prod", "staging", "dev"]`
- Arbitrary environment names supported

## Key Implementation Patterns

### Async API Client Pattern
All Datadog API calls use async/await with httpx:
```python
async with httpx.AsyncClient() as client:
    response = await client.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()
```

### Error Handling Strategy
- Tool handlers wrap logic in try-catch blocks
- Return `CallToolResult` with `isError=True` for failures
- Log errors while returning user-friendly messages
- Individual metric failures don't fail entire requests

### Multi-Environment Query Building
For multiple environments, the client builds OR logic queries:
```python
if len(environment) > 1:
    env_filter = "env:" + " OR env:".join(environment)
    filters.append(f"({env_filter})")
```

### Dynamic Field Discovery Pattern
When aggregation fields don't exist or return zero results:
```python
# Check for zero results
if not has_data and aggregation_by != ["service"]:
    # Fetch available fields for the metric
    available_fields = await fetch_metric_available_fields(...)
    # Suggest available fields to user
    return suggestion_message_with_available_fields
```

### Multi-Field Aggregation Support
Aggregation by multiple fields uses comma-separated syntax:
```python
if aggregation_by and aggregation_by != ["service"]:
    by_clause = ",".join(aggregation_by)
    query_parts.append(f"by {{{by_clause}}}")
```

## Configuration Requirements

### Required Environment Variables
- `DD_API_KEY` - Datadog API authentication key
- `DD_APP_KEY` - Datadog application key for authorization

### Cookie-Based Authentication (Optional)
For httpx-based API calls, cookie authentication is supported as an alternative to API keys:
- `DD_COOKIE_FILE` - Path to file containing Datadog session cookie
- `DD_CSRF_FILE` - Path to file containing CSRF token

**IMPORTANT**: When implementing new httpx-based API functions (e.g., `fetch_metric_formula`):
1. Always call `cookies = get_api_cookies()` to get cookies if available
2. Pass `cookies=cookies` parameter to all `client.post()` and `client.get()` calls
3. This ensures consistency across all tools that support cookie-based auth

Functions using the official Datadog SDK (e.g., `fetch_logs`) automatically handle cookie auth through `get_datadog_configuration()`.

### Python Requirements
- Python 3.13+ (specified in pyproject.toml)
- UV package manager for dependency management
- Async/await support throughout codebase

### Podman Integration
The Podman setup uses multi-stage builds with:
- Python 3.13-slim base image
- UV package manager installation
- Multi-architecture support (AMD64/ARM64)

## Testing Strategy

Tests are organized by feature area and require real Datadog API access:
- All tests validate actual API responses
- Environment variables must be set for test execution
- Tests cover both success and error scenarios
- Each tool has dedicated test coverage

## Claude Desktop Integration

The server integrates with Claude Desktop via MCP configuration. Add to your Claude Desktop config (usually `~/.claude/claude_desktop_config.json`):

### Using UVX (Recommended)
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

Replace `LATEST_VERSION` with the version from [GitHub releases](https://github.com/hacctarr/datadog-mcp/releases) (e.g., `v0.3.4`).

### Using Local Development Setup
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

The server provides comprehensive Datadog monitoring through conversational commands like "Show CI pipelines for my-repo" or "Get error logs for service-name in the last 4 hours".