# Microsoft 365 → Cognito prototype: results

In progress. Started 10 October 2026 for ADR-0007.

## Done without a Microsoft tenant

**Tenant discovery from an email domain works, but must reject personal domains explicitly** (`scripts/discover_tenant.py`, checked 2026-10-10 against Microsoft's public discovery endpoint):

| Domain | Result |
| --- | --- |
| `microsoft.com` | Organization `72f988bf-…`, issuer `login.microsoftonline.com/72f988bf-…/v2.0` |
| `asu.edu` | Organization `41f88ecb-…` (region scope NA) |
| `outlook.com` | Resolves to `f8cdef31-…`, Microsoft's own tenant, not a customer. A naive lookup would make every personal Outlook user one "organization". Rejected by name and by tenant ID |
| `example.edu`, `reversetype.dev`, `makepdfaccessible.com` | `invalid_tenant`: no Microsoft organization |

Cognito side: `terraform/` is ready and validated. It creates one OIDC provider per customer organization, keyed by a short code, with that organization's issuer and its domains as `idp_identifiers`. It creates nothing until the Microsoft app registration exists.

## Waiting on the Microsoft side

T1–T6 in [README.md](README.md) need two Entra tenants and an app registration (README steps 1–3).
