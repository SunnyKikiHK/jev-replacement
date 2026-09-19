"""Baseline support classifier using an OpenRouter chat model."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from config import LLM_MODEL, SYSTEM_PROMPT
from env import load_openrouter_key


OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"
VALID_LABELS = {"account", "billing", "bug", "feature_request"}


@dataclass
class ClassificationResult:
    id: str
    text: str
    expected: str
    predicted: str | None
    confidence: float | None
    latency_ms: float
    input_tokens: int | None
    output_tokens: int | None
    cost_usd: float | None
    raw_response: str | None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _post_json(url: str, payload: dict[str, Any], key: str) -> dict[str, Any]:
    request = Request(
        url=url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/SunnyKikiHK/jev-replacement",
            "X-Title": "jev-replacement-skill-test",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenRouter HTTP {exc.code}: {body}") from exc
    except URLError as exc:
        raise RuntimeError(f"OpenRouter connection error: {exc.reason}") from exc


def _extract_label(content: str) -> str | None:
    text = content.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:].lstrip()
    try:
        parsed = json.loads(text)
        label = parsed.get("label")
    except json.JSONDecodeError:
        label = text.strip().strip('"').lower()

    if isinstance(label, str):
        label = label.strip().lower()
    return label if label in VALID_LABELS else None


def classify_llm(item: dict[str, str]) -> ClassificationResult:
    key = load_openrouter_key()
    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": item["text"]},
        ],
        "temperature": 0,
        "max_tokens": 32,
    }

    started = time.perf_counter()
    raw_content: str | None = None
    error: str | None = None
    predicted: str | None = None
    usage: dict[str, Any] = {}

    try:
        response = _post_json(OPENROUTER_CHAT_URL, payload, key)
        raw_content = response["choices"][0]["message"]["content"]
        predicted = _extract_label(raw_content)
        usage = response.get("usage") or {}
    except Exception as exc:  # Keep benchmark rows complete on provider failures.
        error = str(exc)

    latency_ms = (time.perf_counter() - started) * 1000
    return ClassificationResult(
        id=item["id"],
        text=item["text"],
        expected=item["label"],
        predicted=predicted,
        confidence=None,
        latency_ms=round(latency_ms, 2),
        input_tokens=usage.get("prompt_tokens"),
        output_tokens=usage.get("completion_tokens"),
        cost_usd=usage.get("cost"),
        raw_response=raw_content,
        error=error,
    )

