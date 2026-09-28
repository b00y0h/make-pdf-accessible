# Architecture Decision Records

One decision per file, MADR-style, numbered sequentially. New decisions start as **Proposed** and become **Accepted** when ratified; a changed decision is recorded as a new ADR that supersedes the old one.

| ADR                                                           | Title                                                                                 | Status   |
| ------------------------------------------------------------- | ------------------------------------------------------------------------------------- | -------- |
| [0001](0001-on-demand-remediation-with-content-hash-cache.md) | Remediate on demand and cache artifacts by content hash                               | Proposed |
| [0002](0002-page-parallel-step-functions.md)                  | Page-parallel orchestration on Step Functions Distributed Map with Lambda and Fargate | Proposed |
| [0003](0003-pluggable-engine-pdfix-first.md)                  | Pluggable remediation engine; PDFix with veraPDF first, Adobe Auto-Tag second         | Proposed |
| [0004](0004-evidence-pack-as-unit-of-delivery.md)             | The signed, immutable evidence pack is the unit of delivery                           | Proposed |
| [0005](0005-html-first-output.md)                             | HTML first for text-heavy web documents; PDF/UA when it must remain a PDF             | Proposed |
| [0006](0006-aurora-postgresql-system-of-record.md)            | Aurora PostgreSQL as system of record with DynamoDB for pipeline state                | Proposed |
| [0007](0007-cognito-identity-with-federation.md)              | Cognito is the identity layer with per-tenant SAML/OIDC federation                    | Proposed |
| [0008](0008-pooled-multitenancy-with-tenant-keys.md)          | Pooled multi-tenancy with RLS, tenant-prefixed storage and tenant-scoped KMS keys     | Proposed |
| [0009](0009-marketing-site-static-export-on-s3-cloudfront.md) | Marketing site as a static Next.js export on S3 and CloudFront                        | Proposed |
| [0010](0010-multi-account-environments.md)                    | Separate AWS accounts for dev, staging and prod                                       | Proposed |
| [0011](0011-bedrock-model-strategy.md)                        | Claude models on Bedrock, configured by role, eval-gated                              | Proposed |

Template: the `spec-author` skill's ADR reference. Related PRDs live in `docs/*-PRD.md`; execution specs in `docs/*-SPECS.md`.
