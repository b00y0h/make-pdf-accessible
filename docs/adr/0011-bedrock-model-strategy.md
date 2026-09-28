# ADR-0011: Anthropic Claude models on Amazon Bedrock, configured by role, invoked through the Anthropic Bedrock client, with an eval set gating any model change

- **Status:** Proposed
- **Date:** 2026-09-28
- **Deciders:** Founder (product and engineering)
- **Scope:** All LLM use in the pipeline (alt text, semantic QA, triage classification) and future features
- **Related:** `docs/REMEDIATION-PIPELINE-PRD.md`, `docs/INVENTORY-TRIAGE-PRD.md`, ADR-0004

## Context

The pipeline needs vision-and-language models for figure descriptions, structured judgments for semantic QA (reading order, heading levels, table headers, alt-text adequacy), and cheap classification for triage features. The existing code calls Bedrock with an outdated hard-coded model id (`services/functions/structure/services.py`) and the IAM policy in `infra/terraform/processing-lambdas.tf` allows only older model ARNs. Customers require that their content is not used to train models, that data stays in their region, and that we can state which model produced which output (the evidence pack records it). Model quality on charts and reading order is the difference between a checker pass and a useful document, so any model change must be measured, not assumed.

Constraints: cost of goods under $0.055 per page; Bedrock throughput quotas; AWS-native procurement (Bedrock spend counts toward AWS commitments; no separate vendor for procurement).

## Decision

We will invoke Anthropic Claude models on Amazon Bedrock through the Anthropic Bedrock (Mantle) client, with model ids set per role in configuration and recorded in every evidence pack: `BEDROCK_MODEL_ALT_TEXT` and `BEDROCK_MODEL_SEMANTIC_QA` default to `anthropic.claude-opus-5`, and `BEDROCK_MODEL_CLASSIFY` defaults to `anthropic.claude-haiku-4-5`. `anthropic.claude-sonnet-5` is the designated cost step-down for bulk alt text and QA, adopted per role only when the eval set shows no quality loss. Prompts are versioned files; structured outputs are used for every judgment; cross-region inference profiles are used for throughput; Bedrock Guardrails are enabled for PII in figure descriptions. No customer content is used for training (Bedrock's default), and the model id and prompt version are part of the artifact cache key.

## Alternatives Considered

- **Call Anthropic's API directly** — Same models, but adds a vendor and data-flow to the compliance program and moves spend off AWS commitments; Bedrock keeps data inside the customer's expected boundary.
- **Amazon Nova or Titan models** — Lower cost, but weaker on chart understanding and structured judgments in our early tests; keep as a future eval candidate.
- **Amazon Rekognition and Textract only for alt text** — Labels and text are not descriptions; the existing `alt_text` function's Rekognition path produces checker-satisfying but meaningless text.
- **Fine-tune a small model** — Premature; no eval set or labeled data yet.

## Consequences

**Positive**

- Highest available quality on the judgments that matter; one vendor boundary (AWS); versioned, auditable model use.

**Negative / Trade-offs**

- Opus-tier pricing dominates LLM cost per page; the eval-gated step-down to Sonnet is how margins are protected.
- Bedrock model availability by region can lag; cross-region inference mitigates but complicates data residency statements.

**Neutral / Follow-ups**

- Update the IAM policy in `processing-lambdas.tf` to the inference-profile ARNs for the configured models.
- Build the eval set (`docs/eval/`) before slice P3; publish accuracy monthly.
