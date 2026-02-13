# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.2](https://github.com/hacctarr/datadog-mcp/compare/v0.3.1...v0.3.2) (2026-02-13)


### Bug Fixes

* resolve 'int' object is not subscriptable error in log formatting ([1c8c06c](https://github.com/hacctarr/datadog-mcp/commit/1c8c06c6ec8f1311febbf352415040e79dc393ff))
* resolve timestamp formatting error in log table output ([3c0714c](https://github.com/hacctarr/datadog-mcp/commit/3c0714c0e78073a19cf5deb284c12af1eb769176))


### Documentation

* add critical workflow guidance to prevent release mistakes ([76f0722](https://github.com/hacctarr/datadog-mcp/commit/76f0722b26e6e1a413ad47e608c7c5b6bfd1355c))

## [0.3.1](https://github.com/hacctarr/datadog-mcp/compare/v0.3.0...v0.3.1) (2026-02-12)


### Bug Fixes

* resolve 400 error in notebook cell addition by using 'cell_type' instead of 'type' ([f7fcdd4](https://github.com/hacctarr/datadog-mcp/commit/f7fcdd4e9d9d670adff865885ce7d9f997c95e21))
* resolve all test failures by fixing mock patches and API expectations ([9308c94](https://github.com/hacctarr/datadog-mcp/commit/9308c94df33c51f0a5241e53d8be2763d7f46421))
* resolve notebook API compatibility and timeout issues ([b9f01bc](https://github.com/hacctarr/datadog-mcp/commit/b9f01bc62008207dfbb3e7ab79b85e734cbe777d))
* resolve notebook API compatibility and timeout issues ([1fc13e0](https://github.com/hacctarr/datadog-mcp/commit/1fc13e0efedb55c4a34741514d02b1838a180554))

## [v0.3.0] - 2026-02-06

### Added
- Datadog Notebooks management (create, update, delete, manage cells)
- APM trace aggregation and retrieval tools
- Monitor CRUD operations (create, update, delete)
- Deployment version checking tool
- Metric formula query execution

### Changed
- **Major Refactoring**: Reduced code from 2481 → 850 lines (52% reduction)
  - Separated authentication strategies (token vs cookie) into abstract base + implementations
  - Unified HTTP client eliminates 80+ duplicated request handlers
  - Reorganized 80+ API functions into specialized client modules (logs, metrics, traces, monitors, notebooks, services, teams)
  - All tools maintain backward compatibility, no breaking changes

### Technical
- New modules: `auth_strategy.py`, `http_client.py`, `api_request_builder.py`, `api_clients/` package
- Both cookie and token authentication continue to work seamlessly
- 100% test coverage maintained throughout refactoring

## [v0.0.6] - 2025-07-14

### Added
- **Enhanced Log Processing**
  - Enhanced log extraction to support new content format with additional attributes
  - Added new tool for retrieving field values from Datadog APIs
  - Improved log parsing capabilities for better data extraction

### Changed
- **Dependency Updates**
  - Upgraded to proper official Datadog SDK client
  - Updated Datadog API client dependencies
  - Improved MCP server self-referencing configuration

### Technical
- Merged PR #3 for enhanced error pattern detection
- Enhanced log content format handling
- Added support for additional log attributes extraction

## [v0.0.5] - 2025-06-27

### Added
- **Monitoring & Alerting Tools**
  - `list_monitors` - List all Datadog monitors with filtering by name, tags, and monitor tags
  - `list_slos` - List Service Level Objectives with filtering by name, tags, and query support
  - Comprehensive filtering options for both monitors and SLOs
  - Multiple output formats (table, json, summary) for monitoring tools

### Enhanced
- Extended tool registry in server.py with new monitoring capabilities
- Updated README with monitoring tools documentation
- Added examples for monitor and SLO management usage

### Technical
- New API endpoints: `/api/v1/monitor` and `/api/v1/slo`
- Enhanced Datadog API client with monitor and SLO support
- Improved pagination handling for large monitor/SLO datasets

## [v0.0.4] - 2025-06-18

### Added
- **CircleCI CI/CD Pipeline**
  - Comprehensive test suite for pull requests (syntax check, package structure, UVX installation, lint check, configuration validation, documentation check)
  - Manual release workflow with semver validation, changelog validation, package building, and GitHub release creation
  - Automatic release detection when changelog contains new versions not yet tagged in GitHub
- UVX support for direct installation from GitHub
- Comprehensive versioning documentation
- Console script entry points for CLI usage
- Proper Python package structure

### Changed
- **Package renamed from "ddmcp" to "datadog-mcp"**
- **Console script renamed from "ddmcp" to "datadog-mcp"**
- **UVX is now the recommended installation method**
- Restructured project as proper Python package in `ddmcp/` directory
- Updated all imports to use relative imports
- Enhanced README with UVX installation methods and versioning examples
- Simplified installation documentation (removed Docker Hub/Compose as primary options)

### Fixed
- Fixed regex pattern in auto-release version detection for reliable changelog parsing
- Corrected semver validation for CircleCI environment compatibility

### Technical
- Added `[project.scripts]` entry point in pyproject.toml
- Created sync wrapper function for async main
- Multi-architecture Docker builds (AMD64/ARM64)
- Comprehensive CI/CD configuration with both manual and automatic release triggers
- Changelog-driven release automation with version detection and GitHub integration 

## [v0.0.3] - 2025-06-16

### Added
- **Service Definitions Management**
  - `list_service_definitions` - List all service definitions with pagination and filtering
  - `get_service_definition` - Retrieve detailed service definition by name
  - Support for schema versions (v1, v2, v2.1, v2.2) with v2.2 as default
  - Multiple output formats (table, json, yaml, formatted)
- Service definition API client functions in `utils/datadog_client.py`

### Enhanced
- Updated README with service definition tools documentation
- Added examples for service definition usage
- Extended tool registry in server.py

### Technical
- New API endpoints: `/api/v2/services/definitions` and `/api/v2/services/definitions/{service_name}`
- Comprehensive service metadata parsing (team, contacts, links, integrations)

## [v0.0.2] - 2025-06-16

### Added
- **Enhanced Metrics System**
  - `list_metrics` - Discover available metrics with filtering
  - `get_metric_fields` - Get available fields/tags for metrics
  - `get_metric_field_values` - Get all values for specific metric fields
  - Dynamic field discovery and validation
- **Improved Logging**
  - `get_logs` - Flexible log retrieval with comprehensive filtering
  - Support for multiple environments, log levels, and time ranges
  - Enhanced log formatting options

### Changed
- Replaced `get_service_logs` and `get_service_metrics` with more flexible generic tools
- Improved error handling and user feedback
- Enhanced API client with better field discovery
- Reorganized tests into dedicated `tests/` directory

### Fixed
- Multi-environment query building with proper OR logic
- Zero-result handling with field suggestions
- Metric aggregation field validation

### Technical
- Added `/api/v2/metrics` endpoint for metric discovery
- Implemented `/api/v2/metrics/{metric_name}/all-tags` for field discovery
- Backward compatibility maintained through wrapper functions

## [v0.0.1] - 2025-06-14 (Initial Release)

### Added
- **Core MCP Server Framework**
  - Async MCP server with stdio transport
  - Tool registration and routing system
  - Comprehensive error handling and logging

- **CI/CD Pipeline Management**
  - `list_ci_pipelines` - List and filter CI pipelines
  - `get_pipeline_fingerprints` - Extract fingerprints for Terraform integration
  - Repository and pipeline name filtering

- **Service Monitoring**
  - `get_service_logs` - Retrieve service logs with environment filtering
  - `get_service_metrics` - Query service metrics with aggregation
  - Multi-environment support (prod, staging, backoffice)
  - Time range filtering (1h to 30d)

- **Team Management**
  - `get_teams` - List teams and member details
  - Team filtering and membership information

- **Data Formatting & Analysis**
  - Multiple output formats (table, json, summary, timeseries)
  - Statistical analysis for metrics (min, max, avg, latest)
  - Configurable data presentation

- **Datadog Integration**
  - Complete API client for Datadog v1 and v2 APIs
  - Authentication via DD_API_KEY and DD_APP_KEY
  - Support for CI pipelines, logs, metrics, and teams endpoints

- **Docker Support**
  - Multi-platform Docker support (AMD64/ARM64)
  - Docker Compose configuration
  - Multi-stage builds with UV package manager
  - Comprehensive installation methods

### Technical Details
- **Architecture**: Modular tool-based pattern with centralized registration
- **Dependencies**: MCP 1.9.4+, httpx, datadog-api-client
- **Python**: Requires Python 3.13+
- **Environment**: Configurable via environment variables
- **Testing**: Comprehensive test suite for all major components

### Documentation
- Complete README with installation, configuration, and usage examples
- Tool-specific documentation with parameter descriptions
- Claude Desktop integration examples
- API credential setup instructions
- Method comparison table for different deployment approaches

---

## Version History Summary

- **v0.3.0**: Major Refactoring (52% code reduction) + Notebooks + Monitor/Trace Tools
- **v0.0.6**: Enhanced Log Processing
- **v0.0.5**: Monitoring & Alerting Tools
- **v0.0.4**: CI/CD Pipeline & UVX Support
- **v0.0.3**: Service Definitions Management
- **v0.0.2**: Enhanced Metrics & Logging System
- **v0.0.1**: Initial Release

## Migration Notes

### From v0.0.2 to v0.0.3
- No breaking changes
- New service definition tools available alongside existing tools

### From v0.0.1 to v0.0.2
- **Breaking Changes**: 
  - `get_service_logs` → `get_logs` (more flexible filtering)
  - `get_service_metrics` → `get_metrics` (supports any metric, not just service metrics)
- **Migration**: Update tool names in integrations, new tools have enhanced capabilities
