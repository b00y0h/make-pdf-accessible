"""Runs one complete sign-in, with no browser: our app -> Cognito -> test university -> Cognito -> app.

It follows the same redirects and form posts a browser would. It signs in to the local Shibboleth
as a test user from idp/credentials/test-users.txt, then reports what Cognito returned: an ID
token's claims or Cognito's error. It also saves the SAML request Cognito sent and the SAML
response the university returned, so the NameID format and attributes can be inspected.

    python3 -I prototypes/shibboleth-cognito/scripts/headless_login.py [user]
"""

import base64
import hashlib
import http.cookiejar
import json
import secrets
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
import zlib
from html.parser import HTMLParser
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
OUTPUTS = json.loads((HERE / "terraform" / "outputs.json").read_text())
DOMAIN = OUTPUTS["domain"]["value"]
CLIENT_ID = OUTPUTS["client_id"]["value"]
PROVIDER = OUTPUTS["provider_name"]["value"]
CALLBACK = OUTPUTS["callback_url"]["value"]
RESULTS = HERE / "results"
USERS = dict(
    line.split()
    for line in (HERE / "idp/credentials/test-users.txt").read_text().splitlines()
    if line.strip()
)

# The local IdP uses a self-signed certificate; verify every other host normally.
LOCAL_CONTEXT = ssl.create_default_context()
LOCAL_CONTEXT.check_hostname = False
LOCAL_CONTEXT.verify_mode = ssl.CERT_NONE


class Form(HTMLParser):
    """Collects the first form on a page: its action and its input values."""

    def __init__(self):
        super().__init__()
        self.action, self.fields, self.in_form, self.done = None, {}, False, False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "form" and not self.done:
            self.action, self.in_form = a.get("action"), True
        elif tag in ("input", "button") and self.in_form and a.get("name"):
            if a.get("type") in ("checkbox", "radio") and "checked" not in a:
                return
            self.fields.setdefault(a["name"], a.get("value", ""))

    def handle_endtag(self, tag):
        if tag == "form" and self.in_form:
            self.in_form, self.done = False, True


class CallbackReached(Exception):
    def __init__(self, url):
        self.url = url


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """Hands every redirect back to fetch(), which follows it itself."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


jar = http.cookiejar.CookieJar()


def fetch(url, data=None):
    """Follows redirects across hosts (switching TLS verification per host) until a page or the callback."""
    while True:
        request = urllib.request.Request(
            url, data=urllib.parse.urlencode(data).encode() if data else None
        )
        context = (
            LOCAL_CONTEXT
            if urllib.parse.urlparse(url).hostname == "localhost"
            else ssl.create_default_context()
        )
        opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(jar),
            urllib.request.HTTPSHandler(context=context),
            NoRedirect(),
        )
        try:
            response = opener.open(request, timeout=30)
            return response.geturl(), response.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code in (301, 302, 303, 307):
                location = urllib.parse.urljoin(url, e.headers["Location"])
                if location.startswith(CALLBACK):
                    raise CallbackReached(location) from None
                url, data = location, None
                continue
            return url, e.read().decode("utf-8", "replace")


def saml_request_from(url):
    query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    if "SAMLRequest" not in query:
        return None
    return zlib.decompress(base64.b64decode(query["SAMLRequest"][0]), -15).decode()


def main():
    user = sys.argv[1] if len(sys.argv) > 1 else "alice"
    verifier = secrets.token_urlsafe(48)
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
        .rstrip(b"=")
        .decode()
    )
    state = secrets.token_urlsafe(16)
    url = f"https://{DOMAIN}/oauth2/authorize?" + urllib.parse.urlencode(
        {
            "response_type": "code",
            "client_id": CLIENT_ID,
            "redirect_uri": CALLBACK,
            "scope": "openid email profile",
            "identity_provider": PROVIDER,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "state": state,
        }
    )
    trace = {"user": user}
    RESULTS.mkdir(exist_ok=True)

    try:
        # Cognito redirects to the IdP with a SAML AuthnRequest; capture it before following.
        authorize = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(jar), NoRedirect()
        )
        try:
            authorize.open(url, timeout=30)
            raise SystemExit("Cognito did not redirect to the identity provider")
        except urllib.error.HTTPError as e:
            idp_url = urllib.parse.urljoin(url, e.headers["Location"])
        trace["saml_request"] = saml_request_from(idp_url)

        page_url, page = fetch(idp_url)
        for _ in range(6):
            form = Form()
            form.feed(page)
            if form.action is None:
                break
            action = urllib.parse.urljoin(page_url, form.action)
            fields = dict(form.fields)
            if "SAMLResponse" in fields:
                trace["saml_response"] = base64.b64decode(
                    fields["SAMLResponse"]
                ).decode("utf-8", "replace")
            elif "j_username" in fields:
                fields.update(
                    {
                        "j_username": user,
                        "j_password": USERS[user],
                        "_eventId_proceed": "",
                    }
                )
            elif any(k.startswith("shib_idp_ls") for k in fields):
                fields["shib_idp_ls_supported"] = "false"
                fields.setdefault("_eventId_proceed", "")
            page_url, page = fetch(action, fields)
        result = {
            "outcome": "no_callback",
            "last_url": page_url,
            "last_page": page[:2000],
        }
    except CallbackReached as reached:
        query = urllib.parse.parse_qs(urllib.parse.urlparse(reached.url).query)
        if "error" in query:
            result = {
                "outcome": "error",
                "error": query["error"][0],
                "error_description": query.get("error_description", [""])[0],
            }
        else:
            body = urllib.parse.urlencode(
                {
                    "grant_type": "authorization_code",
                    "client_id": CLIENT_ID,
                    "code": query["code"][0],
                    "redirect_uri": CALLBACK,
                    "code_verifier": verifier,
                }
            ).encode()
            request = urllib.request.Request(
                f"https://{DOMAIN}/oauth2/token",
                data=body,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            tokens = json.loads(urllib.request.urlopen(request, timeout=30).read())
            payload = tokens["id_token"].split(".")[1]
            claims = json.loads(
                base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4))
            )
            result = {"outcome": "signed_in", "id_token_claims": claims}

    trace.update(result)
    (RESULTS / f"login-{user}.json").write_text(json.dumps(trace, indent=2))
    summary = {
        k: v
        for k, v in trace.items()
        if k not in ("saml_request", "saml_response", "last_page")
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
