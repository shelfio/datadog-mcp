"""
Setup authentication for Datadog MCP
"""

import logging
from typing import Any, Dict, Optional

from mcp.types import CallToolRequest, CallToolResult, Tool, TextContent

logger = logging.getLogger(__name__)

from ..utils.datadog_client import (
    save_cookie,
    save_csrf_token,
    save_api_key,
    save_app_key,
    get_cookie,
    get_csrf_token,
    get_api_key,
    get_app_key,
    COOKIE_FILE_PATH,
    CSRF_FILE_PATH,
    API_KEY_FILE_PATH,
    APP_KEY_FILE_PATH,
)


def get_tool_definition() -> Tool:
    """Get the tool definition for setup_auth."""
    return Tool(
        name="setup_auth",
        description="Setup or verify Datadog authentication. Configure cookie-based (internal UI) or token-based (public API) authentication.",
        inputSchema={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["detect", "configure_cookie", "configure_token", "verify", "status"],
                    "description": "Action to perform: detect (auto-detect auth), configure_cookie (setup cookie), configure_token (setup API keys), verify (test connection), status (show current config)",
                    "default": "detect",
                },
                "cookie_value": {
                    "type": "string",
                    "description": "Cookie value (for configure_cookie action). Can be raw hex or 'dogweb=...' format",
                },
                "csrf_token": {
                    "type": "string",
                    "description": "CSRF token (for configure_cookie action). Required for POST requests",
                },
                "api_key": {
                    "type": "string",
                    "description": "Datadog API key (for configure_token action)",
                },
                "app_key": {
                    "type": "string",
                    "description": "Datadog application key (for configure_token action)",
                },
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    )


async def handle_call(request: CallToolRequest) -> CallToolResult:
    """Handle the setup_auth tool call."""
    try:
        args = request.arguments or {}
        action = args.get("action", "detect")

        if action == "detect":
            return await handle_detect()
        elif action == "status":
            return await handle_status()
        elif action == "configure_cookie":
            return await handle_configure_cookie(args)
        elif action == "configure_token":
            return await handle_configure_token(args)
        elif action == "verify":
            return await handle_verify()
        else:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Unknown action: {action}")],
                isError=True,
            )

    except Exception as e:
        logger.error(f"Error in setup_auth: {e}")
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True,
        )


async def handle_detect() -> CallToolResult:
    """Auto-detect current authentication status."""
    cookie = get_cookie()
    csrf = get_csrf_token()

    if cookie:
        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=f"""✅ COOKIE AUTHENTICATION DETECTED

🔐 Status: Cookie-based auth is configured
📁 Location: {COOKIE_FILE_PATH}
🛡️  Cookie: {cookie[:20]}... (hidden for security)
{'✅ CSRF token present' if csrf else '⚠️  CSRF token missing (some POST requests may fail)'}

📝 To reconfigure:
  setup_auth action=configure_cookie cookie_value=... csrf_token=...

🧪 To test connection:
  setup_auth action=verify
""",
                )
            ],
            isError=False,
        )
    else:
        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=f"""ℹ️  NO AUTHENTICATION DETECTED

To configure cookie-based authentication:
1. Go to https://app.datadoghq.com and log in
2. Extract the 'dogweb' cookie from DevTools (see instructions below)
3. Use this command:
   setup_auth action=configure_cookie cookie_value=<your_cookie> csrf_token=<your_csrf>

📖 EXTRACTION INSTRUCTIONS:

🔑 Get Cookie ('dogweb'):
  1. Open DevTools (F12)
  2. Go to Application tab
  3. Expand Cookies
  4. Click datadoghq.com
  5. Find 'dogweb' in the list
  6. Copy the VALUE (long hex string)

🔑 Get CSRF Token:
  1. Open DevTools → Network tab
  2. Make a POST request in Datadog (e.g., create a monitor)
  3. Find the request
  4. Look for 'x-csrf-token' header
  5. Copy that value

💾 File Locations:
  - Cookie: {COOKIE_FILE_PATH}
  - CSRF: {CSRF_FILE_PATH}

❓ Need token authentication instead?
  setup_auth action=configure_token api_key=... app_key=...
""",
                )
            ],
            isError=False,
        )


