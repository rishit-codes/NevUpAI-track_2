from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Default URL for docker-compose; can be overridden via .env
    DATABASE_URL: str = "postgresql+asyncpg://neondb_owner:npg_6ypBXh7mQIUa@ep-summer-union-anewmh07.c-6.us-east-1.aws.neon.tech/neondb?ssl=require"
    JWT_SECRET: str = "97791d4db2aa5f689c3cc39356ce35762f0a73aa70923039d8ef72a2840a1b02"
    JWT_ALGORITHM: str = "HS256"
    OPENAI_API_KEY: str = ""

    class Config:
        env_file = ".env"

settings = Settings()
