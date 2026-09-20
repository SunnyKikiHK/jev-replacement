# Jev Replacement

`jev-replacement` is a Codex agent skill for deciding whether TypeSafe Jev should
replace or augment an existing semantic decision, then proving the result with a
measured migration.

It is not a generic "rewrite everything with AI" skill. A keep, shadow-test,
hybrid, or reject decision is a successful outcome.

## What Is Jev?

Jev is TypeSafe AI's non-generative decision model. It accepts application
`state` and typed `choice`, `noul`, or `score` questions, then returns typed
answers, calibrated probabilities, and confidence. It does not chat, generate
prose or code, execute actions, or perform long-chain planning.

That distinction matters because an agent that has never seen Jev may otherwise
assume it is another LLM. This skill does not rely on pretrained knowledge of
Jev; it contains the required API and migration guidance.

## What It Handles

Use the skill when a project contains:

- keyword-heavy `if/else` logic that is doing semantic interpretation;
- scikit-learn, PyTorch, TensorFlow, BERT, or other trained classifiers;
- embeddings or cross-encoders used for bounded relevance scoring or reranking;
- LLM prompts that classify, route, score, rank, verify, moderate, or select a
  bounded result and then parse the generated text;
- uncertainty or human-review queues that could be replaced by confidence-aware
  decisions.

Do not use Jev for exact arithmetic, counting, date ordering, authorization,
side effects, free-form generation, planning, or native multimodal processing.

## What It Produces

The skill guides an agent through:

1. Scanning the project for candidate decisions.
2. Measuring the current implementation before editing.
3. Deciding **keep**, **shadow test**, **hybrid**, or **migrate**.
4. Designing the Jev `state`, questions, criteria, thresholds, and fallback.
5. Implementing behind the existing interface with rollback intact.
6. Comparing quality, confidence coverage, latency, cost, and failures on the
   same evaluation data.
7. Reporting gains, regressions, uncertainty, and remaining operational risk.

## Install

Clone this repository into a Codex skills directory, or install it with the
Skills CLI:

```bash
npx skills add SunnyKikiHK/jev-replacement --skill jev-replacement
```

Invoke it explicitly with:

```text
$jev-replacement
```

Example prompt:

```text
Use $jev-replacement to evaluate whether our BERT intent classifier should be
replaced, shadow-tested, or kept. Build a migration plan and benchmark it.
```

## Providers

The skill supports two Jev providers:

- TypeSafe direct: `POST https://api.typesafe.ai/v1/systemone`
- OpenRouter Decisions API: `POST https://openrouter.ai/api/alpha/decisions`

Use `TYPESAFE_API_KEY` for TypeSafe direct or `OPENROUTER_API_KEY` for OpenRouter.
Jev must not be called through a normal chat-completions endpoint.

The reusable client is [scripts/jev_client.py](scripts/jev_client.py). It uses
the native `state` and `questions` contract and retries only transient provider
errors.

## Repository Layout

```text
jev-replacement/
|-- SKILL.md
|-- agents/openai.yaml
|-- references/
|   |-- jev-api.md
|   |-- migration-playbook.md
|   `-- evaluation.md
|-- scripts/
|   |-- jev_client.py
|   |-- scan_candidates.py
|   |-- evaluate_predictions.py
|   `-- evaluate_rankings.py
|-- examples/openrouter-support-triage/
`-- tests/
```

The example compares an OpenRouter LLM with Jev on a 20-case support-triage
dataset. It includes the migration plan, full prediction rows, and final decision
record.

## Example Result

The included experiment found:

- accuracy: `0.90` to `1.00`;
- macro F1: `0.9028` to `1.0000`;
- p50 latency: `675.66 ms` to `253.13 ms`;
- mean cost: `1.52x` higher.

The result was recorded as a partial success: Jev passed quality and latency
gates but failed the cost gate for short single-message requests. The LLM path
remains the fallback. See
[examples/openrouter-support-triage/evaluation.md](examples/openrouter-support-triage/evaluation.md).

## Validation

Run the bundled checks:

```bash
python -m unittest discover -s tests -v
python scripts/scan_candidates.py . --format markdown
```

For reranking migrations, use:

```bash
python scripts/evaluate_rankings.py \
  --gold ranked-gold.jsonl \
  --baseline baseline-ranked.jsonl \
  --candidate jev-ranked.jsonl \
  --k 1,5,8,10
```

The skill itself is validated with the Codex `skill-creator` validator.
GitHub Actions runs the unit tests, Python compilation, ASCII checks, and a
committed-secret scan on every push and pull request.

## Forward Tests

The skill was evaluated in two independent trial rounds:

- Round 1 tested LLM prompt-and-parse replacement, a high-volume BERT
  classifier, a deterministic billing workflow, and an embedding plus
  cross-encoder RAG stack.
- Round 2 re-tested discovery and the revised guidance for BERT and RAG after
  the first improvements.

Cold-start discovery cases are recorded in
[evals/discovery-cases.jsonl](evals/discovery-cases.jsonl). They must be run
without forked conversation context so that the test does not leak prior Jev
knowledge to the evaluating agent.

The trials found and fixed:

- vague UI metadata that did not communicate shadow testing or no-change
  outcomes;
- wording that biased the agent toward migration instead of keep or hybrid;
- missing operational checks for remote latency, p99, peak concurrency, and
  owned-GPU economics;
- incomplete RAG stage separation and scoring guidance;
- missing multi-candidate, disagreement, and ranking-evaluation guidance.

Round 2 correctly produced `keep` and `shadow-test` recommendations for the
high-volume BERT and RAG scenarios rather than forcing migration.

## Discovery Behavior

The frontmatter description explicitly covers Jev fit assessment,
BERT/classifier replacement, embeddings used for reranking, LLM
prompt-and-parse migration, shadow testing, and before-and-after evaluation.

The skill intentionally distinguishes stage-level replacements:

- a bi-encoder or ANN index should be kept;
- a cross-encoder reranker may be a shadow-test candidate;
- LLM generation must remain generative;
- deterministic policy and arithmetic remain in code.

## License

This repository is licensed under the MIT License. See [LICENSE](LICENSE).
