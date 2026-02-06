"""
AWS Secrets Manager integration for Datadog credentials.

Provides secure credential fetching with in-memory caching and automatic refresh.
"""

import asyncio
import json
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

import aioboto3

logger = logging.getLogger(__name__)

# Default configuration - works out of the box with standard setup
DEFAULT_API_KEY_SECRET = "/DEVELOPMENT/datadog/API_KEY"
DEFAULT_APP_KEY_SECRET = "/DEVELOPMENT/datadog/APP_KEY"
DEFAULT_REGION = "us-west-2"
DEFAULT_PROFILE = "default"
DEFAULT_CACHE_TTL = 3000  # 50 minutes

# Configuration from environment (with defaults)
AWS_SECRET_API_KEY = os.getenv("AWS_SECRET_API_KEY", DEFAULT_API_KEY_SECRET)
AWS_SECRET_APP_KEY = os.getenv("AWS_SECRET_APP_KEY", DEFAULT_APP_KEY_SECRET)
AWS_REGION = os.getenv("AWS_REGION", DEFAULT_REGION)
AWS_PROFILE = os.getenv("AWS_PROFILE", DEFAULT_PROFILE)
AWS_ROLE_ARN = os.getenv("AWS_ROLE_ARN")  # No default - optional
SECRET_CACHE_TTL = int(os.getenv("SECRET_CACHE_TTL", str(DEFAULT_CACHE_TTL)))


@dataclass
class DatadogCredentials:
    """Container for Datadog API credentials."""
    api_key: str
    app_key: str
    fetched_at: datetime
    expires_at: datetime


class SecretCache:
    """Thread-safe in-memory cache for secrets with TTL and automatic refresh."""

    def __init__(self, ttl_seconds: int = SECRET_CACHE_TTL):
        self._cache: Optional[DatadogCredentials] = None
        self._lock = asyncio.Lock()
        self._ttl = timedelta(seconds=ttl_seconds)
        self._refresh_buffer = timedelta(minutes=10)

    def _needs_refresh(self) -> bool:
        """Check if cache needs refresh (expired or within refresh buffer)."""
        if self._cache is None:
            return True
        # Refresh if within buffer of expiry time
        refresh_threshold = self._cache.expires_at - self._refresh_buffer
        return datetime.now(timezone.utc) >= refresh_threshold

    def is_valid(self) -> bool:
        """Check if cache has valid (non-expired) credentials."""
        if self._cache is None:
            return False
        return datetime.now(timezone.utc) < self._cache.expires_at

    def get_cached(self) -> Optional[DatadogCredentials]:
        """Get cached credentials without refresh (for graceful degradation)."""
        if self.is_valid():
            return self._cache
        return None

    def set(self, api_key: str, app_key: str) -> DatadogCredentials:
        """Store credentials in cache with TTL."""
        now = datetime.now(timezone.utc)
        self._cache = DatadogCredentials(
            api_key=api_key,
            app_key=app_key,
            fetched_at=now,
            expires_at=now + self._ttl,
        )
        return self._cache

    def clear(self) -> None:
        """Clear the cache."""
        self._cache = None


class SecretProvider(ABC):
    """Abstract base class for secret providers."""

    @abstractmethod
    async def get_credentials(self) -> DatadogCredentials:
        """Fetch Datadog credentials."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Clean up resources."""
        pass


