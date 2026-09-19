# Migration Playbook

## Candidate Inventory

Start with a deterministic scan, then verify each hit manually.

```bash
python scripts/scan_candidates.py /path/to/project --format markdown
```

Look for:

- semantic `if/else` trees with keyword lists, thresholds, or overlapping labels;
- scikit-learn, PyTorch, TensorFlow, Transformers, BERT, embedding, or vector
  classifiers;
- LLM prompts that classify, route, score, rank, verify, moderate, or select a
  candidate;
- regex extraction followed by a semantic choice;
- repeated prompt-and-parse code with schema repair or retries;
- human-review queues driven by uncertain or missing labels.

The scan is only a lead generator. Inspect callers, tests, data flow, latency
budgets, and error consequences before proposing replacement.

## Fit Matrix

### Good Fit

- The output is one of a bounded choice set.
- The output is a yes/no or probability judgment.
- The output is an ordered score or ranking signal.
- The decision is a fast semantic judgment over text or structured state.
- The workflow can decompose into independent questions.
- Uncertain decisions can safely fall back to the old model, a reasoning model,
  or a person.
- Repeated calls make latency or cost material.

Common examples: routing, topic or intent classification, relevance scoring,
risk detection, moderation signals, citation support, policy checks, tool-call
verification, RAG passage filtering, and choosing a value from generated
candidates.

### Poor Fit

- Exact deterministic logic that already works.
- Arithmetic, counting, unit conversion, date ordering, or numeric precision.
- Open-ended generation, code generation, explanation, or creative work.
- Planning and long-chain reasoning with many dependent steps.
- Native image, audio, or video processing.
- Decisions that require a global structural invariant across separate answers.
- Workflows with no representative evaluation data and no safe fallback.

## Operational Fit

Structural fit does not settle deployment fit. For high-volume or latency-critical
services, record:

- p50, p95, and p99 end-to-end latency under realistic concurrency;
- network round-trip, queueing, retry, timeout, and fallback overhead;
- fully loaded cost, including owned GPU depreciation, power, hosting, and
  operations;
- whether retiring or reallocating the old capacity is actually possible;
- data residency, privacy, offline, and provider-availability requirements;
- token growth from state, criteria, and large choice sets;
- the projected monthly cost at real request volume.

Use **keep** or **hybrid** when fixed local capacity is cheaper, the existing
p95 is below a practical remote-API floor, the data cannot leave the environment,
or provider outages cannot be tolerated.

For large choice sets, benchmark one large `choice` against grouped or
hierarchical questions. More criteria increase input tokens and can reduce
accuracy as the state grows.

## Retrieval and Reranking

Do not treat "replace embeddings with Jev" as one candidate. Inventory the stages:

| Stage | Jev decision |
| --- | --- |
| Document or query embedding | Keep; Jev does not produce embedding vectors. |
| ANN/vector index and top-K retrieval | Keep; Jev cannot index or search the corpus. |
| Cross-encoder reranking | Conditional; test `score` or `choice` on a bounded shortlist. |
| Answer generation | Keep; Jev is not generative. |
| Citation or support verification | Conditional `noul` candidate. |

For reranking, measure calls per query. If each candidate needs a separate call,
calculate cost and latency for the full shortlist. Prefer a smaller shortlist,
a hybrid reranker, or grouped candidate judgments when one call per candidate is
not viable.

When several candidates fit one request, put a bounded candidate array in
`state`, ask one independent score question per candidate, and map the answer IDs
back to candidate IDs in code. Measure the actual token budget, latency, and
accuracy against separate calls.

Define disagreement behavior before rollout. When Jev and the old reranker return
different top-K lists, choose one policy: old model primary, Jev primary, union of
both lists, Jev as tie-breaker, or human review for material disagreement. Keep
the policy in code and evaluate it as part of the gate.

## Candidate Record

For each candidate, record:

| Field | Question |
| --- | --- |
| Current implementation | What exactly makes the decision today? |
| Input contract | What state is available, and what is sensitive? |
| Output contract | Labels, score range, threshold, or selected candidate? |
| Call volume | How often does this run, and what is the latency budget? |
| Error cost | What happens for a false positive, false negative, or abstention? |
| Baseline evidence | Tests, labels, production samples, or no data? |
| Jev design | State, primitive, criteria, confidence gate, fallback? |
| Fit | Replace, shadow test, keep, or reject? |

## Migration Plan Template

```markdown
## Candidate

Current implementation:
Target behavior:
Why Jev fits:
Why Jev might fail:

## Contract

Input:
Output:
Unchanged behavior:
Fallback:

## Design

Primitive:
State:
Instructions and criteria:
Thresholds:
Provider:

## Evaluation

Dataset:
Baseline metrics:
Acceptance gate:
Rollout mode:
Rollback trigger:

## Steps

1. Add the adapter and question configuration.
2. Add tests for response mapping, uncertainty, and provider errors.
3. Run shadow evaluation.
4. Compare against the gate.
5. Enable the canary or full rollout only after the gate passes.
```

## Migration Patterns

### Replace an LLM Prompt-and-Parse Step

Keep an LLM for generation, open-ended reasoning, or candidate creation. Replace
the bounded decision with Jev:

1. Preserve the existing input as a named `state`.
2. Convert the prompt's allowed outputs into `choice`, `noul`, or `score`.
3. Remove schema-repair prompts and parse retries from the decision path.
4. Retain the old LLM path as the uncertainty or provider-error fallback.

### Replace a Classical or Neural Classifier

1. Reuse the classifier's labels as Jev criteria.
2. Compare on the held-out data used for the old model.
3. Keep feature extraction if it produces exact state; do not remove useful
   deterministic preprocessing.
4. Evaluate confidence and abstention separately before treating direct labels as
   interchangeable.

### Replace Semantic `if/else`

Do not replace syntax. Replace only the semantic condition:

```text
many keyword checks -> one explicit Choice or Noul question
```

Keep exact ranges, account permissions, and final actions in code.

### Replace Candidate Extraction

Use regex, a parser, or a generative model to produce a bounded candidate set.
Use Jev to select or score the candidate, then copy the original source value in
code. Never ask Jev to generate an exact value when it can select one.

## Rollout

1. Run baseline and Jev in shadow mode on the same cases.
2. Add a canary with a rollback flag.
3. Route low-confidence or provider-error cases to the old implementation.
4. Monitor quality, fallback rate, latency, and cost.
5. Remove the old path only after the acceptance gate passes and rollback is no
   longer operationally needed.
