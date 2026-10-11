# Microsoft 365 → Cognito prototype

ADR-0007 prototype 2. Can staff of a small office on Microsoft 365 sign in to our product with their work account, through Cognito, without an IT person setting up SAML?

**How it works:**

- We register one multi-tenant app in Microsoft Entra (Microsoft's sign-in service for work accounts).
- Each customer organization gets its own OIDC identity provider in Cognito, pointing at that organization's issuer (`login.microsoftonline.com/<tenant-id>/v2.0`). Only accounts from that organization can sign in through it.
- A user types their work email. We look up their organization from the domain (`scripts/discover_tenant.py`), and Cognito routes the sign-in by domain (`idp_identifier`).

The prototype reuses the Shibboleth prototype's throwaway Cognito pool, so apply `../shibboleth-cognito/terraform` first.

## What you need on the Microsoft side

Two Microsoft Entra tenants (organizations). They're free, and one test user per test is enough.

| Tenant | Plays the part of | Used for |
| --- | --- | --- |
| A | Make PDF Accessible | Holds our app registration |
| B | A small customer office | Its users sign in; we flip its "users may consent to apps" setting between tests |

For the first test, tenant A can also act as the customer. A second tenant is needed only for the consent tests. If you already have a Microsoft 365 business subscription, it can serve as either one. Otherwise, create a tenant from the [Microsoft Entra admin center](https://entra.microsoft.com) (**Identity → Overview → Manage tenants → Create**), signed in with any Microsoft account that has an Azure subscription.

### 1. Register the app (in tenant A)

In the Entra admin center: **Identity → Applications → App registrations → New registration**.

- **Name:** `Make PDF Accessible (prototype)`
- **Supported account types:** *Accounts in any organizational directory (Any Microsoft Entra ID tenant – Multitenant)*
- **Redirect URI:** platform *Web*, value `https://pdfa-shib-proto-403030.auth.us-east-1.amazoncognito.com/oauth2/idpresponse` (also printed by `terraform output entra_redirect_uri`)

Then:

1. **Token configuration → Add optional claim → ID → `email`**. This makes Microsoft include the user's email in the sign-in token when the user has one.
2. **Certificates & secrets → New client secret.** Six months is plenty.
3. Copy the **Application (client) ID** and the **Directory (tenant) ID** from the Overview page.

### 2. Store the client secret in AWS (you, not me)

In the AWS console for **pdf-accessibility-dev (403030570295)**, us-east-1: **Secrets Manager → Store a new secret → Other type of secret → Plaintext**.

- **Value:** the client secret's value, as is
- **Name:** `prototypes/entra-oidc/client-secret`

Terraform reads it from there, so it never goes in chat or in git. The secret costs $0.40 a month; delete it when the prototype is done.

### 3. Tell me the IDs

None of these are secrets:

- the Application (client) ID
- for each customer tenant: its tenant ID and its email domain (for example `contoso.onmicrosoft.com`)

I put them in `terraform/tenants.tfvars` (git-ignored) and apply:

```hcl
entra_client_id = "00000000-0000-0000-0000-000000000000"
microsoft_tenants = {
  m0001 = { tenant_id = "11111111-1111-1111-1111-111111111111", domains = ["contoso.onmicrosoft.com"] }
}
```

### 4. Sign in (you)

I can't sign in to Microsoft for you, so each test is one command, then a sign-in in your browser:

```bash
(cd terraform && AWS_PROFILE=pdf-dev terraform output -json > outputs.json)
python3 -I scripts/test_login.py alice@contoso.onmicrosoft.com
```

Open the URL it prints, sign in as the test user, and the result is saved to `results/`.

## Tests

| # | Test | Expect |
| --- | --- | --- |
| T1 | A user from tenant A signs in | Signed in. Token shows the email and the organization's issuer |
| T2 | A user from tenant B signs in, with user consent allowed in B | Microsoft asks the user to accept our app once, then signs them in |
| T3 | Same, with user consent blocked in B (Entra: **Enterprise apps → Consent and permissions → Do not allow user consent**) | User sees "Need admin approval". After the admin approves at `https://login.microsoftonline.com/<tenant-B>/adminconsent?client_id=<client-id>`, the user signs in |
| T4 | A personal address (`@outlook.com`) | Rejected before any sign-in (`discover_tenant.py`) |
| T5 | A tenant-A user tries tenant B's provider | Rejected by Cognito (issuer mismatch) |
| T6 | A user whose account has no mailbox | Token has no `email`; check what `preferred_username` carries |

Results go in [RESULTS.md](RESULTS.md).

## Clean up

```bash
(cd terraform && AWS_PROFILE=pdf-dev terraform destroy -var-file=tenants.tfvars)
```

Then delete the Secrets Manager secret and the app registration's client secret.
