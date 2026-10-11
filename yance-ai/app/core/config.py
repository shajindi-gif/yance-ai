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
    api_key_pepper: str = "change-api-key-pepper-at-least-32-characters"

    oss_endpoint: str = ""
    oss_internal_endpoint: str = ""
    oss_bucket: str = ""
    oss_access_key_id: str = ""
    oss_access_key_secret: str = ""
    oss_presign_expire_seconds: int = 900
    document_upload_max_bytes: int = 25 * 1024 * 1024
    document_extracted_text_max_chars: int = 2_000_000
    document_archive_max_entries: int = 10_000
    document_archive_max_uncompressed_bytes: int = 100 * 1024 * 1024
    document_archive_max_compression_ratio: int = 100
    document_workbook_max_rows: int = 25_000
    document_workbook_max_cells: int = 250_000
    document_chunk_size_chars: int = 1_600
    document_chunk_overlap_chars: int = 200
    document_ingestion_lease_seconds: int = 300
    document_ingestion_max_attempts: int = 3
    document_ocr_enabled: bool = False
    document_ocr_provider: Literal["tesseract"] = "tesseract"
    document_ocr_languages: str = "chi_sim+eng"
    document_ocr_max_pages: int = 40
    document_ocr_dpi: int = 200
    document_ocr_max_pixels_per_page: int = 25_000_000
    document_ocr_page_timeout_seconds: float = 30.0
    document_url_import_enabled: bool = True
    document_url_max_redirects: int = 3
    document_url_connect_timeout_seconds: float = 5.0
    document_url_read_timeout_seconds: float = 15.0
    document_url_total_timeout_seconds: float = 30.0
    malware_scan_mode: Literal["disabled", "optional", "required"] = "disabled"
    clamd_host: str = ""
    clamd_port: int = 3310
    clamd_timeout_seconds: float = 15.0

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
    workers_ai_base_url: str = (
        "https://api.cloudflare.com/client/v4/accounts/9620a910f114a4ee7a5c45ef2d2b3bbd/ai/v1"
    )
    embedding_model: str = "@cf/baai/bge-large-en-v1.5"

    # Stripe (legacy)
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_id: str = ""

    demo_features_enabled: bool = False
    eval_dataset_root: str = "evals/datasets"

    # Alipay 电脑网站支付
    alipay_app_id: str = ""
    alipay_seller_id: str = ""
    alipay_private_key: str = ""  # 应用私钥（PEM格式，一行，\n替换为真实换行）
    alipay_public_key: str = ""  # 支付宝公钥
    alipay_notify_url: str = "https://yance.ai/api/v1/payments/alipay/notify"
    alipay_return_url: str = "https://yance.ai/success"
    alipay_gateway: str = "https://openapi.alipay.com/gateway.do"
    alipay_sandbox: bool = False  # True=沙箱环境

    # 微信支付 APIv3（直连商户，Native 扫码；复用已验证商户，独立回调域名）
    wxpay_mode: str = "direct"  # direct | partner
    wxpay_mch_id: str = ""
    wxpay_app_id: str = ""
    wxpay_serial_no: str = ""  # 商户 API 证书序列号
    wxpay_private_key: str = ""  # apiclient_key.pem 内容（单行，\n 表示换行）
    wxpay_apiv3_key: str = ""  # 32 位 APIv3 密钥
    wxpay_notify_url: str = "https://api.yance.ai/api/v1/payments/wechat/notify"
    wxpay_gateway: str = "https://api.mch.weixin.qq.com"
    # 微信支付公钥模式（新商户无平台证书）
    wxpay_pubkey_id: str = ""  # PUB_KEY_ID_xxx
    wxpay_pubkey: str = ""  # 微信支付公钥 PEM（单行，\n 表示换行）
    # 服务商模式字段（direct 模式留空）
    wxpay_sp_mch_id: str = ""
    wxpay_sp_app_id: str = ""
    wxpay_sub_mch_id: str = ""

    # 公司对公账户（银行转账）
    company_name: str = ""
    company_tax_id: str = ""
    company_bank_name: str = ""
    company_bank_account: str = ""

    log_level: str = "INFO"
    agent_log_prompts: bool = False
    agent_worker_poll_seconds: float = 1.0
    agent_lease_seconds: int = 180
    agent_max_retries: int = 2
    trusted_proxy_count: int = 1

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        if self.app_env == "production":
            if self.demo_features_enabled:
                raise ValueError("Demo features must be disabled in production")
            bad = {
                "jwt_secret": self.jwt_secret.startswith("change-"),
                "bootstrap_token": self.bootstrap_token.startswith("change-"),
                "tenant_provisioning_token": self.tenant_provisioning_token.startswith("change-"),
                "api_key_pepper": self.api_key_pepper.startswith("change-"),
            }
            invalid = [name for name, value in bad.items() if value]
            if invalid:
                raise ValueError(f"Production secrets must be replaced: {', '.join(invalid)}")
            if self.malware_scan_mode != "required":
                raise ValueError("Production document ingestion requires MALWARE_SCAN_MODE=required")
            if not self.clamd_host:
                raise ValueError("Production document ingestion requires CLAMD_HOST")
            if not self.document_ocr_enabled:
                raise ValueError("Production document ingestion requires DOCUMENT_OCR_ENABLED=true")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
