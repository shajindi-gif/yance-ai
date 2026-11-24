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
        forwarded_allow_ips="172.18.0.0/16",
    )
    assert config.document_ocr_provider == "tesseract"
    assert config.document_url_import_enabled is True


@pytest.mark.parametrize("secret", ["", "short", "REPLACE_WITH_OPENSSL_RAND_HEX_32"])
def test_production_rejects_weak_or_placeholder_jwt(secret):
    with pytest.raises(ValidationError, match="Production secrets must be replaced"):
        Settings(app_env="production", jwt_secret=secret, demo_features_enabled=False)


@pytest.mark.parametrize("value", ["127.0.0.1", "", "127.0.0.1, ::1"])
def test_production_rejects_loopback_only_forwarded_allow_ips(value):
    """ACC-04: loopback-only trust makes every client share the proxy's rate-limit identity."""
    with pytest.raises(ValidationError, match="reverse proxy"):
        Settings(
            _env_file=None,
            app_env="production",
            jwt_secret="production-jwt-secret-with-at-least-32-characters",
            bootstrap_token="production-bootstrap-token",
            tenant_provisioning_token="production-provisioning-token",
            api_key_pepper="production-api-key-pepper-at-least-32-characters",
            malware_scan_mode="required",
            clamd_host="clamav",
            document_ocr_enabled=True,
            forwarded_allow_ips=value,
        )


def test_production_environment_without_secrets_refuses_to_load(tmp_path):
    """ACC-12: a process that only says APP_ENV=production must not start on defaults."""
    import os
    import subprocess
    import sys
    from pathlib import Path

    backend_root = Path(__file__).resolve().parents[1]
    # Run from an empty directory so a developer's local .env cannot supply secrets.
    env = {
        "APP_ENV": "production",
        "PYTHONPATH": str(backend_root),
        "PATH": os.environ.get("PATH", ""),
        "HOME": str(tmp_path),
    }
    result = subprocess.run(
        [sys.executable, "-c", "import app.core.config"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode != 0
    assert "Production secrets must be replaced" in result.stderr
