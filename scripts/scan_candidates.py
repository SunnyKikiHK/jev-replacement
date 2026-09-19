#!/usr/bin/env python3
"""Find likely Jev replacement candidates in an existing project."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path


IGNORED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "node_modules",
    "vendor",
    "dist",
    "build",
    "target",
    "__pycache__",
    ".next",
    ".idea",
}

ALLOWED_SUFFIXES = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".java",
    ".kt",
    ".go",
    ".rb",
    ".php",
    ".cs",
    ".rs",
    ".md",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
}

PATTERNS: list[tuple[str, str, re.Pattern[str]]] = [
    (
        "llm",
        "LLM call or prompt-and-parse path",
        re.compile(
            r"\b(chat\.completions|chat_completions|responses\.create|"
            r"generate_content|ollama|litellm|anthropic|openai)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "classical-ml",
        "Classical classifier or scoring pipeline",
        re.compile(
            r"\b(sklearn|LogisticRegression|RandomForest|SVM|XGBoost|"
            r"lightgbm|predict_proba|joblib\.load)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "neural-classifier",
        "Neural or transformer classifier",
        re.compile(
            r"\b(torch|tensorflow|transformers|AutoModelForSequenceClassification|"
            r"sentence_transformers|SentenceTransformer|bert|roberta|distilbert)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "semantic-decision",
        "Function name suggests a semantic decision",
        re.compile(
            r"\b(def|function|async def|public|private|protected)\s+"
            r"(?:[A-Za-z0-9]+_)*(classif(?:y|ication|ier)?|route|score|rank|"
            r"verify|moderat(?:e|ion)|detect|select|judge)"
            r"(?:_[A-Za-z0-9]+)*\s*\(",
            re.IGNORECASE,
        ),
    ),
    (
        "heuristic",
        "Keyword or threshold-heavy decision logic",
        re.compile(
            r"\b(if|elif|else if)\b.*"
            r"(contains|includes|match|regex|keyword|"
            r"label|category|intent|topic)",
            re.IGNORECASE,
        ),
    ),
]


@dataclass
class Candidate:
    file: str
    line: int
    category: str
    reason: str
    snippet: str


def iter_files(root: Path, max_file_bytes: int):
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in IGNORED_DIRS for part in path.parts):
            continue
        if path.suffix.lower() not in ALLOWED_SUFFIXES:
            continue
        try:
            if path.stat().st_size > max_file_bytes:
                continue
        except OSError:
            continue
        yield path


def scan(root: Path, max_file_bytes: int) -> list[Candidate]:
    candidates: list[Candidate] = []
    for path in iter_files(root, max_file_bytes):
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for line_number, line in enumerate(lines, start=1):
            if len(line) > 1000:
                continue
            for category, reason, pattern in PATTERNS:
                if pattern.search(line):
                    candidates.append(
                        Candidate(
                            file=str(path.relative_to(root)),
                            line=line_number,
                            category=category,
                            reason=reason,
                            snippet=line.strip()[:240],
                        )
                    )
    return candidates


def print_markdown(candidates: list[Candidate]) -> None:
    print("# Jev Replacement Candidates")
    print()
    print(f"Found {len(candidates)} possible matches. Verify each manually.")
    print()
    print("| File | Line | Category | Reason | Snippet |")
    print("| --- | ---: | --- | --- | --- |")
    for item in candidates:
        snippet = item.snippet.replace("|", "\\|")
        print(
            f"| `{item.file}` | {item.line} | `{item.category}` | "
            f"{item.reason} | `{snippet}` |"
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("project", type=Path)
    parser.add_argument("--format", choices=["json", "markdown"], default="markdown")
    parser.add_argument("--max-file-bytes", type=int, default=2_000_000)
    args = parser.parse_args()

    root = args.project.resolve()
    if not root.exists():
        raise SystemExit(f"Project path does not exist: {root}")
    if not root.is_dir():
        raise SystemExit(f"Project path is not a directory: {root}")

    candidates = scan(root, args.max_file_bytes)
    if args.format == "json":
        print(json.dumps([asdict(item) for item in candidates], indent=2))
    else:
        print_markdown(candidates)


if __name__ == "__main__":
    main()
