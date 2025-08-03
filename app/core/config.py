from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App settings
    app_name: str = "PDF Processor API"
    app_version: str = "1.0.0"
    debug: bool = False

    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000

    # OpenAI API settings
    openai_api_url: str = Field(..., env="OPENAI_API_URL")
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    openai_timeout: int = Field(default=30, env="OPENAI_TIMEOUT")
    mmlm_model: str = Field(..., env="MMLM_MODEL")

    # File processing settings
    max_file_size: int = Field(default=50 * 1024 * 1024, env="MAX_FILE_SIZE")  # 50MB
    allowed_extensions: list[str] = [".pdf"]
    image_dpi: int = Field(default=300, env="IMAGE_DPI")
    image_format: str = Field(default="PNG", env="IMAGE_FORMAT")

    # Processing settings
    max_concurrent_requests: int = Field(default=10, env="MAX_CONCURRENT_REQUESTS")
    batch_size: int = Field(default=5, env="BATCH_SIZE")

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
