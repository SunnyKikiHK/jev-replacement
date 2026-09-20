# Data Redaction and State Minimization

Read this reference before putting user data, production records, logs, or
internal documents into Jev `state`.

## Principle

Build `state` by allowlist, not by deleting a few fields from a larger record.
Send the smallest evidence needed for the question and keep identifiers in code
when possible.

## Never Send Without Explicit Approval

- passwords, API keys, access tokens, session cookies, private keys, or
  authentication headers;
- payment-card numbers, bank-account details, or security codes;
- government identifiers, medical records, legal privileged material, or other
  regulated data;
- precise location, private contact details, or employee/customer records when a
  pseudonymous identifier is sufficient;
- complete production logs or database rows with unrelated fields.

If the workflow requires sensitive data, document why the model needs it, use
the provider's approved data-retention terms, and still remove values that do
not affect the judgment.

## Preferred Substitutions

- Replace names and account numbers with stable internal IDs.
- Use category labels instead of raw dates or amounts when the exact number is
  not part of the semantic judgment.
- Hash identifiers consistently when correlation is needed.
- Truncate documents to relevant passages retrieved in code.
- Mask secrets as `<redacted>` if their presence, rather than their value, is
  part of the judgment.

## Example

Instead of sending this:

```json
{
  "customer": {
    "name": "<name>",
    "email": "<email>",
    "card_number": "<card-number>",
    "ssn": "<government-id>"
  },
  "message": "Please refund the duplicate charge."
}
```

Send this:

```json
{
  "customer_id": "cust_4812",
  "message": "Please refund the duplicate charge."
}
```

## Logging

- Do not log raw `state`, prompts, API keys, or provider headers.
- Log request IDs, model IDs, question IDs, answer labels, confidence, latency,
  and cost.
- Store redacted evidence separately with restricted retention when auditability
  requires it.
- Apply the same rules to fallback models, evaluators, traces, and exception
  messages.

## Provider Review

TypeSafe, OpenRouter, and any future proxy may have different retention and
processing terms. Confirm the applicable agreement before sending production
data, and do not assume an OpenRouter test configuration is suitable for
regulated workloads.

When uncertain, stop and ask the user rather than transmitting the data.
