"""
Gemini explanation layer.

Gemini NEVER detects anomalies and NEVER produces or overrides
anomaly_score / is_anomaly / severity / confidence.

Those values come only from app.ml.anomaly_detector.

Gemini only explains an anomaly that the ML model has already flagged.

Uses the current google-genai SDK.
The API key lives only in backend .env.
"""

import json
import logging

from google import genai
from google.genai import types
from pydantic import ValidationError

from app.core.config import settings
from app.schemas.llm import GeminiStructuredOutput


logger = logging.getLogger("app.services.llm")

_client: genai.Client | None = None


class GeminiUnavailableError(RuntimeError):
    pass


def _get_client() -> genai.Client:
    """Create and reuse the Gemini API client."""

    global _client

    if not settings.GEMINI_API_KEY:
        raise GeminiUnavailableError(
            "GEMINI_API_KEY is not configured in backend .env"
        )

    if _client is None:
        _client = genai.Client(
            api_key=settings.GEMINI_API_KEY
        )

    return _client


def _build_prompt(context: dict) -> str:
    """Build the prompt used to explain an already-detected anomaly."""

    return f"""
You are a network security analyst assistant reviewing a Sophos firewall
anomaly that was already detected by an Isolation Forest / LOF machine
learning model.

Do NOT invent or change the anomaly score, severity, or confidence.
Those values are already final.

Explain the traffic in plain, practical language for a network engineer.

Detected anomaly context:

- Time: {context.get('time')}
- Source IP: {context.get('src_ip')}
- Destination IP: {context.get('dst_ip')}
- Source Port: {context.get('src_port')}
- Destination Port: {context.get('dst_port')}
- Protocol: {context.get('protocol')}
- Username: {context.get('username')}
- Firewall Rule: {context.get('firewall_rule')}
  ({context.get('firewall_rule_name')})
- NAT Rule: {context.get('nat_rule')}
  ({context.get('nat_rule_name')})
- In Interface: {context.get('in_interface')}
- Out Interface: {context.get('out_interface')}
- Rule Type: {context.get('rule_type')}
- Message: {context.get('message')}
- Log Occurrence: {context.get('log_occurrence')}

ML Detection Result (already final):

- Anomaly Score: {context.get('anomaly_score')}
- Severity: {context.get('severity')}
- Confidence: {context.get('confidence')}
- Algorithm: {context.get('algorithm')}

Return ONLY a JSON object with exactly these four keys.
Do not use markdown fences and do not add extra text.

{{
  "analysis": "what happened and why it is flagged as anomalous",
  "possible_cause": "most likely explanation",
  "recommendation": "concrete action for the network engineer",
  "risk_explanation": "what the real-world risk is if this is ignored"
}}
"""


def analyze_anomaly(context: dict) -> GeminiStructuredOutput:
    """
    Explain an anomaly that has already been detected by the ML pipeline.

    Gemini does not calculate or override anomaly_score, severity,
    confidence, or the anomaly decision.
    """

    client = _get_client()
    prompt = _build_prompt(context)

    try:
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                thinking_config=types.ThinkingConfig(
                    thinking_level="medium"
                ),
            ),
        )

    except Exception as exc:
        logger.error(
            "Gemini anomaly analysis failed: %s",
            exc,
            exc_info=True,
        )

        raise GeminiUnavailableError(
            f"Gemini API request failed: {exc}"
        ) from exc

    raw_text = (response.text or "").strip()

    try:
        data = json.loads(raw_text)

        return GeminiStructuredOutput(**data)

    except (json.JSONDecodeError, ValidationError) as exc:
        logger.error(
            "Gemini returned invalid JSON: %s | raw=%s",
            exc,
            raw_text[:500],
        )

        raise GeminiUnavailableError(
            "Gemini returned an invalid response format"
        ) from exc


def generate_text(prompt: str) -> str:
    """
    Plain free-text generation.

    Used by:
    - AI Assistant
    - Report Generator

    Gemini only generates/explains text.
    It does not directly access the database.
    """

    client = _get_client()

    try:
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(
                    thinking_level="medium"
                ),
            ),
        )

    except Exception as exc:
        error_text = str(exc)

        logger.error(
            "Gemini text generation failed: %s",
            exc,
            exc_info=True,
        )

        if (
            "429" in error_text
            or "RESOURCE_EXHAUSTED" in error_text
        ):
            return (
                "⚠️ The AI service has temporarily reached "
                "its usage limit. Please try again shortly."
            )

        return (
            "⚠️ Gemini is temporarily unavailable. "
            "Please try again shortly."
        )

    result = (response.text or "").strip()

    if not result:
        return (
            "⚠️ Gemini did not return a response. "
            "Please try again shortly."
        )

    return result


def chat(history: list[dict], message: str) -> str:
    """
    Chat with the AI Network Assistant.

    history format:
    [
        {"role": "user", "content": "..."},
        {"role": "assistant", "content": "..."}
    ]
    """

    client = _get_client()

    contents = []

    for turn in history:
        role = (
            "user"
            if turn["role"] == "user"
            else "model"
        )

        contents.append(
            types.Content(
                role=role,
                parts=[
                    types.Part(
                        text=turn["content"]
                    )
                ],
            )
        )

    contents.append(
        types.Content(
            role="user",
            parts=[
                types.Part(
                    text=message
                )
            ],
        )
    )

    try:
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(
                    thinking_level="medium"
                ),
            ),
        )

    except Exception as exc:
        error_text = str(exc)

        logger.error(
            "Gemini chat failed: %s",
            exc,
            exc_info=True,
        )

        if (
            "429" in error_text
            or "RESOURCE_EXHAUSTED" in error_text
        ):
            return (
                "⚠️ The AI Assistant has temporarily reached "
                "its usage limit. Please try again shortly."
            )

        return (
            "⚠️ The AI Assistant is temporarily unavailable. "
            "Please try again shortly."
        )

    result = (response.text or "").strip()

    if not result:
        return (
            "⚠️ The AI Assistant did not return a response. "
            "Please try again shortly."
        )

    return result
