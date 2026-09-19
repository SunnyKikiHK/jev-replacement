# Evaluation Guide

## Measure Before Replacing

Use the same representative cases for the old implementation and Jev. Prefer
existing test data or production samples. If neither exists, create a small
labeled set with the user and clearly label it as an initial estimate.

Record:

- dataset source, size, label definition, and class balance;
- baseline model or rule version;
- Jev model ID and question configuration;
- provider and request settings;
- timestamp and environment.

Do not compare a tuned Jev implementation against an unmeasured or straw-man
baseline.

## Metrics by Decision Shape

### Classification or Routing

- accuracy;
- macro precision, recall, and F1;
- per-label confusion and support;
- coverage and accuracy after confidence gating;
- severe-error rate for error classes with different costs.

### Detection or Verification

- precision and recall at the operating threshold;
- false-positive and false-negative counts;
- calibration or expected calibration error when enough samples exist;
- abstention and human-review rate.

### Scoring or Ranking

- correlation with the baseline or human labels;
- ordering quality, such as NDCG when graded relevance exists;
- threshold error;
- stability across repeated semantically equivalent inputs.

### Operations

- p50 and p95 end-to-end latency;
- mean and total cost;
- provider error rate;
- retry rate;
- fallback or escalation rate.

## Acceptance Gate

Set the gate before implementation. A practical starting point is:

```text
quality >= baseline - allowed_regression
confidence-gated accuracy >= required_accuracy
p95 latency <= current_budget
cost_per_decision <= current_cost
provider failures follow the documented fallback
```

For high-consequence decisions, require no regression on severe errors even when
aggregate accuracy improves. For low-consequence routing, a small quality change
may be acceptable when latency and cost improve materially.

## Calibration and Confidence

Calibration is measured across groups of predictions and does not guarantee that
one answer is correct. Do not copy a confidence threshold from documentation,
another model, or another dataset. Plot threshold against precision, recall,
coverage, and business outcome on the target data.

For a `choice` or `score`, confidence summarizes distribution concentration. A
spread distribution can be legitimate when several options are acceptable. For a
`noul`, the returned value is the probability of yes and does not have a separate
confidence field.

## Shadow and Canary Evaluation

Shadow mode runs Jev without changing the user-visible result. Canary mode changes
a limited share of traffic and retains a rollback path.

Before rollout, verify:

- the old and new implementations consume the same input state;
- low-confidence and provider-error cases fall back predictably;
- thresholds are stored in reviewable code;
- no secret or unnecessary personal data is sent;
- rollback does not require a data migration.

## Reporting

Record a compact result with:

- final decision: replace, shadow only, or keep old implementation;
- baseline and candidate metrics;
- uncertainty and sample-size limitations;
- per-class regressions;
- fallback rate and operational cost;
- remaining risks and the next measurement needed.

Useful comparison script:

```bash
python scripts/evaluate_predictions.py \
  --gold gold.jsonl \
  --baseline baseline-predictions.jsonl \
  --candidate jev-predictions.jsonl \
  --output comparison.json
```

