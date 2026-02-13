"""Tests for security configuration validation"""

import os
from unittest.mock import patch

import pytest


class TestAWSCredentialValidation:
    """Test AWS credential security validation"""

    def test_production_requires_aws_credentials(self):
        """Production environment should require AWS credentials"""
        with patch.dict(os.environ, {"APP_ENV": "production"}, clear=False):
            # Remove any existing credentials
            env = os.environ.copy()
            env.pop("AWS_ACCESS_KEY_ID", None)
            env.pop("AWS_SECRET_ACCESS_KEY", None)
            env["APP_ENV"] = "production"

            with patch.dict(os.environ, env, clear=True):
                # Need to reload the module to pick up new env vars
                import importlib

                from pydantic import ValidationError

                import services.api.app.config as config_module

                with pytest.raises(ValidationError) as exc_info:
                    importlib.reload(config_module)

                error_str = str(exc_info.value)
                assert (
                    "aws_access_key_id" in error_str
                    or "aws_secret_access_key" in error_str
                )

    def test_development_allows_missing_credentials(self):
        """Development environment should allow missing credentials"""
        with patch.dict(
            os.environ,
            {"APP_ENV": "development"},
            clear=False,
        ):
            # Remove any existing credentials
            env = os.environ.copy()
            env.pop("AWS_ACCESS_KEY_ID", None)
            env.pop("AWS_SECRET_ACCESS_KEY", None)
            env["APP_ENV"] = "development"

            with patch.dict(os.environ, env, clear=True):
                import importlib

                import services.api.app.config as config_module

                # Should not raise
                importlib.reload(config_module)
                assert config_module.settings.aws_access_key_id is None
                assert config_module.settings.aws_secret_access_key is None


class TestJWTSecretValidation:
    """Test JWT secret security validation"""

    def test_rejects_placeholder_secrets(self):
        """Should reject obvious placeholder secrets"""
        from pydantic import ValidationError

        placeholders = [
            "your-secret-key-here-change-in-production",  # Contains "change-in-production"
            "changeme-this-is-a-test-key-value-here-123",  # Contains "changeme"
            "my-placeholder-key-value-for-testing-12345",  # Contains "placeholder"
        ]

        for placeholder in placeholders:
            env = {
                "APP_ENV": "production",
                "AWS_ACCESS_KEY_ID": "AKIAIOSFODNN7EXAMPLE",
                "AWS_SECRET_ACCESS_KEY": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
                "API_JWT_SECRET": placeholder,
            }

            with patch.dict(os.environ, env, clear=True):
                import importlib

                import services.api.app.config as config_module

                with pytest.raises(ValidationError) as exc_info:
                    importlib.reload(config_module)

                assert "insecure placeholder" in str(exc_info.value).lower()

    def test_requires_minimum_length(self):
        """Should require minimum 32 character secret"""
        from pydantic import ValidationError

        env = {
            "APP_ENV": "production",
            "AWS_ACCESS_KEY_ID": "AKIAIOSFODNN7EXAMPLE",
            "AWS_SECRET_ACCESS_KEY": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            "API_JWT_SECRET": "tooshort123",  # Less than 32 chars
        }

        with patch.dict(os.environ, env, clear=True):
            import importlib

            import services.api.app.config as config_module

            with pytest.raises(ValidationError) as exc_info:
                importlib.reload(config_module)

            assert "32 characters" in str(exc_info.value)

    def test_accepts_valid_secret(self):
        """Should accept valid JWT secrets"""
        valid_secret = "abcd1234efgh5678ijkl9012mnop3456qrst"

        env = {
            "APP_ENV": "production",
            "AWS_ACCESS_KEY_ID": "AKIAIOSFODNN7EXAMPLE",
            "AWS_SECRET_ACCESS_KEY": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            "API_JWT_SECRET": valid_secret,
        }

        with patch.dict(os.environ, env, clear=True):
            import importlib

            import services.api.app.config as config_module

            # Should not raise
            importlib.reload(config_module)
            assert config_module.settings.api_jwt_secret == valid_secret

    def test_development_allows_any_value(self):
        """Development mode allows any/no JWT secret value"""
        env = {
            "APP_ENV": "development",
        }

        with patch.dict(os.environ, env, clear=True):
            import importlib

            import services.api.app.config as config_module

            # Should not raise
            importlib.reload(config_module)
            # In dev, None is allowed
            assert config_module.settings.api_jwt_secret is None


