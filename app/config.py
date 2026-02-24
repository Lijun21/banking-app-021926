from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql://banking:banking@localhost:5432/banking_db"
    test_database_url: str = "postgresql://banking:banking@localhost:5433/banking_test"

    # JWT
    jwt_secret_key: str = "change-me-in-production-use-a-long-random-secret"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
