# Shibboleth → Cognito prototype: results

Run on 10 October 2026 for ADR-0007. The IdP was stock Shibboleth IdP 5.2.3 (InCommon's `i2incommon/shib-idp:5.2.3_20260824_rocky9_multiarch` image), configured as any campus would configure it for a new service. The service provider was a throwaway Cognito user pool on the Essentials plan in the dev account (`us-east-1_DDXQXgBr6`). Every pass ran end to end with `scripts/headless_login.py`: app → Cognito → Shibboleth sign-in → Cognito → tokens.

## Summary

| Pass | Setup | Result |
| --- | --- | --- |
| 1 | Stock Shibboleth defaults (transient NameID) | **Fails.** Cognito: `Invalid SAML response received: 1 validation error detected: Value at 'userName' failed to satisfy constraint: Member must have length less than or equal to 128` |
| 2 | Campus enables persistent IDs; our SP metadata lists the persistent format | **Works.** Stable user per person, email and eduPersonPrincipalName mapped |
| 3a | Encrypted assertions with Shibboleth's default AES-128-GCM | **Fails.** Cognito: `Invalid SAML response received: No SAML assertion found in the SAML response.` |
| 3b | Encrypted assertions; our SP metadata advertises AES-CBC | **Works.** Shibboleth used AES-256-CBC with RSA-OAEP, and Cognito decrypted it |

## What we learned

1. **Cognito doesn't ask for a NameID format.** Its AuthnRequest has no `NameIDPolicy`, which contradicts the community report cited in the identity research. The IdP therefore falls back to its own default.
2. **A campus on Shibboleth's defaults can't sign in.** The default transient NameID is a 160-character encrypted value. Cognito names the user `<ProviderName>_<NameID>` (175 characters here), which exceeds Cognito's 128-character username limit. Even a shorter transient ID would create a new user on every sign-in.
3. **The fix is a persistent NameID.** With computed persistent IDs (`idp.persistentId.sourceAttribute = uid` plus a salt) and `NameIDFormat persistent` in our SP metadata, the username is `TestUniversity_` plus a 32-character ID. Repeat sign-ins map to the same Cognito user (same `sub`), and a second user gets their own. Many campuses already issue persistent or pairwise IDs to other services, so we expect this to be a routine onboarding request (judgment, not tested).
4. **Attributes map cleanly by OID.** `mail` (`urn:oid:0.9.2342.19200300.100.1.3`) mapped to `email`, and `eduPersonPrincipalName` (`urn:oid:1.3.6.1.4.1.5923.1.1.1.6`) to `preferred_username`. The campus has to release them to us with an attribute-filter rule.
5. **Cognito didn't decrypt AES-GCM.** Tested on 10 October 2026, both with RSA-OAEP (`rsa-oaep-mgf1p`) key transport: `aes128-gcm` failed and `aes256-cbc` worked. GCM is Shibboleth 5's default (`idp.encryption.config = shibboleth.EncryptionConfiguration.GCM`); CBC is the older mode Shibboleth moved away from. When our SP metadata lists AES-CBC `EncryptionMethod`s next to Cognito's encryption certificate, Shibboleth picks CBC and sign-in works with no campus-side change. Some campus security teams may prefer turning encryption off for us instead (assertions are still signed and travel over TLS), so the setup guide should offer both choices.
6. **Cognito publishes no SP metadata.** `/saml2/metadata` on the hosted domain and the obvious `cognito-idp` URLs all return 404 or 400. We must generate and host our own SP metadata per pool: entity ID `urn:amazon:cognito:sp:<pool-id>`, ACS `https://<domain>/saml2/idpresponse`, NameIDFormat persistent, Cognito's encryption certificate with CBC methods, and the signing certificate (from `GetSigningCertificate`) if we sign requests.
7. **Federated users arrive with `email_verified: false`.** The app must not rely on that flag for SSO users. Trust comes from the verified domain bound to the identity provider (ADR-0007 change 4).
8. **Cognito accepted IdP metadata whose endpoints are on `localhost`**, which makes local testing easy.
9. **Tenant provider names must be short.** Cognito's username is `<ProviderName>_<NameID>`, capped at 128 characters. Name each tenant's identity provider with a short code (for example `t0042`), not the institution's name, so a long persistent ID from a campus still fits.

## What this means for ADR-0007

- **Core campus sign-in passes**, with two onboarding requirements to put in the ADR and the campus setup guide: issue persistent NameIDs to us, and release `mail` and `eduPersonPrincipalName`. The rest of prototype 1 (IdP-initiated sign-in, signed requests, certificate rollover) is still untested, and prototype 2 (Microsoft) hasn't started.
- Our generated SP metadata must request persistent NameIDs and advertise AES-CBC.
- Two of the research's unverified items are now settled: Cognito doesn't publish SP metadata, and Cognito didn't decrypt AES-GCM. The research's claim that Cognito requests a persistent NameID with `AllowCreate="false"` is wrong: Cognito sends no NameID policy.

## Not tested yet

- Signed AuthnRequests (Cognito's `RequestSigningAlgorithm`)
- IdP-initiated sign-in
- Signing-certificate rollover
- Single logout
- Prototype 2: Microsoft 365 per-tenant OIDC
