from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "Fitness Tracker"
    env: str = "dev"
    log_level: str = "INFO"
    database_url: str

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings() # type: ignore[call-arg]