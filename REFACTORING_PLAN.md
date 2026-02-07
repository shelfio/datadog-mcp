# Datadog MCP Refactoring Plan

## Objective
Reduce code duplication and improve maintainability by separating authentication concerns and creating shared HTTP request abstractions. Current `datadog_client.py` is 2481 lines; target is ~1200 lines (52% reduction).

## Problem Statement

### Current Issues
1. **Authentication Duplication**: Every API function duplicates header setup logic for both cookie and token auth
2. **HTTP Boilerplate**: Repeated `httpx.AsyncClient` setup, error handling, and retry logic across 80+ functions
3. **Auth Strategy Mixing**: Functions contain inline conditionals for both auth methods instead of clean separation
4. **Maintenance Burden**: Adding a new auth method requires changes in 80+ places
5. **Testing Difficulty**: Cannot easily test auth strategies in isolation

### Example Current Pattern (Repeated 80+ times)
```python
async def fetch_metrics(...):
    headers = get_auth_headers()  # May be cookie or token
    if get_api_cookies():  # Override if cookies available
        headers = {"DD-API-KEY": "...", "DD-APPLICATION-KEY": "..."}
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload)
        if response.status_code not in (200, 201):
            handle_error(response)
        return response.json()
```

## Solution Architecture

### Phase 1: Create Auth Strategy Module
**File**: `datadog_mcp/utils/auth_strategy.py`

```python
from abc import ABC, abstractmethod

class AuthStrategy(ABC):
    """Base class for authentication strategies."""

    @abstractmethod
    async def get_headers(self) -> dict:
        """Return authentication headers for this strategy."""
        pass

    @abstractmethod
    def get_cookies(self) -> dict | None:
        """Return cookies for this strategy (if applicable)."""
        pass


class TokenAuthStrategy(AuthStrategy):
    """Token-based authentication using DD_API_KEY and DD_APPLICATION_KEY."""

    async def get_headers(self) -> dict:
        api_key = get_api_key()
        app_key = get_app_key()
        if not api_key or not app_key:
            raise ValueError("TokenAuth requires DD_API_KEY and DD_APP_KEY")
        return {
            "Content-Type": "application/json",
            "DD-API-KEY": api_key,
            "DD-APPLICATION-KEY": app_key,
        }

    def get_cookies(self) -> dict | None:
        return None


class CookieAuthStrategy(AuthStrategy):
    """Cookie-based authentication using DD_COOKIE_FILE and DD_CSRF_FILE."""

    async def get_headers(self) -> dict:
        csrf_token = get_csrf_token()
        if not csrf_token:
            raise ValueError("CookieAuth requires DD_CSRF_FILE")
        return {
            "Content-Type": "application/json",
            "X-CSRF-Token": csrf_token,
        }

    def get_cookies(self) -> dict | None:
        return get_api_cookies()


class AuthStrategyFactory:
    """Factory for selecting appropriate auth strategy."""

    @staticmethod
    async def get_strategy() -> AuthStrategy:
        """Select and return appropriate auth strategy."""
        # Cookies take precedence if both available
        if get_api_cookies():
            return CookieAuthStrategy()
        return TokenAuthStrategy()
```

### Phase 2: Create HTTP Client Module
**File**: `datadog_mcp/utils/http_client.py`

```python
import httpx
from typing import Any

class DatadogHTTPClient:
    """Unified HTTP client for Datadog API with auth strategy support."""

    def __init__(self, auth_strategy: AuthStrategy):
        self.auth_strategy = auth_strategy

    async def get(self, url: str, **kwargs) -> dict:
        """Make GET request with auth."""
        headers = await self.auth_strategy.get_headers()
        cookies = self.auth_strategy.get_cookies()

        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers=headers,
                cookies=cookies,
                **kwargs
            )
            self._check_response(response)
            return response.json()

    async def post(self, url: str, json: dict = None, **kwargs) -> dict:
        """Make POST request with auth."""
        headers = await self.auth_strategy.get_headers()
        cookies = self.auth_strategy.get_cookies()

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers=headers,
                cookies=cookies,
                json=json,
                **kwargs
            )
            self._check_response(response)
            return response.json()

    def _check_response(self, response: httpx.Response) -> None:
        """Validate response and raise on error."""
        if response.status_code not in (200, 201, 204):
            error_text = response.text
            try:
                error_json = response.json()
                error_text = error_json.get("error", {}).get("message", error_text)
            except:
                pass
            raise ValueError(f"API Error {response.status_code}: {error_text}")
```

