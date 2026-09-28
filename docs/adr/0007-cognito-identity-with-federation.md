# ADR-0007: Amazon Cognito is the identity layer, with per-tenant SAML and OIDC federation; BetterAuth is retired

- **Status:** Proposed
- **Date:** 2026-09-28
- **Deciders:** Founder (product and engineering)
- **Scope:** Authentication and authorization for dashboard, API and LTI tool
- **Related:** `docs/ENTERPRISE-READINESS-PRD.md`, ADR-0008

## Context

Three identity systems coexist: BetterAuth in the dashboard (`dashboard/src/lib/auth-server.ts`, Prisma tables, HS256 JWTs validated by the API), a Cognito user pool with Google and SAML providers in Terraform (`infra/terraform/cognito.tf`) used by the worker's JWT code, and our own API keys. The gap report calls this inconsistency a security risk. Higher-education buyers require SSO through their campus identity provider: SAML 2.0 via InCommon/Shibboleth is the norm, Microsoft Entra ID and Google Workspace are common. They also expect MFA for local accounts and to enforce SSO for their email domain.

Constraints: small team; no appetite to run an identity server; the LTI 1.3 tool needs its own OIDC flows with LMS platforms; API keys must keep working.

## Decision

We will use one Cognito user pool per environment as the sole human identity provider: hosted UI with OIDC and PKCE for the dashboard, identifier-first login by email domain, per-tenant SAML or OIDC identity providers created through our API from the customer's metadata, TOTP MFA for non-federated privileged users, and RS256 JWTs validated in the API from the pool's JWKS. BetterAuth, its migrations and its HS256 secret are removed. API keys and connector keys stay ours (hashed, scoped, tenant-bound). The LTI tool implements LTI 1.3 OIDC separately because the LMS is the identity provider in that flow.

## Alternatives Considered

- **Keep BetterAuth and add SAML through a plugin** — Puts SAML, metadata handling and key rotation on a small team; no hosted UI or MFA story comparable to Cognito; the API would keep trusting an HS256 shared secret.
- **Auth0 or Okta CIC** — Strong SAML support, but per-MAU pricing scales badly with campus-wide JIT users and adds a vendor to the compliance program.
- **Cognito plus BetterAuth as a session layer** — Two systems again; the dashboard can hold Cognito tokens directly.
- **Keycloak self-hosted** — Full control, full operational burden.

## Consequences

**Positive**

- SAML and OIDC federation, MFA and hosted UI without running an identity server; AWS-native audit and IAM integration; one token format for all services.

**Negative / Trade-offs**

- Cognito's SAML implementation has rough edges (metadata refresh, attribute mapping, limited customization of the hosted UI); the dashboard's auth code is rewritten.
- Cognito user pool quotas (identity providers per pool) may require pool sharding at hundreds of tenants.

**Neutral / Follow-ups**

- Test with an InCommon-style Shibboleth IdP and an Entra ID tenant before slice E2 is called done.
- Document the pool-per-region strategy when the second region is added.
