# ADR-0011: Anthropic Claude models on Amazon Bedrock, configured by role, invoked through US inference profiles, with an eval set gating any model change

- **Status:** Accepted
- **Date:** 2026-09-28 (accepted 2026-10-10 with current models, US inference profiles and the bedrock-runtime client)
- **Deciders:** Founder (product and engineering)
- **Scope:** All LLM use in the pipeline (alt text, semantic QA, triage classification) and future features
- **Related:** `docs/REMEDIATION-PIPELINE-PRD.md`, `docs/INVENTORY-TRIAGE-PRD.md`, ADR-0004

## Context

The pipeline needs vision-and-language models for figure descriptions, structured judgments for semantic QA (reading order, heading levels, table headers, alt-text adequacy), and cheap classification for triage features. The existing code calls Bedrock with an outdated hard-coded model id (`services/functions/structure/services.py`) and the IAM policy in `infra/terraform/processing-lambdas.tf` allows only older model ARNs. Customers require that their content is not used to train models, that data stays in their region, and that we can state which model produced which output (the evidence pack records it). Model quality on charts and reading order is the difference between a checker pass and a useful document, so any model change must be measured, not assumed.

Constraints: cost of goods under $0.055 per page; Bedrock throughput quotas; AWS-native procurement (Bedrock spend counts toward AWS commitments; no separate vendor for procurement).

## Decision

We will invoke Anthropic Claude models on Amazon Bedrock through the Anthropic SDK's Bedrock client, with model ids set per role in configuration and recorded in every evidence pack: `BEDROCK_MODEL_ALT_TEXT` and `BEDROCK_MODEL_SEMANTIC_QA` default to Claude Opus 5.5, and `BEDROCK_MODEL_CLASSIFY` defaults to Claude Haiku 5.5. Claude Sonnet 5.5 is the designated cost step-down for bulk alt text and QA, adopted per role only when the eval set shows no quality loss.

These models are invoked only through inference profiles. We use the US geographic profiles (`us.anthropic.claude-opus-5-5`, `us.anthropic.claude-sonnet-5-5`, `us.anthropic.claude-haiku-5-5`), so requests are processed in US regions, not global profiles. Calls go through the bedrock-runtime API (the SDK's `AnthropicBedrock` client). The Mantle endpoint is reconsidered once it serves every configured model: on 2026-10-10 it returned "does not exist" for Sonnet 5.5 and Haiku 5.5, observed while the account's access to 5.x models was on hold. Prompts are versioned files. Every judgment uses structured outputs (`output_config.format`), not forced tool calls, which Opus 5.5 rejects. Effort is set per role: Opus 5.5 always thinks, and thinking tokens are billed as output. Bedrock Guardrails are enabled for PII in figure descriptions. No customer content is used for training (Bedrock's default), and the model id and prompt version are part of the artifact cache key (ADR-0001).

## Alternatives Considered

- **Call Anthropic's API directly** — Same models, but adds a vendor and data-flow to the compliance program and moves spend off AWS commitments; Bedrock keeps data inside the customer's expected boundary.
- **Amazon Nova or Titan models** — Lower cost, but weaker on chart understanding and structured judgments in our early tests; keep as a future eval candidate.
- **Amazon Rekognition and Textract only for alt text** — Labels and text are not descriptions; the existing `alt_text` function's Rekognition path produces checker-satisfying but meaningless text.
- **Fine-tune a small model** — Premature; no eval set or labeled data yet.

## Consequences

**Positive**

- Highest available quality on the judgments that matter; one vendor boundary (AWS); versioned, auditable model use.

**Negative / Trade-offs**

- Opus-tier pricing dominates LLM cost per page; the eval-gated step-down to Sonnet is how margins are protected. At the Price List's US ("standard") rates on 2026-10-10, Opus 5.5 costs $4.40 input and $22 output per million tokens, and Sonnet 5.5 half that. A rough estimate puts AI cost at $0.03 to $0.065 per page on Opus 5.5 and $0.014 to $0.033 on Sonnet 5.5, against a $0.055 target for the whole page.
- US geographic profiles cost about 10% more than global profiles; that premium buys the data residency statement. Bedrock model availability by region can lag.

**Neutral / Follow-ups**

- Replace the IAM policy in `processing-lambdas.tf`. Its `model/` ARNs match no Bedrock resource. Grant the inference-profile ARNs plus the foundation-model ARNs in every region the US profiles route to. Replace the hardcoded Claude 3.5 Sonnet id in `services/functions/structure/services.py` and the worker config with the per-role settings.
- Build the eval set (`docs/eval/`) by slice P1, not P3: the per-page cost target depends on the Sonnet step-down. Publish accuracy monthly.
- New accounts start with 5.x models unavailable (applied token quotas of 0 against defaults of 30M, 6M and 10M per minute for Opus, Sonnet and Haiku 5.5). The dev account's hold needs an AWS Support case. Expect the same in prod.
