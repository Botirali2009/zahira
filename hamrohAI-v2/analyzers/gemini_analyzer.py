"""Gemini-based triage analyzer — same slot as llm_analyzer.py (Claude), an
alternative back end for people without Anthropic API credit.

Registered under the same name ("llm") and priority as llm_analyzer.py, so it
is a drop-in swap: app.py's ANALYZER_MODULES picks exactly one of the two
files based on Config.LLM_PROVIDER, never both, so there's no double
registration and no import-order coupling between them.

Deliberately self-contained (doesn't import from llm_analyzer.py) — importing
that module would execute its own `@analyzer(...)` registration as a side
effect, re-adding the Claude path even when it's not the selected provider.
A little duplication (response parsing/coercion) is the trade-off for that
isolation; if the shared shape ever needs to change, update both files.

Same contract as every analyzer: never raises, returns None on anything it
can't confidently answer (missing key, timeout, malformed reply, disabled
flag) so the pipeline always has the rule analyzer to fall back on.
"""

import json
from typing import List, Literal, TypedDict

from config import Config, features
from core import prompts
from analyzers.base import GREEN, RED, YELLOW, AnalyzerResult, analyzer

VALID_LEVELS = (GREEN, YELLOW, RED)
DEFAULT_SCORE = {GREEN: 15, YELLOW: 55, RED: 90}
MAX_TOKENS = 2048


class TriageSchema(TypedDict):
    risk_level: Literal["green", "yellow", "red"]
    risk_score: int
    danger_signals: List[str]
    reasoning: str
    recommended_action: str


def _log_exception(message, *args):
    from flask import current_app
    try:
        current_app.logger.exception(message, *args)
    except RuntimeError:
        pass


def _client():
    """Build a client, or None when the SDK or the key is unavailable."""
    api_key = Config.GEMINI_API_KEY
    if not api_key:
        return None
    try:
        from google import genai
    except ImportError:
        return None
    return genai.Client(api_key=api_key)


def _build_case(context):
    """The per-request user turn: this patient, this day, this answer, plus
    whatever guideline excerpts look relevant to it."""
    from core.retrieval import context_for

    retrieved = context_for(
        context.get("text") or "", limit=Config.TRIAGE_RETRIEVAL_LIMIT)
    return prompts.render(
        Config.TRIAGE_CASE_PROMPT,
        diagnosis=context.get("diagnosis") or "nomaʼlum",
        day_number=context.get("day_number") or "?",
        question_key=context.get("question_key") or "umumiy",
        question_text=context.get("question_text") or "-",
        answer_text=context.get("text") or "",
        retrieved_context=retrieved,
    )


def _system_prompt():
    """Persona (voice/boundaries) ahead of the clinical rules — two files so
    either can be edited or swapped independently."""
    return prompts.load(Config.PERSONA_PROMPT) + "\n\n" + prompts.load(Config.TRIAGE_PROMPT)


def _coerce_score(raw, level):
    try:
        score = int(raw)
    except (TypeError, ValueError):
        return DEFAULT_SCORE[level]
    return max(0, min(100, score))


def _coerce_signals(raw):
    if not isinstance(raw, list):
        return []
    return [str(s).strip() for s in raw if str(s).strip()]


def parse_response(text):
    """Turn raw model output into an AnalyzerResult, or None if unusable."""
    if not text:
        return None
    try:
        payload = json.loads(text)
    except (TypeError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None

    level = str(payload.get("risk_level", "")).strip().lower()
    if level not in VALID_LEVELS:
        return None

    action = str(payload.get("recommended_action") or "").strip() or None
    return AnalyzerResult(
        risk_level=level,
        risk_score=_coerce_score(payload.get("risk_score"), level),
        danger_signals=_coerce_signals(payload.get("danger_signals")),
        reasoning=str(payload.get("reasoning") or "").strip(),
        recommended_action=action,
    )


@analyzer("llm", priority=20)
def analyze(context):
    if not features.enabled("llm_analyzer"):
        return None
    if not (context.get("text") or "").strip():
        return None

    client = _client()
    if client is None:
        return None

    try:
        from google.genai import types

        response = client.models.generate_content(
            model=Config.GEMINI_MODEL,
            contents=_build_case(context),
            config=types.GenerateContentConfig(
                system_instruction=_system_prompt(),
                response_mime_type="application/json",
                response_schema=TriageSchema,
                max_output_tokens=MAX_TOKENS,
                temperature=0,
                http_options=types.HttpOptions(
                    timeout=int(Config.LLM_TIMEOUT_SECONDS * 1000),  # ms
                ),
            ),
        )
    except Exception:
        # Timeout, network failure, bad key, rate limit — all the same to us.
        _log_exception("gemini analyzer call failed")
        return None

    try:
        return parse_response(response.text)
    except Exception:
        _log_exception("gemini analyzer response parsing failed")
        return None
