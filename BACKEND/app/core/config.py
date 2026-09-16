"""
Central application configuration.
Reads everything from environment variables / .env — nothing sensitive is hardcoded.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    DATABASE_URL: str

    # Gemini
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.6-flash"

    # Auth
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 480

    # CORS — comma-separated list supported (e.g. dev + LAN IP + deployed domain),
    # so the frontend still works if it's opened from more than one origin.
    FRONTEND_URL: str = "http://localhost:5176"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip().rstrip("/") for o in self.FRONTEND_URL.split(",") if o.strip()]

    # ML
    ML_PIPELINE_PATH: str = "models/production_network_anomaly_pipeline.joblib"

    # Upload
    MAX_UPLOAD_SIZE_MB: int = 20

    # Severity bands.
    # CRITICAL / HIGH thresholds are read from the trained pipeline itself
    # (production_network_anomaly_pipeline.joblib -> threshold_critical / threshold_high_risk),
    # because they were calibrated against your real score distribution during training.
    # MEDIUM is defined as a configurable margin above the HIGH threshold, for anomalies
    # (predict() == -1) that aren't severe enough to hit HIGH. Everything else predicted
    # as an anomaly falls to LOW. Adjust this margin after you evaluate real alert volume.
    SEVERITY_MEDIUM_BAND_MARGIN: float = 0.05


settings = Settings()
