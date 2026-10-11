# Identity for a B2B SaaS serving organizations of every size

Research for ADR-0007 (on hold), compiled 10 October 2026 from official documentation and pricing pages. **UNV** marks claims that could not be confirmed on an official page. Prices are list prices on that date. Prototype 1 (`prototypes/shibboleth-cognito/RESULTS.md`) tested the SAML claims against a stock Shibboleth IdP the same day; corrections from it are marked **Tested**.

The owner's brief: identity must be flexible and scalable, and workable for every kind of customer, from a 3-person office with Google or Microsoft accounts and no identity administrator, to universities and enterprises that require SAML, SCIM and enforced SSO.

## Recommendation

**Keep Cognito, but give it a narrower job. Own the B2B layer, and buy SCIM per deal.**

- **Cognito (Essentials plan)** issues tokens and brokers SAML and OIDC federation.
- **Our own Postgres tables** hold organizations, memberships, DNS-verified domains, and SSO policy and enforcement.
- **WorkOS Directory Sync** provides SCIM, bought only for contracts that require it.
- Accept the ADR only after prototypes 1 and 2 below pass.

Why:

- **Quotas don't block it.** A user pool takes 300 identity providers by default, adjustable to a hard limit of 1,000. App clients and pools per Region go up to 10,000.
- **It's the cheapest option with a workable B2B federation model.** 50,000 federated campus users cost about $750 a month, against about $4,000–5,000 on WorkOS and about $3,300 on Clerk. Self-serve users of small offices fit within Cognito's 10,000 free direct and social monthly active users.
- **Per-connection pricing hurts the Team plan.** At $125 a month per SSO connection, one connection is $1,500 a year, a quarter of a $6,000 Team contract. With Cognito, SSO can be part of every paid plan.
- **The cost is build time.** About 4–6 engineer-weeks for organizations, domain verification, enforcement, `/settings/sso` and the Microsoft workaround. For comparison, WorkOS would cost about $550–650 a month more than Cognito at 5 campuses, and $3,400–4,400 more at 50.
- **Switching vendors doesn't remove the hardest small-office gap.** WorkOS's Microsoft OAuth guide registers for "Personal Microsoft accounts only".

**Keep it reversible.** The API trusts an allow-list of issuers, and tenant and role always come from Postgres, never from token claims. Revisit the choice, most likely toward WorkOS or Clerk as the whole layer, if any of these happens:

- the Shibboleth prototype fails;
- a pool passes 700 identity providers;
- more than 10 customers need SCIM;
- SAML support takes more than about a day a week.

## Options compared

Costs are monthly. Scenario (a): 50 institutions with 50,000 monthly active users, mostly federated. Scenario (b): 500 small companies with 5,000 monthly active users, mostly email, password or social.

| Option | B2B fit | SSO and SCIM | Small-office onboarding | (a) | (b) | Ops | Lock-in, AWS Marketplace |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **Cognito Essentials + our org layer + WorkOS Directory Sync** | We build it | Up to 1,000 IdPs per pool; SCIM $125, falling to $65, per connection | Email, passkeys, one-time codes and Google natively; Microsoft work accounts need a workaround | ~$750, plus $125 per SCIM customer | ~$0 (~$30 if Microsoft users federate) | Medium | No password-hash export; SP entity ID tied to the pool; AWS-native |
| WorkOS AuthKit, replacing Cognito | Strong: orgs, DNS verification, free unbranded admin portal | $125, falling to $65, per connection, each for SSO and SCIM | Microsoft "personal accounts only" per its docs | ~$4,100–5,100 | ~$0, plus $125 per SSO customer | Low | Hash export UNV; Marketplace $30k/yr for 20 connections |
| Auth0 B2B | Strong: Organizations, self-service SSO, inbound SCIM | 3–5 connections included, $100 each after, cap of 30, then Enterprise | Microsoft through the common endpoint | Enterprise quote (UNV) | From $150 (price at 5k users UNV) | Low | Hashes via support; Marketplace $40,250/yr (10k users, 5 connections) |
| Clerk | Good; verified domains are a $100 add-on | $75, falling to $60, per connection; SCIM billed from 2027 | Microsoft multi-tenant | ~$3,300 | ~$425–525 | Low | CSV export includes hashes; not on Marketplace |
| Stytch B2B | Good | 5 connections free, then $125 each | UNV | ~$9,600 (per-user rate from Marketplace) | ~$0 | Low | Hashes via support; Marketplace $25k/yr |
| Entra External ID | Weak: no organization object | SAML and WS-Fed; inbound SCIM UNV | Microsoft | ~$0 up to 50k users (UNV above) | $0 | Medium | Azure |
| Keycloak 26, FusionAuth, Zitadel or Ory, self-hosted | Keycloak has Organizations and realm-level SCIM (26.8) | Unlimited | We build it | Infrastructure plus on-call | Infrastructure | High | Low |

