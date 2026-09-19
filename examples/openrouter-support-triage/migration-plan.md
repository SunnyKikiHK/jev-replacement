# Jev Migration Plan

## Candidate

Current implementation: `classify_llm` in `llm_classifier.py` sends one support
message to `meta-llama/llama-3.3-70b-instruct` through OpenRouter chat
completions and parses one of four labels from generated JSON.

Target behavior: preserve the four-label output contract while replacing the
LLM prompt-and-parse decision with one Jev `Choice` question.

Why Jev fits:

- the output is a bounded, non-overlapping set of four categories;
- the task is a fast semantic judgment over one message;
- repeated support triage makes latency and cost material;
- Jev returns typed probabilities and confidence without parsing prose.

Why Jev might fail:

- ambiguous messages can mention several product areas;
- account and bug behavior can overlap, as shown by the baseline failure on
  `account-2fa`;
- Jev can still choose the wrong label even though its output schema is safe.

## Baseline

Dataset: 20 labeled support messages, five per category.

Baseline metrics from `evaluation-llm.json`:

- accuracy: `0.95`;
- macro F1: `0.9495`;
- p50 latency: `606.34 ms`;
- p95 latency: `8844.79 ms`;
- mean cost: `$0.00001574` per request.

The only baseline error was `account-2fa`, predicted as `bug`.

## Design

Primitive: `choice`.

State:

```json
{"message": "<support message>"}
```

Question:

```json
{
  "intent": {
    "type": "choice",
    "instructions": "What is the primary support intent in `message`?",
    "criteria": {
      "account": "Login, profile, security, permissions, account access.",
      "billing": "Charges, invoices, refunds, plans, subscriptions.",
      "bug": "A product defect, crash, malfunction, or incorrect behavior.",
      "feature_request": "A request for a new capability or enhancement."
    }
  }
}
```

Confidence gate: auto-accept at confidence `>= 0.8` during evaluation. The
example does not yet route low-confidence answers to the LLM, so the raw Jev
accuracy remains visible.

Provider: OpenRouter Decisions API with `~typesafe/jev-latest`.

## Acceptance Gate

The replacement is successful when all of these hold:

- Jev accuracy is at least `0.90`;
- Jev macro F1 is at least `0.90`;
- Jev does not regress more than `0.05` absolute accuracy from the baseline;
- p50 latency is lower than the baseline;
- mean cost per request is lower than the baseline;
- there are zero provider/schema failures in the 20-case run.

Rollback trigger: keep `--mode llm` available. Any production rollout must route
low-confidence, provider-error, or out-of-distribution cases to the LLM or a
human reviewer.

## Implementation Steps

1. Add `jev_classifier.py` behind the existing `ClassificationResult` contract.
2. Keep question text and criteria in `config.py`.
3. Re-run both implementations on `dataset.jsonl`.
4. Compare accuracy, macro F1, latency, cost, and confidence coverage.
5. Keep the LLM path as fallback and report the measured result.

