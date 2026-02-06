"""
Tests for AWS Secrets Manager integration.

Uses moto with moto's server mode for aioboto3 compatibility, or direct mocking.
"""

import asyncio
import json
import os
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Set test environment variables before importing the module
os.environ["AWS_SECRET_API_KEY"] = "/test/datadog/API_KEY"
os.environ["AWS_SECRET_APP_KEY"] = "/test/datadog/APP_KEY"
os.environ["AWS_REGION"] = "us-west-2"
os.environ["SECRET_CACHE_TTL"] = "60"

from datadog_mcp.utils.secrets_provider import (
    AWSSecretsManagerProvider,
    DatadogCredentials,
    SecretCache,
    close_secret_provider,
    get_secret_provider,
    is_aws_secrets_configured,
)


class TestSecretCache:
    """Tests for SecretCache class."""

    def test_initial_state(self):
        """Cache starts empty."""
        cache = SecretCache(ttl_seconds=60)
        assert cache.get_cached() is None
        assert not cache.is_valid()
        assert cache._needs_refresh()

    def test_set_and_get(self):
        """Can store and retrieve credentials."""
        cache = SecretCache(ttl_seconds=60)
        creds = cache.set("test-api-key", "test-app-key")

        assert creds.api_key == "test-api-key"
        assert creds.app_key == "test-app-key"
        assert cache.is_valid()
        assert cache.get_cached() == creds

    def test_expiry(self):
        """Cache expires after TTL."""
        cache = SecretCache(ttl_seconds=1)
        cache.set("test-api-key", "test-app-key")

        # Manually expire the cache
        cache._cache.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)

        assert not cache.is_valid()
        assert cache.get_cached() is None

    def test_refresh_buffer(self):
        """Cache triggers refresh before full expiry."""
        cache = SecretCache(ttl_seconds=600)  # 10 minute TTL
        cache.set("test-api-key", "test-app-key")

        # Set expiry to 5 minutes from now (within 10 minute refresh buffer)
        cache._cache.expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)

        # Should still be valid but needs refresh
        assert cache.is_valid()
        assert cache._needs_refresh()

    def test_clear(self):
        """Can clear the cache."""
        cache = SecretCache(ttl_seconds=60)
        cache.set("test-api-key", "test-app-key")
        assert cache.is_valid()

        cache.clear()
        assert not cache.is_valid()
        assert cache.get_cached() is None


def create_mock_secretsmanager_client(secrets: dict):
    """Create a mock secretsmanager client context manager."""

    class MockSecretsManagerClient:
        async def get_secret_value(self, SecretId: str):
            if SecretId not in secrets:
                raise Exception(f"Secret {SecretId} not found")
            return {"SecretString": secrets[SecretId]}

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    return MockSecretsManagerClient()


def create_mock_session(secrets: dict):
    """Create a mock aioboto3 session."""
    mock_session = MagicMock()

    def mock_client(service, **kwargs):
        if service == "secretsmanager":
            return create_mock_secretsmanager_client(secrets)
        elif service == "sts":
            # Mock STS client for role assumption
            class MockSTSClient:
                async def assume_role(self, **kwargs):
                    return {
                        "Credentials": {
                            "AccessKeyId": "mock-access-key",
                            "SecretAccessKey": "mock-secret-key",
                            "SessionToken": "mock-session-token",
                        }
                    }

                async def __aenter__(self):
                    return self

                async def __aexit__(self, exc_type, exc_val, exc_tb):
                    pass

            return MockSTSClient()
        raise ValueError(f"Unknown service: {service}")

    mock_session.client = mock_client
    return mock_session