**Rejected hybrid: WorkOS's Cognito integration.**

- It's in preview.
- It creates one Cognito identity provider per connection, so the quota still applies.
- Both vendors bill.
- It requires granting `cognito-idp:*` cross-account to WorkOS, which wouldn't survive a HECVAT review.

## Changes ADR-0007 would need

1. **Title:** Cognito (Essentials) issues tokens and brokers federation; organizations, domains and SSO policy live in our database; SCIM is bought per deal.
2. **Plan tier:**
   - `infra/terraform/cognito.tf` sets `advanced_security_mode = "ENFORCED"`, which requires the Plus plan ($0.020 per user, no free tier).
   - Use Essentials unless password users justify threat protection.
3. **Tenancy:**
   - Store no tenant attribute in Cognito, because memberships are many-to-many.
   - The API resolves the active tenant against `memberships` on each request, then sets `app.tenant_id` per transaction (ADR-0008).
   - Replace `users.cognito_sub` with `user_identities(user_id, issuer, subject)`.
   - Don't use `AdminLinkProviderForUser`: it caps at 5 links and bills as an enterprise user.
4. **Domains:**
   - A DNS TXT record must prove ownership before a domain routes to an identity provider, auto-joins users, or enforces SSO.
   - Reject consumer domains.
   - Bind Microsoft customers by tenant ID (`tid`), not email.
5. **Enforced SSO:**
   - The pre sign-up trigger denies local and social sign-up on enforced domains.
   - `identities` appears only in the ID token, so a V2 pre-token trigger adds an `idp` claim to access tokens.
   - The API rejects tokens whose `idp` doesn't match.
   - Keep one break-glass owner protected by a passkey or TOTP.
6. **SAML profile:**
   - Cognito keys users on NameID, naming each user `<ProviderName>_<NameID>` with a 128-character cap. **Tested:** contrary to a community report, Cognito's AuthnRequest has no NameID policy at all, so a campus on Shibboleth's defaults sends a 160-character transient ID and the sign-in fails. Our SP metadata must request `persistent`, and the campus must issue persistent IDs to us. Keep tenant provider names short (a tenant code) so long persistent IDs still fit.
   - Ship attribute-mapping presets for InCommon attribute OIDs.
   - Use metadata URLs, which Cognito caches for 6 hours.
   - Sign AuthnRequests; assertion encryption is optional, with a key per identity provider. **Tested:** Cognito didn't decrypt AES-128-GCM (Shibboleth 5's default) and did decrypt AES-256-CBC, so our SP metadata advertises CBC `EncryptionMethod`s. Campuses can also turn encryption off for us.
   - **Tested:** Cognito publishes no SP metadata, so we generate and host our own per pool.
7. **Deprovisioning without SCIM:** refresh tokens last at most one day for SSO tenants (`cognito.tf` sets 30 days today), and sessions are revoked when a membership is removed.
8. **Small offices and K-12:**
   - Email and password with TOTP or passkeys, email one-time codes, and Google all work natively.
   - Microsoft work accounts: prototype one Entra OIDC identity provider per customer, using our multi-tenant app with a tenant-specific issuer, discovered from the email domain and passed as `idp_identifier` from our own email-first sign-in page. Those users bill as federated users and count toward the identity-provider cap.
   - Clever is OIDC: one identity provider per district. Its portal-initiated sign-ins arrive without `state`, so they need a landing route that restarts the flow.
   - ClassLink is SAML.
9. **SCIM:** v1 relies on just-in-time provisioning plus SSO-only access. When a contract requires SCIM, standalone WorkOS Directory Sync (API key and Events API) writes into `memberships`. Build our own at about 10 SCIM customers.
10. **Quotas and exit:**
    - Request 1,000 identity providers per pool at launch, and shard at 700.
    - Only 4 custom domains per Region per account.
    - Moving a tenant to another pool changes its SP entity ID, so the campus has to re-establish trust.
    - Leaving Cognito means a lazy migration, because password hashes can't be exported.
11. **Alternatives:** update Auth0 (it now has B2B Organizations, SCIM and a 30-connection cap), and add WorkOS, Clerk, Stytch and Entra External ID.
12. **Follow-ups:**
    - Multi-Region replication is for disaster recovery, not data residency, because it copies user data. Residency needs a pool per Region.
    - LTI launches never create Cognito users.

## Prototype first (about two weeks)

1. **Stock Shibboleth IdP v5 in Docker**, against Cognito and against WorkOS staging. Test:
   - transient NameID, Shibboleth's default
   - `AllowCreate`
   - OID attribute names
   - AES-GCM assertion encryption (**tested:** not supported; CBC works)
   - IdP-initiated sign-in
   - certificate rollover
