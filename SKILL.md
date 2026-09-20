---
name: jev-replacement
license: MIT
metadata:
  version: "0.2.1"
  short-description: "Evaluate and migrate bounded decisions to TypeSafe Jev"
description: TypeSafe Jev is a non-generative decision model that accepts application state plus typed choice, noul, or score questions and returns typed answers, calibrated probabilities, and confidence rather than text. Use this skill to evaluate whether Jev should replace or augment bounded semantic decisions handled by brittle if/else rules, BERT-style or other trained classifiers, embedding rerankers, or LLM prompt-and-parse steps. It covers fit assessment, keep, shadow-test, hybrid, or migrate planning, implementation behind a rollback-safe adapter, and before-and-after evaluation of quality, confidence, latency, cost, and failures. Do not use it for generic model swaps that do not involve Jev, or for exact arithmetic, authorization, side effects, free-form generation, long-chain planning, or multimodal tasks.
---

# Jev Replacement

Migrate only the parts of an existing project where Jev is a better fit than the
current implementation. Treat migration as a measured refactor, not a wholesale
rewrite.

## What Jev Is

Jev is TypeSafe AI's non-generative decision model. It accepts application
`state` plus typed `choice`, `noul`, or `score` questions and returns typed
values, calibrated probabilities, and confidence. It does not chat, write prose
or code, produce explanations, execute actions, or perform long-chain planning.
Never call Jev through a normal chat-completions endpoint.

Do not rely on pretrained knowledge of Jev. Read
[references/jev-api.md](references/jev-api.md) before writing integration code.
Recheck the live TypeSafe or OpenRouter documentation when exact model IDs,
limits, schemas, or provider behavior matter.

Read [references/data-redaction.md](references/data-redaction.md) before
constructing `state` from user data, production records, logs, or internal
documents.

## Decision Outcomes

The correct outcome may be:

- **Keep**: Jev is not a safe or useful replacement.
- **Shadow test**: structural fit is promising, but operational or quality
  evidence is incomplete.
- **Hybrid**: Jev handles bounded or uncertain cases while the existing model
  remains primary.
- **Migrate**: the measured acceptance gate passes and rollback is understood.

Do not force a migration. If no candidate passes the fit checks, stop with a
no-change report and explain what evidence would change the decision.

## Required Outcomes

Deliver all of these when the user authorizes implementation and the evidence
supports migration:

1. A candidate inventory with a keep, shadow-test, hybrid, or migrate decision
   for each workflow.
2. A baseline measurement before replacing behavior.
3. A migration plan with preserved interfaces, fallback behavior, and rollback.
4. The implementation, with questions and thresholds centralized and reviewable.
5. A before-and-after evaluation using the same representative cases.
6. A final report that states gains, regressions, uncertainty, and remaining risk.

## Workflow

### 1. Establish Scope and Baseline

Inspect the project before editing. Identify semantic decisions currently made by
plain `if/else`, heuristics, classical ML, neural classifiers, BERT-style models,
embedding-based rerankers, or LLM prompts that parse text into values.

Before changing behavior, capture the strongest available baseline:

- Use existing tests, labeled examples, production samples, or construct a small
  representative evaluation set when the user authorizes it.
- Record task-level quality, confidence or abstention behavior, latency, cost,
  provider failures, and the consequence of each error class.
- Define the acceptance gate before implementation. At minimum, keep the contract
  of the current component and decide how much quality regression is acceptable.

Read [references/migration-playbook.md](references/migration-playbook.md) when
inventorying candidates, deciding fit, or writing the plan.

### 2. Decide What Not to Replace

Keep deterministic code for exact rules, arithmetic, counting, sorting, lookup,
date comparison, authorization, and side effects. Keep generative models for
open-ended writing, code generation, explanation, long-chain reasoning, planning,
or multimodal understanding.

Do not recommend Jev merely because the current implementation is an LLM. Compare
the actual decision shape and deployment constraints. A simple static mapping may
need no model at all.

