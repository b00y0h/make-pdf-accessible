# Migrate from Cognito → BetterAuth

## Remove Cognito (code & infra)
- [ ] Delete Cognito usage in `web/` (Hosted UI redirects, token storage, axios interceptor)
- [ ] Remove Cognito JWT verification from `services/api/app/auth.py`
- [ ] Terraform: remove Cognito User Pool/App Client/Domain & related IAM bits
- [ ] No Cognito envs or references remain

## Add BetterAuth to `dashboard/` (server + client)
- [ ] Install packages: `pnpm add better-auth @better-auth/cli better-auth/client`
- [ ] Create `lib/auth.ts` with BetterAuth config
  - [ ] Enable email/password login
  - [ ] Add `username` plugin
  - [ ] Configure social providers: Google, Apple, GitHub, Discord
  - [ ] Database: SQLite in dev, Postgres in prod
- [ ] Add `app/api/auth/[...all]/route.ts` → `toNextJsHandler(auth.handler)`
- [ ] Add `lib/auth-client.ts` (signIn/signUp/social/session/signOut helpers)
- [ ] Add middleware to protect `/dashboard`, `/queue`, `/documents`, `/reports`, `/settings`
- [ ] Add `/sign-in` and `/sign-up` pages with forms + social buttons
- [ ] Add user menu with session info + sign-out
- [ ] Configure `.env.local` with secrets for all providers
- [ ] Users can sign in/out with email/password and social providers; session visible via `useSession`

## Issue short-lived API JWTs for Python API
- [ ] Add `app/api/auth/token/route.ts` in Next.js: mint 5–10m API JWT
- [ ] Sign with `API_JWT_SECRET`; claims: sub, email, roles, orgId
- [ ] Axios interceptor: fetch token if missing/expired
- [ ] FastAPI: replace Cognito verifier with HMAC/JWK validator
- [ ] API accepts valid JWTs; rejects missing/expired tokens

## Database for BetterAuth
- [ ] Dev: SQLite file
- [ ] Prod: RDS/Aurora Postgres via Terraform
- [ ] Store `AUTH_DATABASE_URL` in SSM/Secrets Manager
- [ ] Run `npx @better-auth/cli migrate` to create tables
- [ ] BetterAuth schema created and migrations applied

## UI/UX updates
- [ ] Replace Cognito login UI with BetterAuth sign-in/sign-up
- [ ] Add username field to Profile/Settings
- [ ] Ensure accessible labels, keyboard focus, and error messages
- [ ] Sign-in/out UX smooth and accessible

## CI/CD & runtime config
- [ ] GitHub Actions: run BetterAuth migrations in deploy pipeline
- [ ] Store provider secrets in SSM/Secrets Manager
- [ ] Runtime config JSON: remove Cognito entries, add `/api/auth/token` path
- [ ] Deploy pipeline fully automated with DB migrations

## Security & hardening
- [ ] Configure cookies: HttpOnly, Secure, SameSite=strict
- [ ] Short TTL for API JWTs (≤10m)
- [ ] Rotate `API_JWT_SECRET` regularly
- [ ] Enforce `aud`, `iss`, and `exp` checks in API
- [ ] No tokens in localStorage; secure session + JWT handling

## Code skeletons to generate
- [ ] `web/lib/auth.ts` → BetterAuth config
- [ ] `web/app/api/auth/[...all]/route.ts` → handler
- [ ] `web/lib/auth-client.ts` → client helpers
- [ ] `web/middleware.ts` → route guards
- [ ] `web/app/api/auth/token/route.ts` → API JWT minting
- [ ] `services/api/app/auth.py` → JWT verification logic
- [ ] Terraform: remove Cognito, add Postgres + secrets
- [ ] Script: `pnpm better-auth:migrate`

## Acceptance tests
- [ ] Playwright
  - [ ] Email/password sign-up/sign-in → protected page
  - [ ] Social sign-in (GitHub) with test creds
  - [ ] Verify `/api/auth/token` returns token
- [ ] PyTest (API)
  - [ ] Missing/invalid JWT → 401
  - [ ] Expired JWT → 401
  - [ ] Role enforcement works
- [ ] End-to-end auth & API tests pass
