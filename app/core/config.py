from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Default URL for docker-compose; can be overridden via .env
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@db:5432/nevup"
    JWT_SECRET: str = "97791d4db2aa5f689c3cc39356ce35762f0a73aa70923039d8ef72a2840a1b02"
    JWT_ALGORITHM: str = "HS256"
    OPENAI_API_KEY: str = ""

    class Config:
        env_file = ".env"

settings = Settings()
