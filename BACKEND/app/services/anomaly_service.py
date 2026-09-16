import logging

import pandas as pd
from sqlalchemy.orm import Session

from app.core.config import settings
from app.ml.anomaly_detector import DetectionResult, detect_batch
from app.models.anomaly_result import AnomalyResult
from app.models.firewall_log import FirewallLog
from app.models.llm_analysis import LLMAnalysis
from app.services import llm_service

logger = logging.getLogger("app.services.anomaly")

# Maps FirewallLog ORM attribute names -> the Title Case column names the ML
# pipeline was trained on, so a DB row can be re-fed through the same code path
# used for freshly uploaded files.
_ORM_TO_TITLE = {
    "time": "Time", "log_comp": "Log comp", "log_subtype": "Log subtype",
    "username": "Username", "firewall_rule": "Firewall rule",
    "firewall_rule_name": "Firewall rule name", "nat_rule": "NAT rule",
    "nat_rule_name": "NAT rule name", "in_interface": "In interface",
    "out_interface": "Out interface", "src_ip": "Src IP", "dst_ip": "Dst IP",
    "src_port": "Src port", "dst_port": "Dst port", "protocol": "Protocol",
    "rule_type": "Rule type", "live_pcap": "Live PCAP", "message": "Message",
    "log_occurrence": "Log occurrence",
}


def _log_to_row(log: FirewallLog) -> dict:
    return {title: getattr(log, attr) for attr, title in _ORM_TO_TITLE.items()}


def run_detection_for_log(db: Session, log: FirewallLog) -> AnomalyResult:
    df = pd.DataFrame([_log_to_row(log)])
    result: DetectionResult = detect_batch(df)[0]

    existing = db.query(AnomalyResult).filter_by(firewall_log_id=log.id).one_or_none()
    if existing:
        existing.is_anomaly = result.is_anomaly
        existing.anomaly_score = result.anomaly_score
        existing.algorithm = result.algorithm
        existing.severity = result.severity
        existing.confidence = result.confidence
        anomaly = existing
    else:
        anomaly = AnomalyResult(
            firewall_log_id=log.id,
            is_anomaly=result.is_anomaly,
            anomaly_score=result.anomaly_score,
            algorithm=result.algorithm,
            severity=result.severity,
            confidence=result.confidence,
        )
        db.add(anomaly)

    db.commit()
    db.refresh(anomaly)
    return anomaly


def run_detection_for_logs(db: Session, logs: list[FirewallLog]) -> list[AnomalyResult]:
    """Batch version — one model call for many rows, then bulk-save results."""
    if not logs:
        return []

    df = pd.DataFrame([_log_to_row(log) for log in logs])
    detection_results = detect_batch(df)

    saved: list[AnomalyResult] = []
    for log, result in zip(logs, detection_results):
        existing = db.query(AnomalyResult).filter_by(firewall_log_id=log.id).one_or_none()
        if existing:
            existing.is_anomaly = result.is_anomaly
            existing.anomaly_score = result.anomaly_score
            existing.algorithm = result.algorithm
            existing.severity = result.severity
            existing.confidence = result.confidence
            saved.append(existing)
        else:
            anomaly = AnomalyResult(
                firewall_log_id=log.id,
                is_anomaly=result.is_anomaly,
                anomaly_score=result.anomaly_score,
                algorithm=result.algorithm,
                severity=result.severity,
                confidence=result.confidence,
            )
            db.add(anomaly)
            saved.append(anomaly)

    db.commit()
    for a in saved:
        db.refresh(a)
    return saved


def analyze_with_gemini(db: Session, anomaly: AnomalyResult) -> LLMAnalysis | None:
    """Only ever called for is_anomaly == True rows (spec: never call Gemini for normal records)."""
    if not anomaly.is_anomaly:
        return None

    log = anomaly.firewall_log
    context = {
        "time": str(log.time), "src_ip": log.src_ip, "dst_ip": log.dst_ip,
        "src_port": log.src_port, "dst_port": log.dst_port, "protocol": log.protocol,
        "username": log.username, "firewall_rule": log.firewall_rule,
        "firewall_rule_name": log.firewall_rule_name, "nat_rule": log.nat_rule,
        "nat_rule_name": log.nat_rule_name, "in_interface": log.in_interface,
        "out_interface": log.out_interface, "rule_type": log.rule_type,
        "message": log.message, "log_occurrence": log.log_occurrence,
        "anomaly_score": anomaly.anomaly_score, "severity": anomaly.severity,
        "confidence": anomaly.confidence, "algorithm": anomaly.algorithm,
    }

    structured = llm_service.analyze_anomaly(context)  # raises GeminiUnavailableError on failure

    existing = db.query(LLMAnalysis).filter_by(anomaly_id=anomaly.id).one_or_none()
    if existing:
        existing.analysis = structured.analysis
        existing.possible_cause = structured.possible_cause
        existing.recommendation = structured.recommendation
        existing.risk_explanation = structured.risk_explanation
        record = existing
    else:
        record = LLMAnalysis(
            anomaly_id=anomaly.id,
            model_name=settings.GEMINI_MODEL,
            provider="Google Gemini",
            analysis=structured.analysis,
            possible_cause=structured.possible_cause,
            recommendation=structured.recommendation,
            risk_explanation=structured.risk_explanation,
        )
        db.add(record)

    db.commit()
    db.refresh(record)
    return record
