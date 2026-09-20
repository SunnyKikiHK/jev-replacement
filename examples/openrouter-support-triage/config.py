"""Shared configuration for the support-triage comparison."""

from __future__ import annotations

import os
from pathlib import Path


EXAMPLE_DIR = Path(__file__).resolve().parent
REPO_ROOT = EXAMPLE_DIR.parents[1]
DATASET_PATH = EXAMPLE_DIR / "dataset.jsonl"

LLM_MODEL = "meta-llama/llama-3.3-70b-instruct"
JE_V_MODEL = os.environ.get("JE_V_MODEL", "typesafe/jev-1.13")

CATEGORIES = {
    "account": "Login, profile, security, permissions, or account access.",
    "billing": "Charges, invoices, refunds, plans, or subscriptions.",
    "bug": "A product defect, crash, malfunction, or incorrect behavior.",
    "feature_request": "A request for a new capability or product enhancement.",
}

SYSTEM_PROMPT = """You classify customer-support messages.

Return exactly one label from this set:
account, billing, bug, feature_request

Return JSON only in this form:
{"label":"one_of_the_labels"}
"""

JE_V_INSTRUCTIONS = """What is the primary support intent in `message`?

Classify the request that the user wants the support team to act on, not merely
the product area mentioned in the message."""

JE_V_CRITERIA = {
    "account": (
        "The primary request concerns login, profile details, security, "
        "permissions, suspension, or account access."
    ),
    "billing": (
        "The primary request concerns charges, invoices, refunds, plan changes, "
        "subscriptions, or payment status."
    ),
    "bug": (
        "The primary request reports a product defect, crash, malfunction, or "
        "incorrect behavior that should be fixed."
    ),
    "feature_request": (
        "The primary request asks for a new capability, integration, option, or "
        "product enhancement."
    ),
}
