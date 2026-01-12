"""Tests for DD_SITE multi-region support."""

import os
import pytest
from unittest.mock import patch


class TestDDSiteValidation:
    """Test DD_SITE environment variable handling."""

    def test_default_site_is_us1(self):
        """Default DD_SITE should be datadoghq.com (US1)."""
        with patch.dict(os.environ, {"DD_API_KEY": "test", "DD_APP_KEY": "test"}, clear=True):
            # Remove DD_SITE if present
            os.environ.pop("DD_SITE", None)
            
            # Re-import to test default
            import importlib
            import datadog_mcp.utils.datadog_client as client
            importlib.reload(client)
            
            assert client.DD_SITE == "datadoghq.com"
            assert client.DATADOG_API_URL == "https://api.datadoghq.com"

    def test_eu_site_configuration(self):
        """DD_SITE=datadoghq.eu should configure EU endpoint."""
        with patch.dict(os.environ, {
            "DD_API_KEY": "test",
            "DD_APP_KEY": "test",
            "DD_SITE": "datadoghq.eu"
        }, clear=True):
            import importlib
            import datadog_mcp.utils.datadog_client as client
            importlib.reload(client)
            
            assert client.DD_SITE == "datadoghq.eu"
            assert client.DATADOG_API_URL == "https://api.datadoghq.eu"

    def test_us3_site_configuration(self):
        """DD_SITE=us3.datadoghq.com should configure US3 endpoint."""
        with patch.dict(os.environ, {
            "DD_API_KEY": "test",
            "DD_APP_KEY": "test",
            "DD_SITE": "us3.datadoghq.com"
        }, clear=True):
            import importlib
            import datadog_mcp.utils.datadog_client as client
            importlib.reload(client)
            
            assert client.DD_SITE == "us3.datadoghq.com"
            assert client.DATADOG_API_URL == "https://api.us3.datadoghq.com"

    def test_us5_site_configuration(self):
        """DD_SITE=us5.datadoghq.com should configure US5 endpoint."""
        with patch.dict(os.environ, {
            "DD_API_KEY": "test",
            "DD_APP_KEY": "test",
            "DD_SITE": "us5.datadoghq.com"
        }, clear=True):
            import importlib
            import datadog_mcp.utils.datadog_client as client
            importlib.reload(client)
            
            assert client.DD_SITE == "us5.datadoghq.com"
            assert client.DATADOG_API_URL == "https://api.us5.datadoghq.com"

    def test_ap1_site_configuration(self):
        """DD_SITE=ap1.datadoghq.com should configure AP1 (Japan) endpoint."""
        with patch.dict(os.environ, {
            "DD_API_KEY": "test",
            "DD_APP_KEY": "test",
            "DD_SITE": "ap1.datadoghq.com"
        }, clear=True):
            import importlib
            import datadog_mcp.utils.datadog_client as client
            importlib.reload(client)
            
            assert client.DD_SITE == "ap1.datadoghq.com"
            assert client.DATADOG_API_URL == "https://api.ap1.datadoghq.com"

    def test_gov_site_configuration(self):
        """DD_SITE=ddog-gov.com should configure US1-FED (GovCloud) endpoint."""
        with patch.dict(os.environ, {
            "DD_API_KEY": "test",
            "DD_APP_KEY": "test",
            "DD_SITE": "ddog-gov.com"
        }, clear=True):
            import importlib
            import datadog_mcp.utils.datadog_client as client
            importlib.reload(client)
            
            assert client.DD_SITE == "ddog-gov.com"
            assert client.DATADOG_API_URL == "https://api.ddog-gov.com"

    def test_invalid_site_with_special_chars_raises_error(self):
        """DD_SITE with invalid characters should raise ValueError."""
        with patch.dict(os.environ, {
            "DD_API_KEY": "test",
            "DD_APP_KEY": "test",
            "DD_SITE": "https://evil.com/"
        }, clear=True):
            import importlib
            import datadog_mcp.utils.datadog_client as client
            
            with pytest.raises(ValueError, match="Invalid DD_SITE value"):
                importlib.reload(client)

    def test_empty_site_raises_error(self):
        """Empty DD_SITE should raise ValueError."""
        with patch.dict(os.environ, {
            "DD_API_KEY": "test",
            "DD_APP_KEY": "test",
            "DD_SITE": ""
        }, clear=True):
            import importlib
            import datadog_mcp.utils.datadog_client as client
            
            with pytest.raises(ValueError, match="Invalid DD_SITE value"):
                importlib.reload(client)

    def test_sdk_configuration_includes_site(self):
        """SDK Configuration should include server_variables site."""
        with patch.dict(os.environ, {
            "DD_API_KEY": "test",
            "DD_APP_KEY": "test",
            "DD_SITE": "datadoghq.eu"
        }, clear=True):
            import importlib
            import datadog_mcp.utils.datadog_client as client
            importlib.reload(client)
            
            config = client.get_datadog_configuration()
            assert config.server_variables["site"] == "datadoghq.eu"

    def test_unknown_site_logs_warning_but_proceeds(self, caplog):
        """Unknown DD_SITE should log warning but not fail."""
        import logging
        
        with patch.dict(os.environ, {
            "DD_API_KEY": "test",
            "DD_APP_KEY": "test",
            "DD_SITE": "us99.datadoghq.com"  # Hypothetical future region
        }, clear=True):
            import importlib
            import datadog_mcp.utils.datadog_client as client
            
            with caplog.at_level(logging.WARNING):
                importlib.reload(client)
            
            # Should proceed with the unknown site
            assert client.DD_SITE == "us99.datadoghq.com"
            assert client.DATADOG_API_URL == "https://api.us99.datadoghq.com"
            # Should have logged a warning
            assert "not a known Datadog site" in caplog.text


class TestValidDDSites:
    """Test that VALID_DD_SITES constant is complete."""

    def test_valid_sites_includes_all_regions(self):
        """VALID_DD_SITES should include all official Datadog regions."""
        # Need to import without triggering credential check
        with patch.dict(os.environ, {
            "DD_API_KEY": "test",
            "DD_APP_KEY": "test"
        }, clear=True):
            import importlib
            import datadog_mcp.utils.datadog_client as client
            importlib.reload(client)
            
            expected_sites = {
                "datadoghq.com",      # US1
                "us3.datadoghq.com",  # US3
                "us5.datadoghq.com",  # US5
                "datadoghq.eu",       # EU1
                "ap1.datadoghq.com",  # AP1
                "ddog-gov.com",       # US1-FED
            }
            
            assert client.VALID_DD_SITES == expected_sites