### Phase 3: Create API Request Builder Module
**File**: `datadog_mcp/utils/api_request_builder.py`

```python
class QueryBuilder:
    """Builds Datadog metric queries with proper syntax."""

    def __init__(self, metric_name: str):
        self.metric_name = metric_name
        self.aggregation = "avg"
        self.filters = []
        self.by_fields = []

    def with_aggregation(self, agg: str) -> "QueryBuilder":
        self.aggregation = agg
        return self

    def with_filter(self, filter_expr: str) -> "QueryBuilder":
        self.filters.append(filter_expr)
        return self

    def with_group_by(self, *fields: str) -> "QueryBuilder":
        self.by_fields.extend(fields)
        return self

    def build(self) -> str:
        """Build final query string."""
        query = f"{self.aggregation}:{self.metric_name}"

        if self.filters:
            query += "{" + ",".join(self.filters) + "}"

        if self.by_fields:
            query += " by {" + ",".join(self.by_fields) + "}"

        return query


class EndpointResolver:
    """Resolves correct Datadog API endpoints."""

    API_V2_BASE = "https://api.datadoghq.com/api/v2"
    API_V1_BASE = "https://api.datadoghq.com/api"

    @staticmethod
    def logs(query: str, from_ts: int, to_ts: int) -> str:
        return f"{EndpointResolver.API_V2_BASE}/logs-queries/list"

    @staticmethod
    def metrics(metric_name: str) -> str:
        return f"{EndpointResolver.API_V2_BASE}/metrics/{metric_name}/data"

    @staticmethod
    def metric_tags(metric_name: str) -> str:
        return f"{EndpointResolver.API_V2_BASE}/metrics/{metric_name}/all-tags"

    @staticmethod
    def monitors() -> str:
        return f"{EndpointResolver.API_V1_BASE}/monitor"

    @staticmethod
    def notebooks() -> str:
        return f"{EndpointResolver.API_V2_BASE}/notebooks"
```

### Phase 4: Reorganize into API Client Package
**Directory Structure**:
```
datadog_mcp/utils/
├── datadog_client.py          (reduced to 500 lines, core coords)
├── auth_strategy.py           (new: auth strategies)
├── http_client.py             (new: unified HTTP client)
├── api_request_builder.py     (new: query builders)
└── api_clients/               (new package)
    ├── __init__.py
    ├── base_client.py         (new: base class using DatadogHTTPClient)
    ├── logs_client.py         (new: all logs API functions)
    ├── metrics_client.py      (new: all metrics API functions)
    ├── traces_client.py       (new: all traces API functions)
    ├── monitors_client.py     (new: all monitors API functions)
    ├── notebooks_client.py    (new: all notebooks API functions)
    ├── services_client.py     (new: all services API functions)
    ├── teams_client.py        (new: all teams API functions)
    └── misc_client.py         (new: other endpoints)
```

## Implementation Strategy

### Phase 1: Create Auth Strategy Module (Week 1)
**Tasks**:
1. Create `auth_strategy.py` with base + concrete strategy classes
2. Add tests: `tests/test_auth_strategy.py`
3. Verify both auth methods work with new module
4. No changes to existing code yet

**Success Criteria**:
- ✅ TokenAuthStrategy works for v2 endpoints
- ✅ CookieAuthStrategy works for v1 endpoints
- ✅ Both can coexist
- ✅ Tests pass

### Phase 2: Create HTTP Client Module (Week 1)
**Tasks**:
1. Create `http_client.py` with DatadogHTTPClient class
2. Add tests: `tests/test_http_client.py`
3. Update existing functions one category at a time to use new client
4. Maintain backward compatibility