async def handle_status() -> CallToolResult:
    """Show current authentication configuration."""
    cookie = get_cookie()
    csrf = get_csrf_token()

    from ..utils.datadog_client import FORCE_AUTH_METHOD

    status_lines = [
        "📊 DATADOG MCP AUTHENTICATION STATUS\n",
        "=" * 50,
    ]

    # Cookie auth
    if cookie:
        status_lines.append(f"✅ Cookie Auth: CONFIGURED")
        status_lines.append(f"   Location: {COOKIE_FILE_PATH}")
        status_lines.append(f"   Cookie: {cookie[:30]}... (hidden)")
    else:
        status_lines.append(f"❌ Cookie Auth: NOT CONFIGURED")

    # CSRF
    if csrf:
        status_lines.append(f"✅ CSRF Token: CONFIGURED")
        status_lines.append(f"   Location: {CSRF_FILE_PATH}")
    else:
        if cookie:
            status_lines.append(f"⚠️  CSRF Token: NOT CONFIGURED (POST requests may fail)")

    status_lines.append("")

    # API key auth (read fresh from files, not cached)
    api_key = get_api_key()
    app_key = get_app_key()
    if api_key and app_key:
        status_lines.append(f"✅ Token Auth: CONFIGURED")
        status_lines.append(f"   API Key: {api_key[:10]}... (hidden)")
        status_lines.append(f"   App Key: {app_key[:10]}... (hidden)")
        status_lines.append(f"   API Key File: {API_KEY_FILE_PATH}")
        status_lines.append(f"   App Key File: {APP_KEY_FILE_PATH}")
    else:
        status_lines.append(f"❌ Token Auth: NOT CONFIGURED")

    status_lines.append("")
    status_lines.append("=" * 50)

    # Force flag
    if FORCE_AUTH_METHOD:
        status_lines.append(f"🚩 FORCE AUTH: {FORCE_AUTH_METHOD.upper()}")
        status_lines.append(f"   (Only {FORCE_AUTH_METHOD} auth will be used)")
    else:
        status_lines.append(f"🔄 AUTO-DETECT: ENABLED")
        if cookie:
            status_lines.append(f"   Will use: Cookie (preferred)")
        else:
            status_lines.append(f"   Will use: Token (if available)")

    status_lines.append("")
    status_lines.append("Actions:")
    status_lines.append("  setup_auth action=configure_cookie ...  (setup cookie auth)")
    status_lines.append("  setup_auth action=configure_token ...   (setup token auth)")
    status_lines.append("  setup_auth action=verify               (test connection)")

    return CallToolResult(
        content=[TextContent(type="text", text="\n".join(status_lines))],
        isError=False,
    )


async def handle_configure_cookie(args: Dict[str, Any]) -> CallToolResult:
    """Configure cookie-based authentication."""
    cookie_value = args.get("cookie_value")
    csrf_token = args.get("csrf_token")

    if not cookie_value:
        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text="❌ Error: cookie_value is required\n\nUsage:\n  setup_auth action=configure_cookie cookie_value=<value> csrf_token=<value>",
                )
            ],
            isError=True,
        )

    if not csrf_token:
        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text="❌ Error: csrf_token is required\n\nUsage:\n  setup_auth action=configure_cookie cookie_value=<value> csrf_token=<value>",
                )
            ],
            isError=True,
        )

    try:
        # Save both
        cookie_path = save_cookie(cookie_value)
        csrf_path = save_csrf_token(csrf_token)

        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=f"""✅ COOKIE AUTHENTICATION CONFIGURED

📁 Files created:
  - Cookie: {cookie_path}
  - CSRF Token: {csrf_path}

🔐 Configuration:
  Cookie: {cookie_value[:30]}... (hidden)
  CSRF: {csrf_token[:30]}... (hidden)

🧪 Next steps:
  1. Test with: setup_auth action=verify
  2. Or try any Datadog MCP command

💡 Note: All files are secured with 0o600 permissions (owner read/write only)
""",
                )
            ],
            isError=False,
        )

    except Exception as e:
        logger.error(f"Failed to save authentication: {e}")
        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=f"❌ Error saving authentication: {str(e)}",
                )
            ],
            isError=True,
        )


