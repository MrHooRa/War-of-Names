from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_env: str = "development"
    debug: bool = True
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    db_host: str = "db"
    db_port: int = 5432
    db_name: str = "war_of_names"
    db_user: str = "postgres"
    db_password: str = "postgres"

    cors_origin: str = "http://localhost:5173"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
