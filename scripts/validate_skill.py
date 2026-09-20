#!/usr/bin/env python3
"""Validate the repository-owned Codex skill without third-party packages."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
VERSION_RE = re.compile(
    r'(?m)^metadata:\s*\n(?:[ \t]+[^\n]*\n)*?[ \t]+version:\s*["\']?'
    r"(\d+\.\d+\.\d+)"
)
IGNORED_ASCII_DIRS = {".git", ".validation-deps", "__pycache__"}
ASCII_SUFFIXES = {".md", ".py", ".json", ".jsonl", ".yaml", ".yml", ".toml"}


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        raise ValueError("SKILL.md must start with YAML frontmatter.")
    end = text.find("\n---\n", 4)
    if end == -1:
        raise ValueError("SKILL.md frontmatter is not closed.")
    raw = text[4:end]
    body = text[end + 5 :]
    fields: dict[str, str] = {}
    for line in raw.splitlines():
        if not line or line[0].isspace() or ":" not in line:
            continue
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip().strip('"').strip("'")
    return fields, body


def check_links(skill_root: Path, body: str, failures: list[str]) -> None:
    for target in LINK_RE.findall(body):
        target = target.split("#", 1)[0].strip()
        if not target or "://" in target or target.startswith("mailto:"):
            continue
        if not (skill_root / target).exists():
            failures.append(f"Broken local link in SKILL.md: {target}")


def check_ascii(skill_root: Path, failures: list[str]) -> None:
    for path in skill_root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in IGNORED_ASCII_DIRS for part in path.parts):
            continue
        if path.suffix.lower() not in ASCII_SUFFIXES:
            continue
        try:
            path.read_text(encoding="ascii")
        except UnicodeDecodeError:
            failures.append(f"Non-ASCII content: {path.relative_to(skill_root)}")


def validate(skill_root: Path) -> list[str]:
    failures: list[str] = []
    skill_file = skill_root / "SKILL.md"
    if not skill_file.exists():
        return ["Missing SKILL.md"]

    try:
        fields, body = parse_frontmatter(skill_file.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        return [str(exc)]

    name = fields.get("name", "")
    description = fields.get("description", "")
    license_name = fields.get("license", "")

    if not name or not NAME_RE.fullmatch(name):
        failures.append("Frontmatter name must be lowercase hyphen-case.")
    elif name != skill_root.name:
        failures.append("Frontmatter name must match the skill folder name.")
    if not description:
        failures.append("Frontmatter description is required.")
    elif len(description) > 1024:
        failures.append("Frontmatter description exceeds 1024 characters.")
    if not license_name:
        failures.append("Frontmatter license is required.")
    if not VERSION_RE.search(skill_file.read_text(encoding="utf-8")):
        failures.append("Frontmatter metadata.version must be semantic versioning.")
    if "TODO" in body:
        failures.append("SKILL.md contains an unfinished TODO marker.")

    if not (skill_root / "agents" / "openai.yaml").exists():
        failures.append("Missing agents/openai.yaml.")

    check_links(skill_root, body, failures)
    check_ascii(skill_root, failures)
    return failures


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("skill_root", nargs="?", type=Path, default=Path("."))
    args = parser.parse_args()

    root = args.skill_root.resolve()
    if not root.is_dir():
        raise SystemExit(f"Skill path is not a directory: {root}")

    failures = validate(root)
    if failures:
        for failure in failures:
            print(f"ERROR: {failure}")
        raise SystemExit(1)
    print(f"Skill is valid: {root.name}")


if __name__ == "__main__":
    main()
