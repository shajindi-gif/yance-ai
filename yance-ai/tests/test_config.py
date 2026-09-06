import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_production_rejects_default_secrets():
    with pytest.raises(ValidationError):
        Settings(
            app_env="production",
            jwt_secret="change-me-in-production-at-least-32-characters",
            bootstrap_token="change-bootstrap-token",
            tenant_provisioning_token="change-tenant-provisioning-token",
        )


def test_cors_origins_are_split():
    config = Settings(cors_origins="https://a.example, https://b.example")
    assert config.cors_origin_list == ["https://a.example", "https://b.example"]


def test_production_rejects_demo_features_even_with_rotated_secrets():
    with pytest.raises(ValidationError, match="Demo features must be disabled"):
        Settings(
            app_env="production",
            jwt_secret="production-jwt-secret-with-at-least-32-characters",
            bootstrap_token="production-bootstrap-token",
            tenant_provisioning_token="production-provisioning-token",
            demo_features_enabled=True,
        )


def test_financial_configuration_has_no_code_defaults():
    config = Settings(_env_file=None)
    assert config.company_tax_id == ""
    assert config.company_bank_account == ""
    assert config.demo_features_enabled is False


def test_production_document_ingestion_requires_fail_closed_malware_scanning():
    with pytest.raises(ValidationError, match="MALWARE_SCAN_MODE=required"):
        Settings(
            app_env="production",
            jwt_secret="production-jwt-secret-with-at-least-32-characters",
            bootstrap_token="production-bootstrap-token",
            tenant_provisioning_token="production-provisioning-token",
            api_key_pepper="production-api-key-pepper-at-least-32-characters",
            malware_scan_mode="disabled",
        )
