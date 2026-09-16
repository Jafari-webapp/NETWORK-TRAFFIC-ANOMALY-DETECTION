import re

from sqlalchemy.orm import Session

from app.models.anomaly_result import AnomalyResult
from app.models.firewall_log import FirewallLog
from app.services import dashboard_service, llm_service

IP_PATTERN = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")


def _build_context(db: Session, user_message: str) -> str:
    summary = dashboard_service.get_summary(db)
    recent = dashboard_service.get_recent_anomalies(db, limit=10, hours=None)

    lines = [
        "=== Live Network Snapshot (from PostgreSQL, already computed — do not invent numbers beyond these) ===",
        f"Total logs: {summary['total_logs']}",
        f"Total anomalies: {summary['total_anomalies']} "
        f"(LOW={summary['low_severity']}, MEDIUM={summary['medium_severity']}, "
        f"HIGH={summary['high_severity']}, CRITICAL={summary['critical_severity']})",
        "",
        "Most recent anomalies:",
    ]
    for a in recent[:10]:
        lines.append(
            f"- [{a['time']}] {a['src_ip']} -> {a['dst_ip']}:{a['dst_port']} "
            f"({a['protocol']}) severity={a['severity']} score={a['anomaly_score']:.4f}"
        )

    # If the engineer mentioned a specific IP, pull its anomaly history too.
    ips_mentioned = IP_PATTERN.findall(user_message)
    if ips_mentioned:
        lines.append("")
        lines.append("Anomaly history for IP(s) mentioned in the question:")
        for ip in ips_mentioned[:3]:
            rows = (
                db.query(AnomalyResult, FirewallLog)
                .join(FirewallLog, AnomalyResult.firewall_log_id == FirewallLog.id)
                .filter(
                    (FirewallLog.src_ip == ip) | (FirewallLog.dst_ip == ip),
                    AnomalyResult.is_anomaly.is_(True),
                )
                .order_by(AnomalyResult.detected_at.desc())
                .limit(10)
                .all()
            )
            if not rows:
                lines.append(f"- {ip}: no anomalies on record")
            else:
                for anomaly, log in rows:
                    lines.append(
                        f"- {ip} | {log.time} | {log.src_ip}->{log.dst_ip}:{log.dst_port} "
                        f"| severity={anomaly.severity} score={anomaly.anomaly_score:.4f}"
                    )

    return "\n".join(lines)


SYSTEM_PREAMBLE = """You are the AI Network Assistant inside SOPHOSMIXX, a network anomaly detection
dashboard for a Network Engineer. Answer questions about traffic, anomalies, threats, IPs, and
protocols using ONLY the live data snapshot given below plus general networking/security knowledge.
Never invent specific numbers, IPs, or events not present in the snapshot. If the data needed to
answer isn't in the snapshot, say so plainly and suggest how the engineer could find it (e.g. via
the Firewall Logs or Anomalies page). Keep answers concise and practical."""



def ask(db: Session, message: str, history: list[dict]) -> str:
    """
    AI Network Assistant.
    Only network-related questions are processed.
    Non-network questions are rejected before querying the database
    or calling Gemini.
    """

    network_keywords = [
        "network",
        "firewall",
        "sophos",
        "traffic",
        "anomaly",
        "anomalies",
        "ip",
        "source ip",
        "destination ip",
        "port",
        "protocol",
        "tcp",
        "udp",
        "icmp",
        "connection",
        "connections",
        "packet",
        "packets",
        "log",
        "logs",
        "firewall rule",
        "nat",
        "nat rule",
        "intrusion",
        "security event",
        "security",
        "attack",
        "threat",
        "malware",
        "dns",
        "http",
        "https",
        "ssh",
        "vpn",
        "bandwidth",
        "latency",
        "packet loss",
        "network performance",
        "network monitoring",
    ]

    normalized_message = message.lower().strip()

    is_network_question = any(
        keyword in normalized_message
        for keyword in network_keywords
    )

    if not is_network_question:
        return (
            "I’m a Network AI Assistant. I can only help with "
            "network-related questions such as firewall logs, traffic, "
            "IPs, ports, protocols, anomalies, and security events."
        )

    context = _build_context(db, message)

    full_message = (
        f"{SYSTEM_PREAMBLE}\n\n"
        f"{context}\n\n"
        f"=== Network Engineer's question ===\n"
        f"{message}"
    )

    return llm_service.chat(
        history=history,
        message=full_message
    )

