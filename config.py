from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    GROQ_API_KEY: str | None = None
    DATABASE_URL: str | None = None  # e.g. postgresql://user:password@localhost:5432/emr_db
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    class Config:
        env_file = ".env"


settings = Settings()