**Success Criteria**:
- ✅ Logs API functions use DatadogHTTPClient
- ✅ Metrics API functions use DatadogHTTPClient
- ✅ All tests still pass

### Phase 3: Create API Request Builder Module (Week 1-2)
**Tasks**:
1. Create `api_request_builder.py` with QueryBuilder and EndpointResolver
2. Add tests: `tests/test_api_request_builder.py`
3. Update metric/query building functions to use new builders
4. Ensure backward compatibility maintained

**Success Criteria**:
- ✅ QueryBuilder produces correct Datadog syntax
- ✅ EndpointResolver returns correct URLs
- ✅ All existing queries still work

### Phase 4: Reorganize into Package Structure (Week 2-3)
**Tasks**:
1. Create `api_clients/` package with `base_client.py`
2. Create specialized clients: logs, metrics, traces, monitors, notebooks, services, teams, misc
3. Migrate functions by category
4. Update tool imports to use new package
5. Reduce `datadog_client.py` to coordinator only

**Success Criteria**:
- ✅ All 80+ API functions migrated
- ✅ All tests pass
- ✅ datadog_client.py reduced to ~500 lines
- ✅ Tools work without changes

## Backward Compatibility Strategy

### Maintain Facade Functions
Keep existing functions in `datadog_client.py` as thin wrappers:

```python
# datadog_client.py (old)
async def fetch_logs(...):
    """Maintained for backward compatibility."""
    client = LogsAPIClient()
    return await client.fetch_logs(...)
```

### Update Tool Imports Incrementally
1. Tools import from `datadog_client.py` (unchanged)
2. `datadog_client.py` imports from new modules internally
3. No tool code changes required
4. Gradual migration possible

### Verification Checklist
- ✅ All tool tests pass without modification
- ✅ Server starts without errors
- ✅ All 26 tools work via MCP
- ✅ Both auth methods (cookie + token) work

## Risk Assessment

### Low Risk (99% confidence)
- Creating new modules without changing existing code
- Writing new tests for new modules
- Using composition (HttpClient wrapping) instead of inheritance

### Medium Risk (90% confidence)
- Migrating API functions to new structure
- Changes to imports and dependencies
- Mitigation: Run full test suite after each category

### High Risk Areas (80% confidence)
- Error handling in DatadogHTTPClient
- Auth strategy fallback logic
- Endpoint URL construction
- Mitigation: Extra test coverage, manual verification

## Code Metrics

### Before Refactoring
- `datadog_client.py`: 2481 lines (monolithic)
- Duplication: ~40% (auth headers, HTTP setup, error handling)
- Auth strategies: Mixed inline
- Testing difficulty: High (can't test strategies in isolation)

### After Refactoring
- `datadog_client.py`: ~500 lines (coordinator + facades)
- `auth_strategy.py`: ~150 lines (clean separation)
- `http_client.py`: ~100 lines (unified requests)
- `api_request_builder.py`: ~80 lines (query building)
- `api_clients/`: ~1800 lines (organized by domain)
- **Total reduction**: 52% fewer duplicate lines

## Timeline

| Phase | Duration | Key Deliverables |
|-------|----------|------------------|
| 1 | 2 days | auth_strategy.py + tests |
| 2 | 2 days | http_client.py + tests |
| 3 | 2 days | api_request_builder.py + tests |
| 4 | 5 days | Package structure + migration |
| Testing | 2 days | Full regression testing |
| **Total** | **~2 weeks** | Production-ready refactored code |

## Success Criteria

- [ ] All 26 tools working without modification
- [ ] 52% code reduction achieved
- [ ] 100% test pass rate
- [ ] Auth strategies cleanly separated
- [ ] HTTP requests unified in DatadogHTTPClient
- [ ] API functions organized by domain
- [ ] Documentation updated
- [ ] Zero breaking changes for tool users
- [ ] Both auth methods (cookie + token) supported
- [ ] Code review approval

## Rollback Plan

If issues arise:
1. Keep original `datadog_client.py` in git history
2. All functions have backward-compatible facades
3. Can revert to monolithic version in hours
4. Tests ensure quick verification of rollback
