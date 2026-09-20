# OpenRouter Support Triage

This example compares a normal OpenRouter chat model with TypeSafe Jev for a
small support-ticket classification task.

The baseline uses `meta-llama/llama-3.3-70b-instruct` through the OpenRouter
chat-completions API. The replacement uses Jev through OpenRouter's Decisions
API.

## Dataset

`dataset.jsonl` contains support messages with one of four labels:

- `account`
- `billing`
- `bug`
- `feature_request`

## Baseline

```bash
python evaluate.py --mode llm
```

The command writes `evaluation-llm.json`.

## Jev replacement

The migration design and acceptance gate are recorded in `migration-plan.md`.
The replacement is implemented in `jev_classifier.py`:

```bash
python evaluate.py --mode jev
```

The command writes `evaluation-jev.json`.

The benchmark uses pinned model IDs recorded in `model-manifest.json`. Set
`JE_V_MODEL` to override the candidate model for a separate experiment.

To run both in one process and print a comparison:

```bash
python evaluate.py --mode compare
```

The OpenRouter key is read from the repository-level `.env` file or the
`OPENROUTER_API_KEY` environment variable.

The LLM implementation remains available as the rollback path.

The measured outcome and acceptance-gate decision are recorded in
`evaluation.md`.
