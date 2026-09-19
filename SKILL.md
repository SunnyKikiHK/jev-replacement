---
name: jev-replacement
description: Assess an existing project for replacing brittle semantic if/else rules, classifiers, embeddings, or LLM prompt-and-parse steps with TypeSafe Jev; produce a migration plan, implement the replacement, and evaluate before-and-after performance. Use when the user asks to adopt Jev or explicitly test whether Jev should replace classification, routing, scoring, ranking, verification, moderation, or bounded candidate selection.
---

# Jev Replacement

Migrate only the parts of an existing project where Jev is a better fit than the
current implementation. Treat migration as a measured refactor, not a wholesale
rewrite.

## Required Outcomes

Deliver all of these when the user authorizes implementation:

1. A candidate inventory with a fit decision for each workflow.
2. A baseline measurement before replacing behavior.
3. A migration plan with preserved interfaces, fallback behavior, and rollback.
4. The implementation, with questions and thresholds centralized and reviewable.
5. A before-and-after evaluation using the same representative cases.
6. A final report that states gains, regressions, uncertainty, and remaining risk.

## Workflow

### 1. Establish Scope and Baseline

Inspect the project before editing. Identify semantic decisions currently made by
plain `if/else`, heuristics, classical ML, neural classifiers, BERT-style models,
embeddings, or LLM prompts that parse text into values.

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

### 3. Design the Jev Boundary

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

Read [references/jev-api.md](references/jev-api.md) before writing integration
code. Recheck the live TypeSafe or OpenRouter documentation when exact model IDs,
limits, or schemas matter.

### 4. Plan Before Implementing

Produce a compact plan containing:

- candidate and current implementation;
- expected benefit and error risk;
- state and question design;
- untouched behavior;
- rollback trigger;
- evaluation data and acceptance thresholds;
- implementation and verification steps.

Prefer one candidate per migration commit. Do not remove the old path until the
acceptance gate passes.

### 5. Implement

Use the project's existing language, dependency policy, error handling, and test
patterns. Centralize question definitions and thresholds in one reviewable module.
Do not hardcode credentials; read them from environment variables.

For a quick provider-neutral HTTP client, use
[scripts/jev_client.py](scripts/jev_client.py). For a first-pass candidate scan,
use [scripts/scan_candidates.py](scripts/scan_candidates.py).

### 6. Evaluate and Decide

Run baseline and candidate implementations over the same cases. Compare task
quality, calibration or coverage, latency, cost, and failure modes. Treat Jev's
schema safety as an interface guarantee, not evidence that a decision is correct.

Use [references/evaluation.md](references/evaluation.md) to choose metrics and
interpret results. Use
[scripts/evaluate_predictions.py](scripts/evaluate_predictions.py) when prediction
files are available.

If the gate fails, keep the old implementation, report the failure, and adjust the
question design, thresholds, state, or candidate choice before trying again.

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

