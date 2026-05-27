from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "AegisForge"
    environment: str = "local"
    llm_provider: str = "mock"
    openai_api_key: str | None = None
    bedrock_region: str = "us-east-1"
    enable_autonomous_actions: bool = False


def get_settings() -> Settings:
    return Settings()
