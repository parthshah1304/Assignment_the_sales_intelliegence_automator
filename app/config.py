import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    APP_NAME: str = "Sales Intelligence Automator"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Database
    DATABASE_PATH: str = "leads.db"
    
    # LLM Settings
    LLM_PROVIDER: str = "gemini"  # "gemini", "openai", "groq", or "mock"
    GEMINI_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    
    GEMINI_MODEL: str = "gemini-2.5-flash"
    OPENAI_MODEL: str = "gpt-4o-mini"
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    
    # Scraper Settings
    MAX_CRAWL_PAGES_PER_LEAD: int = 3
    REQUEST_TIMEOUT_SECONDS: int = 12
    MAX_TEXT_LENGTH_FOR_LLM: int = 12000

settings = Settings()