@pytest.mark.asyncio
class TestAWSSecretsManagerProvider:
    """Tests for AWSSecretsManagerProvider class."""

    async def test_fetch_separate_secrets(self):
        """Can fetch credentials from separate secrets."""
        secrets = {
            "/test/datadog/API_KEY": "test-datadog-api-key-12345",
            "/test/datadog/APP_KEY": "test-datadog-app-key-67890",
        }

        provider = AWSSecretsManagerProvider(
            api_key_secret="/test/datadog/API_KEY",
            app_key_secret="/test/datadog/APP_KEY",
            region="us-east-1",
            cache_ttl=60,
        )

        # Patch the session
        provider._session = create_mock_session(secrets)

        try:
            creds = await provider.get_credentials()

            assert creds.api_key == "test-datadog-api-key-12345"
            assert creds.app_key == "test-datadog-app-key-67890"
            assert creds.fetched_at is not None
            assert creds.expires_at > datetime.now(timezone.utc)
        finally:
            await provider.close()

    async def test_fetch_combined_secret(self):
        """Can fetch credentials from a combined JSON secret."""
        secrets = {
            "/test/datadog/combined": json.dumps({
                "DD_API_KEY": "combined-api-key",
                "DD_APP_KEY": "combined-app-key",
            }),
        }

        provider = AWSSecretsManagerProvider(
            api_key_secret="/test/datadog/combined",
            app_key_secret="/test/datadog/combined",  # Same path = combined
            region="us-east-1",
            cache_ttl=60,
        )

        provider._session = create_mock_session(secrets)

        try:
            creds = await provider.get_credentials()

            assert creds.api_key == "combined-api-key"
            assert creds.app_key == "combined-app-key"
        finally:
            await provider.close()

    async def test_caching(self):
        """Credentials are cached and not re-fetched."""
        secrets = {
            "/test/datadog/API_KEY": "test-api-key",
            "/test/datadog/APP_KEY": "test-app-key",
        }

        provider = AWSSecretsManagerProvider(
            api_key_secret="/test/datadog/API_KEY",
            app_key_secret="/test/datadog/APP_KEY",
            region="us-east-1",
            cache_ttl=3600,  # Long TTL to avoid refresh buffer triggering
        )

        provider._session = create_mock_session(secrets)

        try:
            # First call
            creds1 = await provider.get_credentials()

            # Second call should return same cached object
            creds2 = await provider.get_credentials()

            assert creds1 is creds2
            assert creds1.fetched_at == creds2.fetched_at
        finally:
            await provider.close()

    async def test_cache_refresh_on_expiry(self):
        """Cache is refreshed when expired."""
        secrets = {
            "/test/datadog/API_KEY": "test-api-key",
            "/test/datadog/APP_KEY": "test-app-key",
        }

        provider = AWSSecretsManagerProvider(
            api_key_secret="/test/datadog/API_KEY",
            app_key_secret="/test/datadog/APP_KEY",
            region="us-east-1",
            cache_ttl=1,  # Very short TTL
        )

        provider._session = create_mock_session(secrets)

        try:
            # First call
            creds1 = await provider.get_credentials()
            original_fetched_at = creds1.fetched_at

            # Manually expire
            provider._cache._cache.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)

            # Second call should refresh
            creds2 = await provider.get_credentials()

            assert creds2.fetched_at > original_fetched_at
        finally:
            await provider.close()

    async def test_graceful_degradation(self):
        """Returns cached credentials when AWS is unreachable."""
        secrets = {
            "/test/datadog/API_KEY": "test-api-key",
            "/test/datadog/APP_KEY": "test-app-key",
        }

        provider = AWSSecretsManagerProvider(
            api_key_secret="/test/datadog/API_KEY",
            app_key_secret="/test/datadog/APP_KEY",
            region="us-east-1",
            cache_ttl=3600,  # Long TTL
        )

        provider._session = create_mock_session(secrets)

        try:
            # First call - populate cache
            creds1 = await provider.get_credentials()

            # Force refresh by setting needs_refresh
            provider._cache._cache.expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)

            # Mock AWS failure
            with patch.object(
                provider, "_fetch_credentials_from_aws",
                side_effect=Exception("AWS unreachable")
            ):
                # Should return cached credentials
                creds2 = await provider.get_credentials()
                assert creds2.api_key == creds1.api_key
        finally:
            await provider.close()

    async def test_json_secret_with_value_key(self):
        """Can extract value from JSON secret with 'value' key."""
        secrets = {
            "/test/datadog/API_KEY": json.dumps({"value": "json-api-key"}),
            "/test/datadog/APP_KEY": json.dumps({"value": "json-app-key"}),
        }

        provider = AWSSecretsManagerProvider(
            api_key_secret="/test/datadog/API_KEY",
            app_key_secret="/test/datadog/APP_KEY",
            region="us-east-1",
            cache_ttl=60,
        )

        provider._session = create_mock_session(secrets)

        try:
            creds = await provider.get_credentials()
            assert creds.api_key == "json-api-key"
            assert creds.app_key == "json-app-key"
        finally:
            await provider.close()

    async def test_secret_not_found(self):
        """Raises error when secret doesn't exist."""
        secrets = {}  # Empty - no secrets

        provider = AWSSecretsManagerProvider(
            api_key_secret="/nonexistent/secret",
            app_key_secret="/also/nonexistent",
            region="us-east-1",
            cache_ttl=60,
        )

        provider._session = create_mock_session(secrets)

        try:
            with pytest.raises(Exception):
                await provider.get_credentials()
        finally:
            await provider.close()

    async def test_role_assumption(self):
        """Can assume IAM role before fetching secrets."""
        secrets = {
            "/test/datadog/API_KEY": "role-assumed-api-key",
            "/test/datadog/APP_KEY": "role-assumed-app-key",
        }

        provider = AWSSecretsManagerProvider(
            api_key_secret="/test/datadog/API_KEY",
            app_key_secret="/test/datadog/APP_KEY",
            region="us-east-1",
            role_arn="arn:aws:iam::123456789012:role/test-role",
            cache_ttl=60,
        )

        provider._session = create_mock_session(secrets)

        try:
            creds = await provider.get_credentials()
            assert creds.api_key == "role-assumed-api-key"
            assert creds.app_key == "role-assumed-app-key"
        finally:
            await provider.close()


