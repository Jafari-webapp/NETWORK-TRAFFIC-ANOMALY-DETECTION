```python
import logging

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.database.connection import engine, test_connection
from app.database.base import Base
import app.models
from sqlalchemy import text
from app.ml.model_loader import ModelNotLoadedError, load_pipeline
from app.routers import anomalies, assistant, auth, dashboard, firewall_logs, llm, reports
from app.services import cleanup_service

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger("app.main")

app = FastAPI(
    title="Network Traffic Anomaly Detection API",
    description="Sophos Firewall Logs -> PostgreSQL -> Isolation Forest -> Gemini AI explanation -> Dashboard",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # Never leak a Python traceback to the client.
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal error occurred. Please try again or contact support."},
    )


@app.on_event("startup")
def on_startup():
    db_ok = test_connection()
    if not db_ok:
        logger.error("Database is unreachable at startup - check DATABASE_URL in .env")

    if db_ok:
        try:
            with engine.begin() as conn:
                conn.execute(text("CREATE SCHEMA IF NOT EXISTS network"))

            Base.metadata.create_all(bind=engine)

            logger.info("Database schema and tables initialized successfully.")

            cleanup_service.ensure_schema_upgrades()
        except Exception:
            logger.exception("Database initialization/schema upgrade failed — continuing anyway.")

    try:
        load_pipeline()
        logger.info("ML pipeline ready.")
    except ModelNotLoadedError as exc:
        logger.error("ML pipeline failed to load at startup: %s", exc)

    if not settings.GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY is empty - AI analysis endpoints will fail until it's set in .env")

    logger.info("CORS allowed origins: %s", settings.cors_origins)
    logger.info(
        "Reminder: changes to .env only take effect on the NEXT restart of this process "
        "(pydantic-settings reads .env once, at startup)."
    )

    if db_ok:
        import asyncio

        asyncio.create_task(cleanup_service.cleanup_loop())
        logger.info(
            "Retention cleanup scheduled: firewall logs/anomalies older than %dd, "
            "upload history older than %dd (runs hourly).",
            cleanup_service.FIREWALL_LOG_RETENTION_DAYS,
            cleanup_service.UPLOAD_HISTORY_RETENTION_DAYS,
        )


@app.get("/", tags=["health"])
def root():
    return {"status": "ok", "service": "network-anomaly-detection-api"}


@app.get("/health", tags=["health"])
def health():
    return {"database": test_connection()}


app.include_router(auth.router)
app.include_router(firewall_logs.router)
app.include_router(anomalies.router)
app.include_router(llm.router)
app.include_router(dashboard.router)
app.include_router(assistant.router)
app.include_router(reports.router)
```
