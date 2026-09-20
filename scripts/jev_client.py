#!/usr/bin/env python3
"""Minimal provider-neutral client for TypeSafe Jev decisions."""

from __future__ import annotations

import argparse
import json
import os
import random
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


PROVIDERS = {
    "typesafe": {
        "url": "https://api.typesafe.ai/v1/systemone",
        "model": "jev-latest",
        "env": "TYPESAFE_API_KEY",
    },
    "openrouter": {
        "url": "https://openrouter.ai/api/alpha/decisions",
        "model": "~typesafe/jev-latest",
        "env": "OPENROUTER_API_KEY",
    },
}


@dataclass
class DecisionResponse:
    model: str
    answers: dict[str, dict[str, Any]]
    usage: dict[str, Any]
    provider: str
    request_id: str | None


class JevError(RuntimeError):
    """Raised when Jev cannot return a usable decision response."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        retry_after: float | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.retry_after = retry_after


def _provider_name(provider: str) -> str:
    if provider == "auto":
        return "typesafe" if os.getenv("TYPESAFE_API_KEY") else "openrouter"
    if provider not in PROVIDERS:
        raise ValueError(f"Unsupported provider: {provider}")
    return provider


def _headers(provider: str, api_key: str) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if provider == "openrouter":
        headers["HTTP-Referer"] = os.getenv(
            "OPENROUTER_HTTP_REFERER",
            "https://github.com/SunnyKikiHK/jev-replacement",
        )
        headers["X-Title"] = os.getenv("OPENROUTER_TITLE", "jev-replacement")
    return headers


def _parse_retry_after(value: str | None) -> float | None:
    if not value:
        return None
    value = value.strip()
    try:
        return max(0.0, float(value))
    except ValueError:
        pass

    try:
        retry_at = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if retry_at.tzinfo is None:
        retry_at = retry_at.replace(tzinfo=timezone.utc)
    return max(0.0, (retry_at - datetime.now(timezone.utc)).total_seconds())


def _post(
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    timeout: float,
) -> dict[str, Any]:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        retry_after = _parse_retry_after(exc.headers.get("Retry-After"))
        raise JevError(
            f"HTTP {exc.code}: {body}",
            status_code=exc.code,
            retry_after=retry_after,
        ) from exc
    except URLError as exc:
        raise JevError(f"Connection error: {exc.reason}") from exc


def decide(
    state: Any,
    questions: dict[str, Any],
    *,
    provider: str = "auto",
    model: str | None = None,
    api_key: str | None = None,
    timeout: float = 60.0,
    retries: int = 3,
    retry_base_seconds: float = 0.5,
) -> DecisionResponse:
    """Call Jev and return its typed answers.

    Retries are limited to overload, rate-limit, and server errors. Invalid
    requests and authentication failures fail immediately.
    """

    provider_name = _provider_name(provider)
    config = PROVIDERS[provider_name]
    key = api_key or os.getenv(config["env"])
    if not key:
        raise JevError(
            f"{config['env']} is required for the {provider_name} provider."
        )

    payload = {
        "model": model or config["model"],
        "state": state,
        "questions": questions,
    }

    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            raw = _post(
                str(config["url"]),
                payload,
                _headers(provider_name, key),
                timeout,
            )
            answers = raw.get("answers")
            if not isinstance(answers, dict):
                raise JevError("Response did not contain an answers object.")
            return DecisionResponse(
                model=str(raw.get("model", model or config["model"])),
                answers=answers,
                usage=raw.get("usage") or {},
                provider=str(raw.get("provider", provider_name)),
                request_id=raw.get("id"),
            )
        except JevError as exc:
            last_error = exc
            message = str(exc)
            retryable = (
                exc.status_code in {429, 500, 502, 503, 504, 529}
                or (
                    exc.status_code is None
                    and message.startswith("Connection error:")
                )
            )
            if not retryable or attempt >= retries:
                raise
            if exc.retry_after is not None:
                delay = exc.retry_after
            else:
                delay = retry_base_seconds * (2**attempt)
                delay += random.uniform(0, retry_base_seconds)
            time.sleep(delay)

    raise JevError(str(last_error or "Unknown Jev error"))


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Input JSON must be an object.")
    return value


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Call Jev with a state and questions JSON file."
    )
    parser.add_argument("request", type=Path, help="JSON containing state and questions.")
    parser.add_argument(
        "--provider",
        choices=["auto", "typesafe", "openrouter"],
        default="auto",
    )
    parser.add_argument("--model")
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--retries", type=int, default=3)
    args = parser.parse_args()

    request = _load_json(args.request)
    response = decide(
        request["state"],
        request["questions"],
        provider=args.provider,
        model=args.model,
        timeout=args.timeout,
        retries=args.retries,
    )
    print(
        json.dumps(
            {
                "model": response.model,
                "answers": response.answers,
                "usage": response.usage,
                "provider": response.provider,
                "request_id": response.request_id,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
