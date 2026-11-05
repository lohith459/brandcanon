import os
from pydantic import BaseModel

class Settings(BaseModel):
    PROJECT_NAME: str = "BrandCanon"
    VERSION: str = "1.0.0"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./brandcanon.db")
    PORT: int = int(os.getenv("PORT", "8000"))
    HOST: str = os.getenv("HOST", "0.0.0.0")
    
    # Upload limits: 2MB max, restricted extensions
    MAX_UPLOAD_SIZE_BYTES: int = 2 * 1024 * 1024  # 2MB
    ALLOWED_EXTENSIONS: tuple[str, ...] = (".txt", ".docx", ".pdf", ".md", ".html")
    
    # Optional AI layer keys (offline mode if empty)
    GEMINI_API_KEY: str | None = os.getenv("GEMINI_API_KEY")
    ANTHROPIC_API_KEY: str | None = os.getenv("ANTHROPIC_API_KEY")
    
    # Rate limiting: max requests per minute per IP for sensitive endpoints
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
    
    # Confidential mode: suppresses all external AI calls
    CONFIDENTIAL_MODE_DEFAULT: bool = False

settings = Settings()
