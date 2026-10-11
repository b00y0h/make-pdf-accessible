"""Finds which Microsoft organization (Entra tenant) an email domain belongs to.

This is the first step of email-first sign-in for small offices on Microsoft 365. The user types
an email address; we look up the domain's tenant, and the sign-in goes to that tenant's own
identity provider in Cognito. Microsoft's discovery endpoint is public and needs no sign-in.

Personal Microsoft domains (outlook.com and the like) resolve to Microsoft's own tenants, not to
the user's organization, so they are rejected by name and by tenant ID.

    python3 -I prototypes/microsoft-oidc-cognito/scripts/discover_tenant.py contoso.com [...]
"""

import json
import sys
import urllib.error
import urllib.request

# Tenants that hold personal Microsoft accounts or Microsoft's consumer domains, never a customer.
CONSUMER_TENANTS = {
    "9188040d-6c67-4c5b-b112-36a304b66dad",  # personal Microsoft accounts (MSA)
    "f8cdef31-a31e-4b4a-93e4-5f571e91255a",  # Microsoft Services, owner of outlook.com and similar
}
CONSUMER_DOMAINS = {
    "outlook.com",
    "hotmail.com",
    "live.com",
    "msn.com",
    "passport.com",
    "windowslive.com",
    "gmail.com",
    "googlemail.com",
    "yahoo.com",
    "icloud.com",
    "me.com",
    "aol.com",
    "proton.me",
    "protonmail.com",
}


def discover(domain):
    domain = domain.strip().lower()
    if domain in CONSUMER_DOMAINS:
        return {"domain": domain, "status": "consumer_domain"}
    url = f"https://login.microsoftonline.com/{domain}/v2.0/.well-known/openid-configuration"
    try:
        with urllib.request.urlopen(url, timeout=15) as response:
            config = json.loads(response.read())
    except urllib.error.HTTPError as e:
        body = json.loads(e.read() or b"{}")
        return {
            "domain": domain,
            "status": "not_microsoft",
            "error": body.get("error", str(e.code)),
        }
    issuer = config["issuer"]
    tenant_id = issuer.split("/")[3]
    if tenant_id in CONSUMER_TENANTS:
        return {"domain": domain, "status": "consumer_tenant", "tenant_id": tenant_id}
    return {
        "domain": domain,
        "status": "microsoft_organization",
        "tenant_id": tenant_id,
        "issuer": issuer,
        "region_scope": config.get("tenant_region_scope"),
    }


if __name__ == "__main__":
    for d in sys.argv[1:] or ["microsoft.com"]:
        print(json.dumps(discover(d)))
