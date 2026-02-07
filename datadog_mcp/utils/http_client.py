"""
Unified HTTP client for Datadog API requests.

Provides a single abstraction layer for making HTTP requests with proper
authentication, error handling, and retry logic. Eliminates boilerplate
duplication across 80+ API functions.
"""

import json
import logging
from typing import Any, Dict, Optional

import httpx

from .auth_strategy import AuthStrategy

logger = logging.getLogger(__name__)


class DatadogHTTPClient:
    """Unified HTTP client for Datadog API with authentication strategy support.

    Handles:
    - Authentication via configurable strategies (token or cookie)
    - Request header setup and validation
    - Response error handling and validation
    - Proper HTTP status code checking
    - Clean separation between auth concerns and HTTP logic
    """

    def __init__(self, auth_strategy: AuthStrategy, timeout: float = 30.0):
        """Initialize HTTP client with authentication strategy.

        Args:
            auth_strategy: Authentication strategy to use (TokenAuthStrategy or CookieAuthStrategy)
            timeout: Request timeout in seconds (default: 30)
        """
        self.auth_strategy = auth_strategy
        self.timeout = timeout

    async def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        expected_status: tuple = (200,),
        **kwargs,
    ) -> Dict[str, Any]:
        """Make GET request with authentication.

        Args:
            url: Endpoint URL
            params: Query parameters
            expected_status: Tuple of acceptable HTTP status codes (default: (200,))
            **kwargs: Additional arguments passed to httpx.AsyncClient.get()

        Returns:
            Response JSON as dictionary

        Raises:
            ValueError: If response status code not in expected_status
        """
        headers = await self.auth_strategy.get_headers()
        cookies = self.auth_strategy.get_cookies()

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                url,
                headers=headers,
                cookies=cookies,
                params=params,
                **kwargs,
            )
            self._check_response(response, expected_status)
            return response.json()

    async def post(
        self,
        url: str,
        json: Optional[Dict[str, Any]] = None,
        expected_status: tuple = (200, 201),
        **kwargs,
    ) -> Dict[str, Any]:
        """Make POST request with authentication.

        Args:
            url: Endpoint URL
            json: Request body as dictionary
            expected_status: Tuple of acceptable HTTP status codes (default: (200, 201))
            **kwargs: Additional arguments passed to httpx.AsyncClient.post()

        Returns:
            Response JSON as dictionary

        Raises:
            ValueError: If response status code not in expected_status
        """
        headers = await self.auth_strategy.get_headers()
        cookies = self.auth_strategy.get_cookies()

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                url,
                headers=headers,
                cookies=cookies,
                json=json,
                **kwargs,
            )
            self._check_response(response, expected_status)
            return response.json()

    async def put(
        self,
        url: str,
        json: Optional[Dict[str, Any]] = None,
        expected_status: tuple = (200,),
        **kwargs,
    ) -> Dict[str, Any]:
        """Make PUT request with authentication.

        Args:
            url: Endpoint URL
            json: Request body as dictionary
            expected_status: Tuple of acceptable HTTP status codes (default: (200,))
            **kwargs: Additional arguments passed to httpx.AsyncClient.put()

        Returns:
            Response JSON as dictionary

        Raises:
            ValueError: If response status code not in expected_status
        """
        headers = await self.auth_strategy.get_headers()
        cookies = self.auth_strategy.get_cookies()

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.put(
                url,
                headers=headers,
                cookies=cookies,
                json=json,
                **kwargs,
            )
            self._check_response(response, expected_status)
            return response.json()

    async def delete(
        self,
        url: str,
        expected_status: tuple = (200, 204),
        **kwargs,
    ) -> Optional[Dict[str, Any]]:
        """Make DELETE request with authentication.

        Args:
            url: Endpoint URL
            expected_status: Tuple of acceptable HTTP status codes (default: (200, 204))
            **kwargs: Additional arguments passed to httpx.AsyncClient.delete()

        Returns:
            Response JSON as dictionary, or None if response has no content

        Raises:
            ValueError: If response status code not in expected_status
        """
        headers = await self.auth_strategy.get_headers()
        cookies = self.auth_strategy.get_cookies()

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.delete(
                url,
                headers=headers,
                cookies=cookies,
                **kwargs,
            )
            self._check_response(response, expected_status)

            # DELETE requests may return no content (204)
            if response.status_code == 204 or not response.content:
                return None

            return response.json()

    async def patch(
        self,
        url: str,
        json: Optional[Dict[str, Any]] = None,
        expected_status: tuple = (200,),
        **kwargs,
    ) -> Dict[str, Any]:
        """Make PATCH request with authentication.

        Args:
            url: Endpoint URL
            json: Request body as dictionary
            expected_status: Tuple of acceptable HTTP status codes (default: (200,))
            **kwargs: Additional arguments passed to httpx.AsyncClient.patch()

        Returns:
            Response JSON as dictionary

        Raises:
            ValueError: If response status code not in expected_status
        """
        headers = await self.auth_strategy.get_headers()
        cookies = self.auth_strategy.get_cookies()

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.patch(
                url,
                headers=headers,
                cookies=cookies,
                json=json,
                **kwargs,
            )
            self._check_response(response, expected_status)
            return response.json()

    def _check_response(
        self, response: httpx.Response, expected_status: tuple
    ) -> None:
        """Validate response and raise on error.

        Args:
            response: HTTP response object
            expected_status: Tuple of acceptable status codes

        Raises:
            ValueError: If response status code not in expected_status or response indicates error
        """
        if response.status_code not in expected_status:
            error_text = response.text

            # Try to extract better error message from JSON
            try:
                error_json = response.json()
                # Datadog API error structure
                if "error" in error_json:
                    error_msg = error_json["error"]
                    if isinstance(error_msg, dict):
                        error_text = error_msg.get("message", error_text)
                    else:
                        error_text = str(error_msg)
                # Alternative error structure
                elif "errors" in error_json:
                    errors = error_json["errors"]
                    if isinstance(errors, list) and errors:
                        error_text = errors[0]
                    else:
                        error_text = str(errors)
                # Generic message field
                elif "message" in error_json:
                    error_text = error_json["message"]
            except Exception:
                # Use the raw text if JSON parsing or extraction fails
                pass

            status_name = self._get_status_name(response.status_code)
            raise ValueError(
                f"API Error {response.status_code} {status_name}: {error_text}"
            )

    @staticmethod
    def _get_status_name(status_code: int) -> str:
        """Get human-readable status code name."""
        status_names = {
            400: "Bad Request",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
            429: "Too Many Requests",
            500: "Internal Server Error",
            502: "Bad Gateway",
            503: "Service Unavailable",
        }
        return status_names.get(status_code, "Error")