class AWSSecretsManagerProvider(SecretProvider):
    """
    Fetches Datadog credentials from AWS Secrets Manager.

    Supports two secret storage patterns:
    1. Separate secrets: AWS_SECRET_API_KEY and AWS_SECRET_APP_KEY point to individual secrets
    2. Combined secret: Both keys stored in a single JSON secret (DD_API_KEY and DD_APP_KEY fields)

    Uses boto3's credential chain with configurable profile (SSO, IAM roles, env vars, etc.)
    """

    def __init__(
        self,
        api_key_secret: str = AWS_SECRET_API_KEY,
        app_key_secret: str = AWS_SECRET_APP_KEY,
        region: str = AWS_REGION,
        profile: str = AWS_PROFILE,
        role_arn: Optional[str] = AWS_ROLE_ARN,
        cache_ttl: int = SECRET_CACHE_TTL,
    ):
        self._api_key_secret = api_key_secret
        self._app_key_secret = app_key_secret
        self._region = region
        self._profile = profile
        self._role_arn = role_arn
        self._cache = SecretCache(ttl_seconds=cache_ttl)
        self._session: Optional[aioboto3.Session] = None

    async def _get_session(self) -> aioboto3.Session:
        """Get or create aioboto3 session with configured profile."""
        if self._session is None:
            self._session = aioboto3.Session(profile_name=self._profile)
        return self._session

    async def _assume_role_if_needed(self, session: aioboto3.Session):
        """
        Assume IAM role if AWS_ROLE_ARN is configured.
        Returns credentials dict or None to use default chain.
        """
        if not self._role_arn:
            return None

        async with session.client("sts", region_name=self._region) as sts:
            response = await sts.assume_role(
                RoleArn=self._role_arn,
                RoleSessionName="datadog-mcp-secrets",
            )
            creds = response["Credentials"]
            return {
                "aws_access_key_id": creds["AccessKeyId"],
                "aws_secret_access_key": creds["SecretAccessKey"],
                "aws_session_token": creds["SessionToken"],
            }

    async def _fetch_secret(self, secret_id: str, assumed_creds: Optional[dict] = None) -> str:
        """Fetch a single secret value from AWS Secrets Manager."""
        session = await self._get_session()

        client_kwargs = {"region_name": self._region}
        if assumed_creds:
            client_kwargs.update(assumed_creds)

        async with session.client("secretsmanager", **client_kwargs) as client:
            response = await client.get_secret_value(SecretId=secret_id)

            # Handle both string and binary secrets
            if "SecretString" in response:
                return response["SecretString"]
            else:
                # Binary secret - decode as UTF-8
                import base64
                return base64.b64decode(response["SecretBinary"]).decode("utf-8")

    async def _fetch_credentials_from_aws(self) -> tuple[str, str]:
        """Fetch both API and APP keys from AWS Secrets Manager."""
        session = await self._get_session()
        assumed_creds = await self._assume_role_if_needed(session)

        # Check if both secrets point to the same path (combined secret pattern)
        if self._api_key_secret == self._app_key_secret:
            # Combined secret with JSON structure
            secret_value = await self._fetch_secret(self._api_key_secret, assumed_creds)
            try:
                secret_data = json.loads(secret_value)
                api_key = secret_data.get("DD_API_KEY") or secret_data.get("api_key")
                app_key = secret_data.get("DD_APP_KEY") or secret_data.get("app_key")
                if not api_key or not app_key:
                    raise ValueError(
                        f"Combined secret must contain DD_API_KEY/api_key and DD_APP_KEY/app_key fields"
                    )
                return api_key, app_key
            except json.JSONDecodeError:
                raise ValueError(
                    f"Combined secret at {self._api_key_secret} is not valid JSON"
                )
        else:
            # Separate secrets - fetch both in parallel
            api_key_task = self._fetch_secret(self._api_key_secret, assumed_creds)
            app_key_task = self._fetch_secret(self._app_key_secret, assumed_creds)

            api_key, app_key = await asyncio.gather(api_key_task, app_key_task)

            # Secrets might be plain text or JSON with a "value" field
            api_key = self._extract_value(api_key)
            app_key = self._extract_value(app_key)

            return api_key, app_key

    def _extract_value(self, secret_string: str) -> str:
        """Extract value from secret (handles both plain text and JSON)."""
        secret_string = secret_string.strip()

        # Try parsing as JSON first
        if secret_string.startswith("{"):
            try:
                data = json.loads(secret_string)
                # Look for common key names
                for key in ["value", "secret", "key", "DD_API_KEY", "DD_APP_KEY"]:
                    if key in data:
                        return data[key]
                # If JSON but no recognized key, return first value
                if data:
                    return next(iter(data.values()))
            except json.JSONDecodeError:
                pass

        # Plain text secret
        return secret_string

    async def get_credentials(self) -> DatadogCredentials:
        """
        Get Datadog credentials with caching and automatic refresh.

        Thread-safe: uses asyncio.Lock to prevent concurrent AWS calls.
        Graceful degradation: returns cached credentials if AWS is temporarily unreachable.
        """
        async with self._cache._lock:
            if not self._cache._needs_refresh():
                return self._cache._cache

            try:
                logger.info("Fetching Datadog credentials from AWS Secrets Manager")
                api_key, app_key = await self._fetch_credentials_from_aws()
                credentials = self._cache.set(api_key, app_key)
                logger.info("Successfully refreshed Datadog credentials from AWS")
                return credentials

            except Exception as e:
                # Graceful degradation: use cached credentials if available
                cached = self._cache.get_cached()
                if cached:
                    logger.warning(
                        f"Failed to refresh credentials from AWS ({e}), using cached credentials"
                    )
                    return cached

                logger.error(f"Failed to fetch credentials from AWS Secrets Manager: {e}")
                raise

    async def close(self) -> None:
        """Clean up resources."""
        self._cache.clear()
        self._session = None


# Global provider instance (lazy initialization)
_provider: Optional[SecretProvider] = None
_provider_lock = asyncio.Lock()


def is_aws_secrets_configured() -> bool:
    """
    Check if AWS Secrets Manager is configured.

    Always returns True since defaults are provided. The actual availability
    of credentials depends on AWS profile/SSO login status at runtime.
    """
    return bool(AWS_SECRET_API_KEY and AWS_SECRET_APP_KEY)


async def get_secret_provider() -> Optional[SecretProvider]:
    """
    Get or create the global secret provider instance.

    Uses defaults if environment variables are not set:
    - Secret paths: /DEVELOPMENT/datadog/API_KEY and /DEVELOPMENT/datadog/APP_KEY
    - Region: us-west-2
    - Profile: default

    Returns the provider instance (credentials are fetched lazily on first use).
    """
    global _provider

    if not is_aws_secrets_configured():
        return None

    async with _provider_lock:
        if _provider is None:
            _provider = AWSSecretsManagerProvider(
                api_key_secret=AWS_SECRET_API_KEY,
                app_key_secret=AWS_SECRET_APP_KEY,
                region=AWS_REGION,
                profile=AWS_PROFILE,
                role_arn=AWS_ROLE_ARN,
                cache_ttl=SECRET_CACHE_TTL,
            )
            logger.info(
                f"Initialized AWS Secrets Manager provider "
                f"(profile={AWS_PROFILE}, region={AWS_REGION}, "
                f"api_key={AWS_SECRET_API_KEY}, app_key={AWS_SECRET_APP_KEY})"
            )
        return _provider


async def close_secret_provider() -> None:
    """Close and clean up the global secret provider."""
    global _provider

    async with _provider_lock:
        if _provider is not None:
            await _provider.close()
            _provider = None
            logger.info("Closed AWS Secrets Manager provider")