2. **Microsoft per-tenant OIDC** with a 3-person Microsoft 365 tenant, once with user consent allowed and once with it blocked.
3. **Domain verification and SSO enforcement**, end to end.
4. **WorkOS Directory Sync** into `memberships`, with Okta and Entra test directories.

## Risks

- **InCommon registration.** Some campuses may want an InCommon-registered service provider. That costs $700 once plus $2,500 a year and needs a sponsoring institution; whether a URN entity ID is accepted is UNV. Bilateral trust is common: Stanford lists most of its service providers as non-InCommon.
- **No metadata aggregate support.** No vendor consumes the InCommon aggregate or its per-entity metadata service, so each institution is set up individually.
- **SAML support load** falls on us without an admin portal.
- **Sign-in path:** Lambda triggers sit on it.
- **Subprocessor:** WorkOS joins the FERPA and HECVAT subprocessor lists.
- **Also UNV:** whether WorkOS's volume tiers are graduated. (Cognito publishing SP metadata was tested: it doesn't.)

## Sources

All fetched 10 October 2026.

**Cognito:**

- [Quotas](https://docs.aws.amazon.com/cognito/latest/developerguide/quotas.html)
- [Pricing](https://aws.amazon.com/cognito/pricing/)
- [Feature plans](https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-sign-in-feature-plans.html)
- [SAML things to know](https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools-saml-idp-things-to-know.html)
- [SAML session initiation](https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools-SAML-session-initiation.html)
- [SAML signing and encryption](https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools-SAML-signing-encryption.html)
- [Attribute mapping](https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools-specifying-attribute-mapping.html)
- [Pre-token trigger](https://docs.aws.amazon.com/cognito/latest/developerguide/user-pool-lambda-pre-token-generation.html)
- [Pre sign-up trigger](https://docs.aws.amazon.com/cognito/latest/developerguide/user-pool-lambda-pre-sign-up.html)
- [Multi-tenancy](https://docs.aws.amazon.com/cognito/latest/developerguide/multi-tenancy-security-recommendations.html)
- [Social providers](https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools-social-idp.html)
- [Multi-Region](https://docs.aws.amazon.com/cognito/latest/developerguide/user-pool-multi-region.html)
- [SaaS Lens](https://docs.aws.amazon.com/wellarchitected/latest/saas-lens/identity-and-access-management.html)

**Community reports:**

- [Entra `common` issuer mismatch](https://learn.microsoft.com/en-us/answers/questions/2285623/configure-sso-with-aws-cognito-for-multi-tenant-si)
- [NameID policy](https://www.repost.aws/questions/QUbLK6JDDlQhCZkYQDoyRRzQ/saml-shibboleth-nameidpolicy-error)

**Vendors:**

- WorkOS:
  - [pricing](https://workos.com/pricing)
  - [admin portal](https://workos.com/admin-portal)
  - [Microsoft OAuth](https://workos.com/docs/integrations/microsoft-oauth)
  - [Cognito integration](https://workos.com/docs/integrations/aws-cognito)
  - [Directory Sync](https://workos.com/docs/directory-sync/quick-start)
  - [Marketplace](https://aws.amazon.com/marketplace/pp/prodview-a5556eloilfuu)
- Auth0: [pricing](https://auth0.com/pricing), [Marketplace](https://aws.amazon.com/marketplace/pp/prodview-zuzf7ue36wzly)
- Clerk: [pricing](https://clerk.com/pricing), [Microsoft](https://clerk.com/docs/authentication/social-connections/microsoft)
- Stytch: [pricing](https://stytch.com/pricing), [Marketplace](https://aws.amazon.com/marketplace/pp/prodview-mk7ac2kpntwec)
- Entra External ID: [pricing](https://www.microsoft.com/en-us/security/pricing/microsoft-entra-external-id), [features](https://learn.microsoft.com/en-us/entra/external-id/customers/concept-supported-features-customers)
- [Keycloak 26.8](https://www.keycloak.org/2026/10/keycloak-2680-released)
- [FusionAuth pricing](https://fusionauth.io/pricing)

**Higher education and K-12:**

- [InCommon fees](https://incommon.org/federation/fees)
- [InCommon sponsored partners](https://incommon.org/join-incommon/sponsored-partners)
- [Stanford service-provider onboarding](https://uit.stanford.edu/service/saml/onboard-service-provider)
- [Shibboleth GCM encryption](https://shibboleth.atlassian.net/wiki/spaces/IDP5/pages/3199501202/GCMEncryption)
- [Shibboleth knowledge base on Cognito (2019)](https://shibboleth.atlassian.net/wiki/spaces/KB/pages/1429930512/AmazonCognito)
- [Clever](https://dev.clever.com/docs/oauth-implementation)
