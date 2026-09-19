# Jev API Notes

Use the live documentation as the source of truth:

- Documentation index: <https://docs.typesafe.ai/llms.txt>
- Introduction: <https://docs.typesafe.ai/introduction.md>
- System One architecture: <https://docs.typesafe.ai/concepts/system-one.md>
- Building guide: <https://docs.typesafe.ai/concepts/how-to-build-with-system-one.md>
- Primitives: <https://docs.typesafe.ai/primitives.md>
- Models and limits: <https://docs.typesafe.ai/models.md>
- Jev 1.13 limitations: <https://docs.typesafe.ai/model-jaggedness/jev-1.13.md>

The provider details below were verified on 2026-09-19. Recheck them when exact
model IDs or endpoints matter.

## Request Shape

Jev accepts a `state` and a record of `questions`.

```json
{
  "model": "jev-latest",
  "state": {
    "message": "I was charged twice for the same order."
  },
  "questions": {
    "refund_requested": {
      "type": "noul",
      "instructions": "Does `message` request a refund?"
    },
    "intent": {
      "type": "choice",
      "instructions": "What is the primary request in `message`?",
      "criteria": {
        "billing": "The request concerns charges, invoices, refunds, or plans.",
        "account": "The request concerns login, profile, or account access."
      }
    }
  }
}
```

`state` may be a string, JSON object, or array of text. `questions` is an object.
Question IDs are for application code and are not sent to the model.

## Primitives

Choose by the meaning of the answer:

| Need | Type | Result |
| --- | --- | --- |
| Pick from a defined set | `choice` | Selected option, probability per option, confidence |
| Decide whether a condition holds | `noul` | Probability from 0 to 1; no separate confidence |
| Rate a dimension with ordered levels | `score` | Continuous score, level probabilities, confidence |

Ask one narrow judgment per question. Independent questions over the same state
should be sent together because they run in parallel and cannot see each other's
answers.

Example `score` question for query-passage relevance:

```json
{
  "model": "jev-latest",
  "state": {
    "query": "What is the refund window?",
    "passage": "Refunds are available within 30 days of purchase."
  },
  "questions": {
    "relevance": {
      "type": "score",
      "instructions": "How directly does `passage` answer `query`?",
      "criteria": [
        "Irrelevant to the query.",
        "Topically related but does not answer it.",
        "Partially answers the query.",
        "Directly answers the query.",
        "Contains sufficient evidence for a grounded answer."
      ]
    }
  }
}
```

The response returns a continuous `score`, ordered `legend`, probabilities for
the levels, and confidence. Code should sort or threshold those values; Jev must
not generate the passage or compute embedding similarity.

Example score response:

```json
{
  "answers": {
    "relevance": {
      "type": "score",
      "score": 3.74,
      "legend": {
        "0": "Irrelevant to the query.",
        "1": "Topically related but does not answer it.",
        "2": "Partially answers the query.",
        "3": "Directly answers the query.",
        "4": "Contains sufficient evidence for a grounded answer."
      },
      "probabilities": {
        "0": 0.0,
        "1": 0.03,
        "2": 0.11,
        "3": 0.72,
        "4": 0.14
      },
      "confidence": 0.76
    }
  }
}
```

The score is continuous and may fall between levels. Thresholds must be selected
from target-domain data. For multiple candidates, prefer assigning candidate IDs
in `state` and asking one independent score question per candidate in the same
request when the combined state and questions fit the context budget. Code then
maps question IDs to candidate IDs and sorts the scores. Benchmark that batched
design against separate requests; do not assume either form is cheaper without
measurement.

## Response Shape

```json
{
  "model": "typesafe/jev-1.13-20260917",
  "answers": {
    "refund_requested": {
      "type": "noul",
      "noul": 0.97
    }
  },
  "usage": {
    "input_tokens": 110,
    "output_tokens": 12,
    "cost": 0.00000462
  },
  "provider": "TypeSafe"
}
```

Read answers from the `answers` object. A valid response can still contain the
wrong semantic decision.

## Provider Options

### TypeSafe Direct

- Endpoint: `POST https://api.typesafe.ai/v1/systemone`
- Model example: `jev-latest`
- Credential: `TYPESAFE_API_KEY`
- Context: currently documented as 64k total, with 32k for `state` plus the
  longest question.

Use the direct provider for production workloads and the larger documented
context window.

### OpenRouter Decisions API

- Endpoint: `POST https://openrouter.ai/api/alpha/decisions`
- Model example: `~typesafe/jev-latest`
- Credential: `OPENROUTER_API_KEY`
- Context: the Jev Latest model page advertised 32k on 2026-09-19.

OpenRouter's chat-completions endpoint rejects Jev because Jev is not a chat
model. Send TypeSafe's native `state` and `questions` schema to the Decisions
endpoint instead.

## Limits and Failure Modes

Do not use Jev for:

- free-form text generation, code generation, or explanations;
- exact arithmetic, counting, numeric interpolation, or date comparison;
- complex multi-hop reasoning or extensive indirection;
- native image, audio, or video understanding;
- high-stakes adversarial decisions without explicit hardening and review.

Jev can be literal, suffers from context rot, and may be moved by prompt-injection
content in `state`. State is currently text-first, and English is the strongest
language. Test non-English workloads against local data.

## Error Handling

Handle these categories explicitly:

- `400`: invalid request, wrong endpoint, or a model that is not a Decisions model.
- `401`: invalid or wrong-service API key.
- `402`: insufficient provider credit.
- `429` or `529`: rate limiting or overload; honor `Retry-After` and use bounded
  exponential backoff.
- malformed or missing `answers`: treat as a provider failure and use the fallback
  path.

Never retry authorization failures or invalid schemas indefinitely.
