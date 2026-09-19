"""Environment loading helpers for the example project."""

from __future__ import annotations

import os
from pathlib import Path

from config import REPO_ROOT


def load_openrouter_key() -> str:
    key = os.environ.get("OPENROUTER_API_KEY")
    if key:
        return key

    for env_path in (REPO_ROOT / ".env", REPO_ROOT.parent / ".env"):
        if not env_path.exists():
            continue
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, value = line.split("=", 1)
            if name.strip() == "OPENROUTER_API_KEY":
                key = value.strip().strip('"').strip("'")
                break
        if key:
            break

    if not key:
        raise RuntimeError(
            "OPENROUTER_API_KEY is missing. Put it in the repository-level .env "
            "file or export it in the environment."
        )
    return key
