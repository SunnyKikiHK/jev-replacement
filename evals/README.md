# Cold-Start Discovery Evaluation

This suite checks whether an agent can identify when to invoke
`$jev-replacement` without prior conversation context or prior knowledge of
Jev.

## Protocol

1. Start a fresh agent with no forked conversation history.
2. Provide only the installed skill catalog metadata or the frontmatter
   description and UI metadata.
3. Give one request from `discovery-cases.jsonl`.
4. Record whether the agent invokes the skill.
5. Compare the result with `expected`.
6. Do not mention Jev API details, previous migrations, or the desired answer.

## Why This Suite Exists

Earlier forward tests used forked context and explicit instructions to load the
skill. Those tests exercised execution after invocation, not real discovery.
This suite prevents that mistake by testing the selection boundary directly.

## Cases

- Positive cases must invoke the skill for explicit Jev fit, migration,
  reranking, routing, verification, and guarded rejection scenarios.
- Negative cases must avoid invoking the skill for generic model swaps,
  free-form generation, general product explanation, and multimodal work.

Run the schema checks with:

```bash
python -m unittest tests.test_discovery_cases -v
```