class TestHelperFunctions:
    """Tests for module-level helper functions."""

    def test_is_aws_secrets_configured_with_defaults(self):
        """Returns True by default (defaults are provided)."""
        # Clear env vars - defaults should still apply
        with patch.dict(os.environ, {}, clear=False):
            # Remove any existing overrides
            os.environ.pop("AWS_SECRET_API_KEY", None)
            os.environ.pop("AWS_SECRET_APP_KEY", None)

            import importlib
            from datadog_mcp.utils import secrets_provider
            importlib.reload(secrets_provider)

            # Should be True because defaults are provided
            assert secrets_provider.is_aws_secrets_configured() is True
            # Verify defaults are applied
            assert secrets_provider.AWS_SECRET_API_KEY == "/DEVELOPMENT/datadog/API_KEY"
            assert secrets_provider.AWS_SECRET_APP_KEY == "/DEVELOPMENT/datadog/APP_KEY"
            assert secrets_provider.AWS_PROFILE == "default"

    def test_is_aws_secrets_configured_with_custom_values(self):
        """Custom env vars override the defaults."""
        with patch.dict(os.environ, {
            "AWS_SECRET_API_KEY": "/custom/api_key",
            "AWS_SECRET_APP_KEY": "/custom/app_key",
            "AWS_PROFILE": "my-profile",
        }):
            import importlib
            from datadog_mcp.utils import secrets_provider
            importlib.reload(secrets_provider)

            assert secrets_provider.is_aws_secrets_configured() is True
            assert secrets_provider.AWS_SECRET_API_KEY == "/custom/api_key"
            assert secrets_provider.AWS_SECRET_APP_KEY == "/custom/app_key"
            assert secrets_provider.AWS_PROFILE == "my-profile"


