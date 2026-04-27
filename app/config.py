# app/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict  # ← Importa SettingsConfigDict
from typing import List, Optional
from functools import lru_cache


class Settings(BaseSettings):
    # 🔥 Config nueva para Pydantic v2
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        # ✅ Esto permite parsear listas desde el .env
        env_nested_delimiter="__",  # Opcional: para variables anidadas
    )
    
    # Database
    DB_NAME: str
    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str
    DB_PORT: str

    # JWT
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    # Cloudinary
    CLOUDINARY_CLOUD_NAME: str
    CLOUDINARY_API_KEY: str
    CLOUDINARY_API_SECRET: str

    # Stripe
    STRIPE_SECRET_KEY: str
    STRIPE_PUBLISHABLE_KEY: str
    STRIPE_WEBHOOK_SECRET: str

    # Firebase
    FIREBASE_CREDENTIALS_PATH: Optional[str] = None

    # App
    BACKEND_CORS_ORIGINS: List[str]  # ← Pydantic v2 parsea esto automáticamente
    ENVIRONMENT: str = "development"

    # Security
    MAX_LOGIN_ATTEMPTS: int = 3
    COMMISSION_PERCENTAGE: float = 10.00

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+psycopg2://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()