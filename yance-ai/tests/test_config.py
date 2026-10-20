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


def test_production_document_ingestion_requires_ocr():
    with pytest.raises(ValidationError, match="DOCUMENT_OCR_ENABLED=true"):
        Settings(
            app_env="production",
            jwt_secret="production-jwt-secret-with-at-least-32-characters",
            bootstrap_token="production-bootstrap-token",
            tenant_provisioning_token="production-provisioning-token",
            api_key_pepper="production-api-key-pepper-at-least-32-characters",
            malware_scan_mode="required",
            clamd_host="clamav",
            document_ocr_enabled=False,
        )


def test_production_document_ingestion_accepts_fail_closed_ocr_configuration():
    config = Settings(
        _env_file=None,
        app_env="production",
        jwt_secret="production-jwt-secret-with-at-least-32-characters",
        bootstrap_token="production-bootstrap-token",
        tenant_provisioning_token="production-provisioning-token",
        api_key_pepper="production-api-key-pepper-at-least-32-characters",
        malware_scan_mode="required",
        clamd_host="clamav",
        document_ocr_enabled=True,
    )
    assert config.document_ocr_provider == "tesseract"
    assert config.document_url_import_enabled is True


@pytest.mark.parametrize("secret", ["", "short", "REPLACE_WITH_OPENSSL_RAND_HEX_32"])
def test_production_rejects_weak_or_placeholder_jwt(secret):
    with pytest.raises(ValidationError, match="Production secrets must be replaced"):
        Settings(app_env="production", jwt_secret=secret, demo_features_enabled=False)
