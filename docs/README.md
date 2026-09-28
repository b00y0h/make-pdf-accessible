# Documentation index

## Plan and strategy

| Document                                                                                         | Purpose                                                                                                             |
| ------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------- |
| [`business/BUSINESS-PLAN.md`](business/BUSINESS-PLAN.md)                                         | Business plan: market, positioning, pricing, go-to-market, unit economics, financial model, team, risks, milestones |
| [`research/higher-ed-market-research-2026-09.md`](research/higher-ed-market-research-2026-09.md) | Market and regulatory research (ADA Title II, Section 504, state law), demand evidence, competitors, code audit     |
| [`research/ithaka-pipeline-analysis.md`](research/ithaka-pipeline-analysis.md)                   | Analysis of ITHAKA's on-demand PDF remediation pipeline on AWS: what to adopt, where to go further                  |

## Product requirement documents (PRDs)

| Document                                                     | Scope                                                                                                                                        |
| ------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------- |
| [`PLATFORM-PRD.md`](PLATFORM-PRD.md)                         | Umbrella: the six-stage loop (Inventory, Triage, Remediate or Convert, Publish, Prove, Maintain), locked decisions, success criteria, slices |
| [`REMEDIATION-PIPELINE-PRD.md`](REMEDIATION-PIPELINE-PRD.md) | Page-parallel, engine-pluggable, validated pipeline with evidence packs, review workbench and the Accessible Link                            |
| [`INVENTORY-TRIAGE-PRD.md`](INVENTORY-TRIAGE-PRD.md)         | Crawler, connectors, imports, rule-based triage, plan exports, maintenance, free website report                                              |
| [`INTEGRATIONS-PRD.md`](INTEGRATIONS-PRD.md)                 | WordPress and Drupal publish-back, LTI 1.3, public API and webhooks, Accessible Link                                                         |
| [`ENTERPRISE-READINESS-PRD.md`](ENTERPRISE-READINESS-PRD.md) | Identity (Cognito with SAML/OIDC), tenancy and RBAC, audit, metering and billing, SLOs and DR, compliance program                            |
| [`MARKETING-SITE-PRD.md`](MARKETING-SITE-PRD.md)             | The public site at makepdfaccessible.com: information architecture, lead capture, trust center, accessibility and performance gates, hosting |

## Architecture decision records

See [`adr/README.md`](adr/README.md) for the index (ADR-0001 to ADR-0011).

## Execution specs (ordered, file-level implementation plans)

| Document                                                         | Implements                                                                                                                                                       |
| ---------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [`AWS-DEPLOYMENT-SPECS.md`](AWS-DEPLOYMENT-SPECS.md)             | Terraform validity, remote state per environment, static-site module, marketing site app and deploy workflow, multi-account guardrails                           |
| [`REMEDIATION-PIPELINE-SPECS.md`](REMEDIATION-PIPELINE-SPECS.md) | Removing mocks, engine adapter, PDFix and veraPDF containers, evidence packs, Distributed Map, alt text and QA, Accessible Link, HTML profile, worker retirement |
| [`INVENTORY-TRIAGE-SPECS.md`](INVENTORY-TRIAGE-SPECS.md)         | Inventory schema and API, crawler, rules engine, dashboard views, connectors and imports, schedules, free report                                                 |
| [`ENTERPRISE-READINESS-SPECS.md`](ENTERPRISE-READINESS-SPECS.md) | Aurora and migrations, Mongo cutover, Cognito everywhere, audit and metering, Stripe billing, SLOs and DR, compliance scaffolding                                |

## Operational references

| Document                                                                                       | Purpose                                                                  |
| ---------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| [`LLM_INTEGRATION.md`](LLM_INTEGRATION.md)                                                     | Deprecated discovery approach (public embeddings endpoints are disabled) |
| [`costs/RUNBOOK.md`](costs/RUNBOOK.md), [`costs/DATA_DICTIONARY.md`](costs/DATA_DICTIONARY.md) | AWS cost dashboard operations                                            |
| [`gap-report.md`](gap-report.md), [`implementation-plan.md`](implementation-plan.md)           | Earlier (2025) audit and plan, superseded by the PRDs and specs above    |
| [`../infra/terraform/README.md`](../infra/terraform/README.md)                                 | Infrastructure: bootstrap, environments, deploy                          |
