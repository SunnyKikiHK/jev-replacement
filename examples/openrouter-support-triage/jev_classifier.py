"""Jev replacement for the baseline support classifier."""

from __future__ import annotations

import sys
import time
from typing import Any

from config import JE_V_CRITERIA, JE_V_INSTRUCTIONS, JE_V_MODEL, REPO_ROOT
from env import load_openrouter_key
from llm_classifier import ClassificationResult

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.jev_client import decide  # noqa: E402


def classify_jev(item: dict[str, str]) -> ClassificationResult:
    """Classify one support message through OpenRouter's Jev Decisions API."""

    state = {"message": item["text"]}
    questions = {
        "intent": {
            "type": "choice",
            "instructions": JE_V_INSTRUCTIONS,
            "criteria": JE_V_CRITERIA,
        }
    }

    started = time.perf_counter()
    predicted: str | None = None
    confidence: float | None = None
    raw_response: str | None = None
    error: str | None = None
    usage: dict[str, Any] = {}

    try:
        response = decide(
            state,
            questions,
            provider="openrouter",
            model=JE_V_MODEL,
            api_key=load_openrouter_key(),
        )
        answer = response.answers.get("intent")
        if not isinstance(answer, dict):
            raise RuntimeError("Jev response did not contain the intent answer.")
        predicted = answer.get("choice")
        confidence = answer.get("confidence")
        raw_response = str(answer)
        usage = response.usage
        if predicted not in JE_V_CRITERIA:
            raise RuntimeError(f"Jev returned an invalid label: {predicted!r}")
    except Exception as exc:  # Keep the benchmark row complete.
        error = str(exc)

    latency_ms = (time.perf_counter() - started) * 1000
    return ClassificationResult(
        id=item["id"],
        text=item["text"],
        expected=item["label"],
        predicted=predicted,
        confidence=float(confidence) if confidence is not None else None,
        latency_ms=round(latency_ms, 2),
        input_tokens=usage.get("input_tokens"),
        output_tokens=usage.get("output_tokens"),
        cost_usd=usage.get("cost"),
        raw_response=raw_response,
        error=error,
    )
