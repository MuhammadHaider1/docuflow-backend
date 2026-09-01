from typing import Any

from pydantic import PostgresDsn, ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_ignore_empty=True, extra="ignore"
    )

    PROJECT_NAME: str = "Docuflow SaaS"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str
    ALGORITHIM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # DATABASE settings
    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str
    DB_PORT: int
    DB_NAME: str

    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET_NAME: str = "docuflow-documents"
    MINIO_SECURE: bool = False

    # Google Gemini API Key
    GOOGLE_API_KEY: str = ""

    # 🟢 Yahan defaults update karein taake field required na rahe validation ke waqt
    DATABASE_URI: str = ""

    @field_validator("DATABASE_URI", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: Any, info: ValidationInfo) -> Any:
        # Agar .env mein pehle se poori link string maujood hai to usey chalne dein
        if isinstance(v, str) and v.startswith("postgresql"):
            return v

        # Agar .env mein DATABASE_URI khali hai ya abhi tak generate nahi hui, to variables se khud banayein
        db_user = info.data.get("DB_USER")
        db_password = info.data.get("DB_PASSWORD")
        db_host = info.data.get("DB_HOST")
        db_port = info.data.get("DB_PORT")
        db_name = info.data.get("DB_NAME")

        # Fallback security check agar variables bhi missing hon test runs mein
        if not all([db_user, db_host, db_name]):
            return "postgresql+asyncpg://postgres:postgres@localhost:5432/docuflow_db"

        # Async connection string for宣SQLAlchemy (asyncpg)
        return str(
            PostgresDsn.build(
                scheme="postgresql+asyncpg",
                username=db_user,
                password=db_password,
                host=db_host,
                port=db_port,
                path=db_name,
            )
        )


settings = Settings()  # type: ignore
