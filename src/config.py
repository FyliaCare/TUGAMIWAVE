from pydantic import BaseModel
import os

class Settings(BaseModel):
    COMPANY_NAME: str = os.getenv("COMPANY_NAME", "TUGAMIWAVE")
    BASE_CURRENCY: str = os.getenv("BASE_CURRENCY", "GHS")
    DB_URL: str = os.getenv("DB_URL", "sqlite:///tugamiwave.db")

def get_settings() -> Settings:
    return Settings()
