"""
Runs inference with the loaded pipeline. Isolation Forest is the primary detector
(spec requirement); LOF is used only as a secondary consensus signal that feeds
into the confidence score — it never overrides is_anomaly on its own.

Severity bands (see app/core/config.py for the rationale):
  CRITICAL : score <= threshold_critical         (calibrated p1 of training scores)
  HIGH     : threshold_critical < score <= threshold_high_risk   (calibrated p5)
  MEDIUM   : threshold_high_risk < score <= threshold_high_risk + margin, AND flagged anomaly
  LOW      : any other row flagged as an anomaly (predict() == -1) but with a
             score above the MEDIUM band
Rows where predict() == 1 (normal) are not anomalies and get no severity.
"""
from dataclasses import dataclass

import pandas as pd

from app.core.config import settings
from app.ml.model_loader import get_pipeline
from app.ml.preprocessing import build_feature_matrix


@dataclass
class DetectionResult:
    is_anomaly: bool
    anomaly_score: float
    algorithm: str
    severity: str | None
    confidence: float


def _classify_severity(score: float, threshold_high_risk: float, threshold_critical: float) -> str:
    medium_bound = threshold_high_risk + settings.SEVERITY_MEDIUM_BAND_MARGIN
    if score <= threshold_critical:
        return "CRITICAL"
    if score <= threshold_high_risk:
        return "HIGH"
    if score <= medium_bound:
        return "MEDIUM"
    return "LOW"


def detect_batch(df: pd.DataFrame) -> list[DetectionResult]:
    """df: one or more raw-ish Sophos rows (Title Case columns). Returns one result per row, in order."""
    pipeline = get_pipeline()
    primary = pipeline["primary_model"]
    secondary = pipeline["secondary_model"]
    threshold_high_risk = float(pipeline["threshold_high_risk"])
    threshold_critical = float(pipeline["threshold_critical"])

    X = build_feature_matrix(df, pipeline)

    primary_pred = primary.predict(X.values)          # -1 anomaly, 1 normal
    primary_scores = primary.score_samples(X.values)   # lower = more anomalous
    secondary_scores = secondary.score_samples(X.values)

    results: list[DetectionResult] = []
    for i in range(len(X)):
        is_anom = bool(primary_pred[i] == -1)
        score = float(primary_scores[i])

        if is_anom:
            severity = _classify_severity(score, threshold_high_risk, threshold_critical)
            # Confidence: agreement between the two models, both expressed as
            # a 0-1 distance below the high-risk boundary, averaged and clipped.
            primary_strength = min(max((threshold_high_risk - score) / abs(threshold_high_risk) if threshold_high_risk else 0, 0), 1)
            secondary_strength = min(max((threshold_high_risk - float(secondary_scores[i])) / abs(threshold_high_risk) if threshold_high_risk else 0, 0), 1)
            confidence = round(min(0.5 + 0.5 * ((primary_strength + secondary_strength) / 2), 0.99), 4)
        else:
            severity = None
            confidence = round(max(1 - abs(score - threshold_high_risk), 0.5), 4)

        results.append(DetectionResult(
            is_anomaly=is_anom,
            anomaly_score=score,
            algorithm="IsolationForest+LOF",
            severity=severity,
            confidence=confidence,
        ))
    return results


def detect_single(record: dict) -> DetectionResult:
    df = pd.DataFrame([record])
    return detect_batch(df)[0]
