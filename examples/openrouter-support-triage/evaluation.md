# Evaluation Result

## Run

Date: 2026-09-19

Dataset: 20 labeled support messages, five per category.

Baseline: `meta-llama/llama-3.3-70b-instruct` through OpenRouter chat
completions.

Replacement: Jev through OpenRouter Decisions API using
`typesafe/jev-1.13`.

Both implementations ran in the same process against the same dataset.

## Results

| Metric | LLM baseline | Jev | Change |
| --- | ---: | ---: | ---: |
| Accuracy | 0.9500 | 1.0000 | +0.0500 |
| Macro F1 | 0.9495 | 1.0000 | +0.0505 |
| p50 latency | 613.58 ms | 307.06 ms | 0.5004x |
| p95 latency | 961.85 ms | 614.43 ms | 0.6388x |
| Mean cost | $0.00001495 | $0.00001900 | 1.2709x |
| Provider errors | 0 | 0 | none |

## Confidence

Jev assigned confidence `>= 0.8` to 19 of 20 cases:

- coverage at the threshold: `0.95`;
- accuracy on accepted cases: `1.00`;
- `billing-declined`: confidence `0.65`, predicted `billing` correctly.

The low-confidence cases should route to the LLM or human review in a production
policy, even though both happened to be correct here.

## Acceptance Gate

| Gate | Result |
| --- | --- |
| Accuracy at least 0.90 | Pass |
| Macro F1 at least 0.90 | Pass |
| No more than 0.05 absolute accuracy regression | Pass |
| p50 latency lower than baseline | Pass |
| Mean cost lower than baseline | **Fail** |
| Zero provider/schema failures | Pass |

## Decision

The replacement is a **partial success**, not an unconditional replacement.

- Jev improved task quality on this dataset.
- Jev reduced p50 latency by about 2.0x and p95 latency by about 1.6x.
- For short, single-message requests, Jev cost about 1.27x more because the
  question definitions and criteria add fixed input tokens.
- The LLM path must remain available as a fallback for low-confidence,
  provider-error, and cost-sensitive cases.

The next cost experiment should compare Jev against a cheaper or smaller LLM and
measure workloads with longer state, more labels, or repeated decisions. This
20-case run is enough to validate the integration, not to establish a universal
cost advantage.

## Artifacts

- `evaluation-llm.json`: full baseline rows and metrics.
- `evaluation-jev.json`: full Jev rows and metrics.
- `comparison.json`: machine-readable metric deltas.