@pytest.mark.asyncio
class TestGlobalProvider:
    """Tests for global provider management."""

    async def test_get_and_close_provider(self):
        """Can get and close global provider."""
        # Clear any env var overrides and reload with defaults
        os.environ.pop("AWS_SECRET_API_KEY", None)
        os.environ.pop("AWS_SECRET_APP_KEY", None)
        os.environ.pop("AWS_PROFILE", None)

        import importlib
        from datadog_mcp.utils import secrets_provider
        importlib.reload(secrets_provider)

        # Reset global state first
        await secrets_provider.close_secret_provider()

        # Use the default secret paths that the reloaded module will use
        # After reload without env vars, module uses DEFAULT_* constants
        default_api = secrets_provider.AWS_SECRET_API_KEY  # Will be DEFAULT after reload
        default_app = secrets_provider.AWS_SECRET_APP_KEY

        secrets = {
            default_api: "global-api-key",
            default_app: "global-app-key",
        }

        with patch.object(secrets_provider, "aioboto3") as mock_aioboto3:
            mock_aioboto3.Session.return_value = create_mock_session(secrets)

            provider = await secrets_provider.get_secret_provider()
            assert provider is not None

            creds = await provider.get_credentials()
            assert creds.api_key == "global-api-key"

            await secrets_provider.close_secret_provider()


@pytest.mark.asyncio
class TestConcurrency:
    """Tests for concurrent access safety."""

    async def test_concurrent_access(self):
        """Multiple concurrent requests share the same cached credentials."""
        secrets = {
            "/test/datadog/API_KEY": "concurrent-api-key",
            "/test/datadog/APP_KEY": "concurrent-app-key",
        }

        provider = AWSSecretsManagerProvider(
            api_key_secret="/test/datadog/API_KEY",
            app_key_secret="/test/datadog/APP_KEY",
            region="us-east-1",
            cache_ttl=3600,  # Long TTL to avoid refresh buffer triggering
        )

        provider._session = create_mock_session(secrets)

        try:
            # Launch many concurrent requests
            tasks = [provider.get_credentials() for _ in range(10)]
            results = await asyncio.gather(*tasks)

            # All should return the same cached object
            first = results[0]
            for cred in results[1:]:
                assert cred is first
        finally:
            await provider.close()


class TestExtractValue:
    """Tests for the _extract_value helper method."""

    def test_plain_text(self):
        """Extracts plain text secrets."""
        provider = AWSSecretsManagerProvider(
            api_key_secret="/test",
            app_key_secret="/test",
            region="us-east-1",
        )

        result = provider._extract_value("my-secret-value")
        assert result == "my-secret-value"

    def test_plain_text_with_whitespace(self):
        """Strips whitespace from plain text secrets."""
        provider = AWSSecretsManagerProvider(
            api_key_secret="/test",
            app_key_secret="/test",
            region="us-east-1",
        )

        result = provider._extract_value("  my-secret-value  \n")
        assert result == "my-secret-value"

    def test_json_with_value_key(self):
        """Extracts 'value' key from JSON secrets."""
        provider = AWSSecretsManagerProvider(
            api_key_secret="/test",
            app_key_secret="/test",
            region="us-east-1",
        )

        result = provider._extract_value('{"value": "extracted"}')
        assert result == "extracted"

    def test_json_with_secret_key(self):
        """Extracts 'secret' key from JSON secrets."""
        provider = AWSSecretsManagerProvider(
            api_key_secret="/test",
            app_key_secret="/test",
            region="us-east-1",
        )

        result = provider._extract_value('{"secret": "my-secret"}')
        assert result == "my-secret"

    def test_json_with_dd_api_key(self):
        """Extracts DD_API_KEY from JSON secrets."""
        provider = AWSSecretsManagerProvider(
            api_key_secret="/test",
            app_key_secret="/test",
            region="us-east-1",
        )

        result = provider._extract_value('{"DD_API_KEY": "datadog-key"}')
        assert result == "datadog-key"