class TestEndpointValidation:
    """Test endpoint URL security validation"""

    def test_rejects_localstack_in_production(self):
        """Should reject LocalStack endpoint in production"""
        from pydantic import ValidationError

        for endpoint in ["http://localstack:4566", "http://localhost:4566"]:
            env = {
                "APP_ENV": "production",
                "AWS_ACCESS_KEY_ID": "AKIAIOSFODNN7EXAMPLE",
                "AWS_SECRET_ACCESS_KEY": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
                "API_JWT_SECRET": "abcd1234efgh5678ijkl9012mnop3456qrst",
                "AWS_ENDPOINT_URL": endpoint,
            }

            with patch.dict(os.environ, env, clear=True):
                import importlib

                import services.api.app.config as config_module

                with pytest.raises(ValidationError) as exc_info:
                    importlib.reload(config_module)

                assert (
                    "localhost" in str(exc_info.value).lower()
                    or "localstack" in str(exc_info.value).lower()
                )

    def test_allows_localstack_in_development(self):
        """Should allow LocalStack endpoint in development"""
        env = {
            "APP_ENV": "development",
            "AWS_ENDPOINT_URL": "http://localstack:4566",
        }

        with patch.dict(os.environ, env, clear=True):
            import importlib

            import services.api.app.config as config_module

            # Should not raise
            importlib.reload(config_module)
            assert config_module.settings.aws_endpoint_url == "http://localstack:4566"

    def test_allows_none_endpoint_in_production(self):
        """Production should work without explicit endpoint (uses real AWS)"""
        env = {
            "APP_ENV": "production",
            "AWS_ACCESS_KEY_ID": "AKIAIOSFODNN7EXAMPLE",
            "AWS_SECRET_ACCESS_KEY": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            "API_JWT_SECRET": "abcd1234efgh5678ijkl9012mnop3456qrst",
        }

        with patch.dict(os.environ, env, clear=True):
            import importlib

            import services.api.app.config as config_module

            # Should not raise
            importlib.reload(config_module)
            assert config_module.settings.aws_endpoint_url is None


class TestStartupValidation:
    """Test startup configuration validation"""

    def test_startup_validation_passes_in_development(self):
        """Should pass validation in development mode"""
        env = {"APP_ENV": "development"}

        with patch.dict(os.environ, env, clear=True):
            import importlib

            import services.api.app.config as config_module

            importlib.reload(config_module)

            # Import and test the startup validation function
            import services.api.app.main as main_module

            importlib.reload(main_module)

            # Should not raise
            main_module._validate_startup_configuration()

    def test_startup_validation_fails_with_missing_config(self):
        """Should fail at startup with invalid production config"""
        env = {
            "APP_ENV": "production",
            # Missing AWS credentials and JWT secret
        }

        with patch.dict(os.environ, env, clear=True):
            import importlib

            # Config validation should fail first
            from pydantic import ValidationError

            import services.api.app.config as config_module

            with pytest.raises(ValidationError):
                importlib.reload(config_module)

    def test_startup_validation_passes_with_valid_config(self):
        """Should pass validation with complete production config"""
        env = {
            "APP_ENV": "production",
            "AWS_ACCESS_KEY_ID": "AKIAIOSFODNN7EXAMPLE",
            "AWS_SECRET_ACCESS_KEY": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            "API_JWT_SECRET": "abcd1234efgh5678ijkl9012mnop3456qrst",
        }

        with patch.dict(os.environ, env, clear=True):
            import importlib

            import services.api.app.config as config_module

            importlib.reload(config_module)

            import services.api.app.main as main_module

            importlib.reload(main_module)

            # Should not raise
            main_module._validate_startup_configuration()
