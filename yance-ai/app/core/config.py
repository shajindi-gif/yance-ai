from functools import lru_cache
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "yance.ai API"
    app_env: Literal["development", "test", "staging", "production"] = "development"
    app_version: str = "0.1.0"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    cors_origins: str = "http://localhost:3000"

    database_url: str = "postgresql+psycopg://yance:yance_dev_password@db:5432/yance_dev"
    db_pool_size: int = 10
    db_max_overflow: int = 20

    jwt_secret: str = "change-me-in-production-at-least-32-characters"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    bootstrap_token: str = "change-bootstrap-token"
    tenant_provisioning_token: str = "change-tenant-provisioning-token"

    oss_endpoint: str = ""
    oss_internal_endpoint: str = ""
    oss_bucket: str = ""
    oss_access_key_id: str = ""
    oss_access_key_secret: str = ""
    oss_presign_expire_seconds: int = 900

    llm_default_provider: str = "mock"
    qwen_api_key: str = ""
    qwen_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    anthropic_api_key: str = ""

    # Workers AI Embedding
    workers_ai_api_key: str = ""
    workers_ai_base_url: str = "https://api.cloudflare.com/client/v4/accounts/9620a910f114a4ee7a5c45ef2d2b3bbd/ai/v1"
    embedding_model: str = "@cf/baai/bge-large-en-v1.5"

    # Stripe (legacy)
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_id: str = ""

    # Alipay 电脑网站支付
    alipay_app_id: str = ""
    alipay_private_key: str = ""       # 应用私钥（PEM格式，一行，\n替换为真实换行）
    alipay_public_key: str = ""        # 支付宝公钥
    alipay_notify_url: str = "https://yance.ai/api/v1/payments/alipay/notify"
    alipay_return_url: str = "https://yance.ai/success"
    alipay_gateway: str = "https://openapi.alipay.com/gateway.do"
    alipay_sandbox: bool = False       # True=沙箱环境

    # 公司对公账户（银行转账）
    company_name: str = "上海衍策引擎人工智能科技有限公司"
    company_tax_id: str = "91310104MAKDCJH00L"
    company_bank_name: str = "上海浦东发展银行"
    company_bank_account: str = "96530078801800000264"
    company_bank_card: str = "6232500101935514"

    log_level: str = "INFO"
    agent_log_prompts: bool = False
    trusted_proxy_count: int = 1

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        if self.app_env == "production":
            bad = {
                "jwt_secret": self.jwt_secret.startswith("change-"),
                "bootstrap_token": self.bootstrap_token.startswith("change-"),
                "tenant_provisioning_token": self.tenant_provisioning_token.startswith("change-"),
            }
            invalid = [name for name, value in bad.items() if value]
            if invalid:
                raise ValueError(f"Production secrets must be replaced: {', '.join(invalid)}")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
