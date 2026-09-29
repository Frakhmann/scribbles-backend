from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # DB & JWT
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # SMTP
    SMTP_SERVER: str
    SMTP_PORT: int
    SMTP_USER: str
    SMTP_PASSWORD: str

    # где брать переменные и что делать с лишними
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",   # игнорируем ключи, которых нет в этом классе
    )

settings = Settings()
