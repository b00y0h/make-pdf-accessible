# Shibboleth → Cognito prototype

Tests whether a university running stock Shibboleth can sign in to our product through Amazon Cognito (ADR-0007, prototype 1). A Shibboleth IdP runs on this Mac in Docker as a test university. A throwaway Cognito user pool runs in the dev AWS account; Cognito has no local version. Findings are in [RESULTS.md](RESULTS.md).

## Pieces

| Path | What it is |
| --- | --- |
| `docker-compose.yml` | Shibboleth IdP 5.2.3 (InCommon's image) at `https://localhost:8443/idp/` |
| `idp/conf/` | Stock IdP config with only campus-style changes, each marked `Prototype` |
| `idp/nameid-formats.txt` | NameID formats the IdP's metadata advertises |
| `scripts/setup-idp.sh` | Generates fresh IdP keys, test users (`alice`, `bob`) and IdP metadata |
| `terraform/` | The Cognito test pool, domain, SAML provider and test app client |
| `scripts/render-sp-metadata.sh` | Writes Cognito's SP metadata for the IdP from Terraform outputs |
| `scripts/headless_login.py` | Runs a full sign-in without a browser and saves the SAML messages and tokens |
| `scripts/test_login.py` | The same sign-in in your own browser, with a callback server on `:8080` |

Generated files (keys, test-user passwords, metadata, results) are git-ignored. Test passwords are in `idp/credentials/test-users.txt`.

## Run it

```bash
cd prototypes/shibboleth-cognito
scripts/setup-idp.sh
(cd terraform && AWS_PROFILE=pdf-dev terraform init && AWS_PROFILE=pdf-dev terraform apply)
AWS_PROFILE=pdf-dev scripts/render-sp-metadata.sh
docker compose -p shib-proto up -d
python3 -I scripts/headless_login.py alice
```

To try it in a browser, run `python3 -I scripts/test_login.py`, open the URL it prints, accept the IdP's self-signed certificate, and sign in as `alice`. (Untested so far: the prototype's passes ran headless.)

## Clean up

```bash
docker compose -p shib-proto down
(cd terraform && AWS_PROFILE=pdf-dev terraform destroy)
```

The pool costs nothing at a handful of users. Its Terraform state lives in the dev state bucket under `prototypes/shibboleth-cognito/`.
