"""配置管理：环境变量 / .env 加载 + LLM 工厂。"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Agent Orchestration Platform"
    debug: bool = False

    # LLM
    llm_provider: str = "deepseek"  # deepseek | mock
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    llm_temperature: float = 0.3
    llm_max_tokens: int = 4096
    llm_timeout: float = 120.0
    llm_max_retries: int = 3          # 429/5xx/超时 等瞬时错误的指数退避重试次数
    llm_retry_backoff: float = 1.5    # 首次退避秒数（后续翻倍）

    # 检索
    retriever_type: str = "hybrid"    # bm25 | semantic | hybrid
    embedding_model: str = "BAAI/bge-small-zh-v1.5"

    # 编排并发
    max_concurrency: int = 4          # 动态扇出时的并发 LLM 调用上限（限流保护）


@lru_cache
def get_settings() -> Settings:
    return Settings()


def build_llm(settings: Settings | None = None):
    """根据配置构建 LLM 客户端（惰性导入，离线测试时不强制依赖 openai）。"""
    settings = settings or get_settings()
    if settings.llm_provider == "mock":
        from app.core.llm.mock import MockLLM

        return MockLLM()
    from app.core.llm.deepseek import DeepSeekLLM

    return DeepSeekLLM(settings)
