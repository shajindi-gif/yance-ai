from app.core.config import settings
from app.services.llm.providers.openai_compatible import OpenAICompatibleProvider

# 使用通义千问 text-embedding-v3（1024维，与原 bge-large-en-v1.5 兼容）
_embedding_provider = OpenAICompatibleProvider(
    name="qwen_embedding",
    api_key=settings.qwen_api_key,
    base_url=settings.qwen_base_url,
    embedding_model="text-embedding-v3",
)


async def embed_texts(inputs: list[str]) -> list[list[float]]:
    """便捷函数：使用通义千问生成文本 embedding 向量（1024维）。"""
    return await _embedding_provider.embed(inputs)
