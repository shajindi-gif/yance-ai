import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_production_rejects_default_secrets():
    with pytest.raises(ValidationError):
        Settings(app_env="production")


def test_cors_origins_are_split():
    config = Settings(cors_origins="https://a.example, https://b.example")
    assert config.cors_origin_list == ["https://a.example", "https://b.example"]
