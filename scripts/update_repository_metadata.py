#!/usr/bin/env python3
"""Dry-run or apply GitHub repository description and topics."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_METADATA = Path(".github/repository-metadata.json")
API_ROOT = "https://api.github.com"


def load_metadata(path: Path) -> dict[str, Any]:
    metadata = json.loads(path.read_text(encoding="utf-8"))
    description = metadata.get("description")
    topics = metadata.get("topics")
    if not isinstance(description, str) or not description.strip():
        raise ValueError("metadata.description must be a non-empty string.")
    if len(description) > 350:
        raise ValueError("GitHub repository descriptions are limited to 350 characters.")
    if not isinstance(topics, list) or not all(
        isinstance(topic, str) and topic for topic in topics
    ):
        raise ValueError("metadata.topics must be a list of non-empty strings.")
    return metadata


def build_requests(repo: str, metadata: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "method": "PATCH",
            "url": f"{API_ROOT}/repos/{repo}",
            "payload": {
                "description": metadata["description"],
                "homepage": metadata.get("homepage") or "",
            },
        },
        {
            "method": "PUT",
            "url": f"{API_ROOT}/repos/{repo}/topics",
            "payload": {"names": metadata["topics"]},
        },
    ]


def send(request: dict[str, Any], token: str) -> dict[str, Any]:
    body = json.dumps(request["payload"]).encode("utf-8")
    http_request = Request(
        request["url"],
        data=body,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "jev-replacement-metadata-updater",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        method=request["method"],
    )
    try:
        with urlopen(http_request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub HTTP {exc.code}: {body}") from exc
    except URLError as exc:
        raise RuntimeError(f"GitHub connection error: {exc.reason}") from exc


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repo",
        default=os.getenv("GITHUB_REPOSITORY", "SunnyKikiHK/jev-replacement"),
    )
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes. Without this flag, only print the requests.",
    )
    parser.add_argument("--token-env", default="GITHUB_TOKEN")
    args = parser.parse_args()

    metadata = load_metadata(args.metadata)
    requests = build_requests(args.repo, metadata)

    if not args.apply:
        print(json.dumps(requests, indent=2))
        return

    token = os.getenv(args.token_env)
    if not token:
        raise SystemExit(
            f"{args.token_env} is required with --apply. The token needs repository "
            "administration permission."
        )
    for request in requests:
        response = send(request, token)
        print(json.dumps(response, indent=2))


if __name__ == "__main__":
    main()

