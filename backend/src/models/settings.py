"""应用配置，从环境变量加载。"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """全局配置，API key 从 .env 文件或环境变量读取。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 高德地图 API
    amap_api_key: str = ""
    amap_api_base: str = "https://restapi.amap.com/v3"

    # LLM API
    llm_provider: str = "deepseek"
    deepseek_api_key: str = ""
    deepseek_api_base: str = "https://api.deepseek.com"
    claude_api_key: str = ""

    # 应用
    debug: bool = False
    log_level: str = "INFO"
