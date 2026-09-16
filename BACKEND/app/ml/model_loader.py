"""
Loads production_network_anomaly_pipeline.joblib ONCE at process startup and keeps it
in memory. Never re-train inside a request handler.

The .joblib is a dict with:
  primary_model        -> IsolationForest (real-time inline scoring)
  secondary_model      -> LocalOutlierFactor (novelty=True, consensus check)
  scaler               -> RobustScaler fitted on the full 32-column engineered feature set
  selected_features     -> the 15 features actually fed to the models
  threshold_high_risk   -> calibrated p5 boundary on Isolation Forest score_samples()
  threshold_critical    -> calibrated p1 boundary on Isolation Forest score_samples()
"""
import logging
import threading
from pathlib import Path
from typing import Optional

import joblib

from app.core.config import settings

logger = logging.getLogger("app.ml.model_loader")

_lock = threading.Lock()
_pipeline: Optional[dict] = None


class ModelNotLoadedError(RuntimeError):
    pass


def load_pipeline() -> dict:
    """Idempotent — safe to call multiple times, only loads from disk once."""
    global _pipeline
    if _pipeline is not None:
        return _pipeline

    with _lock:
        if _pipeline is not None:
            return _pipeline

        path = Path(settings.ML_PIPELINE_PATH)
        if not path.is_absolute():
            # resolve relative to BACKEND/ root regardless of current working directory
            path = Path(__file__).resolve().parents[2] / settings.ML_PIPELINE_PATH

        if not path.exists():
            raise ModelNotLoadedError(f"ML pipeline file not found at {path}")

        try:
            pipeline = joblib.load(path)
        except Exception as exc:
            logger.error("Failed to load ML pipeline: %s", exc)
            raise ModelNotLoadedError(str(exc)) from exc

        required_keys = {
            "primary_model", "secondary_model", "scaler",
            "selected_features", "threshold_high_risk", "threshold_critical",
        }
        missing = required_keys - pipeline.keys()
        if missing:
            raise ModelNotLoadedError(f"Pipeline artifact missing keys: {missing}")

        _pipeline = pipeline
        logger.info(
            "ML pipeline loaded: %d selected features, high_risk=%.4f, critical=%.4f",
            len(pipeline["selected_features"]),
            pipeline["threshold_high_risk"],
            pipeline["threshold_critical"],
        )
        return _pipeline


def get_pipeline() -> dict:
    if _pipeline is None:
        return load_pipeline()
    return _pipeline


def is_loaded() -> bool:
    return _pipeline is not None