### 3. Check Operational Fit

Structural fit is not deployment fit. Before choosing a migration, compare the
current and proposed paths across:

- p50, p95, and p99 end-to-end latency, including network round trips, queueing,
  retries, and fallback;
- fully loaded cost, including owned GPU capacity, provider tokens, monitoring,
  operations, and failure recovery;
- data residency, privacy, offline operation, provider availability, and outage
  behavior;
- peak concurrency and request volume rather than average throughput alone;
- token growth from state, criteria, and large choice sets.

A remote Jev call may be a poor replacement for a low-latency colocated model even
when its semantic fit is excellent. In that case, prefer shadow testing, a hybrid
boundary, or keeping the existing implementation.

### 4. Design the Jev Boundary

Choose the smallest workflow that can be measured independently. Preserve the
existing public interface and add a provider adapter behind it so rollback is a
configuration change rather than a rewrite.

For each candidate, define:

- `state`: only the facts needed for that decision, using named JSON fields.
- primitive: `choice`, `noul`, or `score`.
- complete `instructions` and explicit `criteria`.
- confidence or probability thresholds selected from baseline data.
- fallback behavior for uncertainty, provider errors, and out-of-distribution input.
- whether the replacement runs in shadow mode, a canary, or a full rollout.

For large choice sets, measure criteria-token growth and latency. Test grouped,
hierarchical, or independent judgments before assuming one request is the best
design.

Read [references/jev-api.md](references/jev-api.md) before writing integration
code. Recheck the live TypeSafe or OpenRouter documentation when exact model IDs,
limits, or schemas matter.

### 5. Plan Before Implementing

Produce a compact plan containing:

- candidate and current implementation;
- expected benefit and error risk;
- state and question design;
- untouched behavior;
- rollback trigger;
- evaluation data and acceptance thresholds;
- implementation and verification steps.

Prefer one candidate per migration commit. Do not remove the old path until the
acceptance gate passes. Reserve evaluation data that was not used to tune the
questions or thresholds.

### 6. Implement

Use the project's existing language, dependency policy, error handling, and test
patterns. Centralize question definitions and thresholds in one reviewable module.
Do not hardcode credentials; read them from environment variables.

For a quick provider-neutral HTTP client, use
[scripts/jev_client.py](scripts/jev_client.py). For a first-pass candidate scan,
use [scripts/scan_candidates.py](scripts/scan_candidates.py).

### 7. Evaluate and Decide

Run baseline and candidate implementations over the same cases. Compare task
quality, calibration or coverage, latency, cost, and failure modes. Treat Jev's
schema safety as an interface guarantee, not evidence that a decision is correct.

Use [references/evaluation.md](references/evaluation.md) to choose metrics and
interpret results. Use
[scripts/evaluate_predictions.py](scripts/evaluate_predictions.py) when prediction
files are available, or [scripts/evaluate_rankings.py](scripts/evaluate_rankings.py)
for reranking and retrieval comparisons.

If the gate fails, keep the old implementation, report the failure, and adjust the
question design, thresholds, state, or candidate choice before trying again.
For claims that one implementation is better, report sample size and uncertainty;
a small point-estimate improvement is not enough.

## Guardrails

- Preserve unrelated behavior and user changes.
- Do not claim Jev is better without same-data measurements.
- Do not use Jev for exact arithmetic, counting, date ordering, or free-form text
  generation.
- Do not send secrets, private data, or unnecessary context in `state`.
- Do not rely on a confidence threshold tuned on a different model or dataset.
- Do not let an agent-authored threshold become policy without human-reviewable
  code and documented consequences.
- Do not delete the baseline implementation until rollback and production behavior
  are understood.
- Challenge broad requests such as "make the whole workflow AI-driven." Decompose
  them and preserve deterministic boundaries for payments, permissions, compliance,
  arithmetic, and side effects.