async def handle_configure_token(args: Dict[str, Any]) -> CallToolResult:
    """Configure token-based authentication."""
    api_key = args.get("api_key")
    app_key = args.get("app_key")

    if not api_key or not app_key:
        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text="❌ Error: Both api_key and app_key are required\n\nUsage:\n  setup_auth action=configure_token api_key=<key> app_key=<key>",
                )
            ],
            isError=True,
        )

    try:
        # Save both keys to files (read fresh on each call, no restart needed)
        api_key_path = save_api_key(api_key)
        app_key_path = save_app_key(app_key)

        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=f"""✅ TOKEN AUTHENTICATION CONFIGURED

📁 Files created:
  - API Key: {api_key_path}
  - App Key: {app_key_path}

🔐 Configuration:
  API Key: {api_key[:20]}... (hidden)
  App Key: {app_key[:20]}... (hidden)

🧪 Next steps:
  1. Test with: setup_auth action=verify
  2. Or try any Datadog MCP command

💡 Note:
  - The MCP will use cookie auth if available, otherwise will use token auth
  - Use DD_FORCE_AUTH=token to force token authentication
  - Files are secured with 0o600 permissions (owner read/write only)
  - No restart required - keys are read fresh on each call
""",
                )
            ],
            isError=False,
        )

    except Exception as e:
        logger.error(f"Failed to save token authentication: {e}")
        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=f"❌ Error saving authentication: {str(e)}",
                )
            ],
            isError=True,
        )


async def handle_verify() -> CallToolResult:
    """Test the current authentication setup."""
    from ..utils.datadog_client import get_auth_headers, get_auth_mode
    import httpx

    try:
        use_cookie, api_url = get_auth_mode()
        headers = get_auth_headers()

        # Try a simple read-only request
        test_url = f"{api_url}/api/v1/monitor"
        if not use_cookie:
            test_url = f"{api_url}/api/v1/monitor"

        async with httpx.AsyncClient() as client:
            response = await client.get(test_url, headers=headers, params={"limit": 1})

            if response.status_code == 200:
                auth_method = "Cookie (internal UI)" if use_cookie else "Token (public API)"
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=f"""✅ AUTHENTICATION TEST PASSED

🔐 Auth Method: {auth_method}
📍 API URL: {api_url}
✨ Connected successfully!

You can now use all Datadog MCP commands.

Try:
  mcp__datadog__list_monitors
  mcp__datadog__list_slos
  mcp__datadog__list_teams
""",
                        )
                    ],
                    isError=False,
                )
            elif response.status_code == 401:
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=f"""❌ AUTHENTICATION TEST FAILED (401 Unauthorized)

Your credentials are not valid or have expired.

🔍 Current Setup:
  Auth Method: {"Cookie" if use_cookie else "Token"}
  API URL: {api_url}

💡 Solutions:
  1. If using Cookie auth: Re-extract the 'dogweb' cookie (it may have expired)
     setup_auth action=configure_cookie cookie_value=... csrf_token=...

  2. If using Token auth: Verify your API keys
     setup_auth action=configure_token api_key=... app_key=...

  3. Check configuration:
     setup_auth action=status
""",
                        )
                    ],
                    isError=True,
                )
            else:
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=f"""⚠️  AUTHENTICATION TEST ERROR

Status Code: {response.status_code}
Response: {response.text[:500]}

Check your configuration:
  setup_auth action=status
""",
                        )
                    ],
                    isError=True,
                )

    except Exception as e:
        logger.error(f"Verification failed: {e}")
        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=f"""❌ VERIFICATION FAILED

Error: {str(e)}

Check your configuration:
  setup_auth action=status
""",
                )
            ],
            isError=True,
        )
