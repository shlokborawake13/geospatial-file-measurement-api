from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Geospatial File Measurement API"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"

    # Service-role key gives the backend trusted access that bypasses RLS.
    # Optional so the test suite can run without a live Supabase project.
    # In production / development both values are required.
    SUPABASE_URL: Optional[str] = None
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None
    SUPABASE_STORAGE_BUCKET: str = "geospatial-files"

    MAX_UPLOAD_SIZE_MB: int = 50
    TEMP_DIR: str = "/tmp/geospatial-processing"

    CORS_ORIGINS: str = (
        "http://localhost:5173,http://127.0.0.1:5173,https://geospatial-file-measurement-api.vercel.app"
    )
    FRONTEND_URL: Optional[str] = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origins_list(self) -> List[str]:
        origins: set[str] = {
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "https://geospatial-file-measurement-api.vercel.app",
        }
        if self.CORS_ORIGINS:
            for o in self.CORS_ORIGINS.split(","):
                cleaned = o.strip().rstrip("/")
                if cleaned:
                    origins.add(cleaned)
        if self.FRONTEND_URL:
            for o in self.FRONTEND_URL.split(","):
                cleaned = o.strip().rstrip("/")
                if cleaned:
                    origins.add(cleaned)
        return sorted(origins)

    @property
    def max_upload_size_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024


settings = Settings()
