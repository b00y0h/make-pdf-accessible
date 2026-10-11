"""Email-first Microsoft sign-in through Cognito, in your own browser.

Give it a work email address. It looks up the domain's Microsoft organization (rejecting personal
domains), builds a Cognito sign-in URL that routes by domain (idp_identifier), and waits on :8080
for the redirect. Then it saves the ID token's claims, or Cognito's error, to
results/login-<email>.json.

    python3 -I prototypes/microsoft-oidc-cognito/scripts/test_login.py alice@contoso.com
"""

import base64
import hashlib
import json
import secrets
import sys
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

# Isolated mode (-I) leaves the script's own folder off the import path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from discover_tenant import discover  # noqa: E402

HERE = Path(__file__).resolve().parent.parent
RESULTS = HERE / "results"

email = sys.argv[1]
email_domain = email.split("@")[-1].lower()
tenant = discover(email_domain)
print(json.dumps(tenant))
if tenant["status"] != "microsoft_organization":
    sys.exit(
        f"{email_domain} is not a Microsoft 365 organization ({tenant['status']}); no sign-in."
    )

OUTPUTS = json.loads((HERE / "terraform" / "outputs.json").read_text())
if "client_id" not in OUTPUTS:
    sys.exit(
        "Terraform hasn't created the Microsoft test app yet; finish README steps 1-3 first."
    )
DOMAIN = OUTPUTS["domain"]["value"]
CLIENT_ID = OUTPUTS["client_id"]["value"]
CALLBACK = OUTPUTS["callback_url"]["value"]

verifier = secrets.token_urlsafe(48)
challenge = (
    base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
    .rstrip(b"=")
    .decode()
)
state = secrets.token_urlsafe(16)
authorize_url = f"https://{DOMAIN}/oauth2/authorize?" + urllib.parse.urlencode(
    {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": CALLBACK,
        "scope": "openid email profile",
        "idp_identifier": email_domain,
        "login_hint": email,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": state,
    }
)


def exchange(code):
    body = urllib.parse.urlencode(
        {
            "grant_type": "authorization_code",
            "client_id": CLIENT_ID,
            "code": code,
            "redirect_uri": CALLBACK,
            "code_verifier": verifier,
        }
    ).encode()
    request = urllib.request.Request(
        f"https://{DOMAIN}/oauth2/token",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read())


class Callback(BaseHTTPRequestHandler):
    def do_GET(self):
        if not self.path.startswith("/callback"):
            self.send_response(404)
            self.end_headers()
            return
        query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        if "error" in query:
            result = {
                "outcome": "error",
                "error": query["error"][0],
                "error_description": query.get("error_description", [""])[0],
            }
        elif query.get("state", [""])[0] != state:
            result = {"outcome": "error", "error": "state mismatch"}
        else:
            id_token = exchange(query["code"][0])["id_token"]
            payload = id_token.split(".")[1]
            claims = json.loads(
                base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4))
            )
            result = {"outcome": "signed_in", "id_token_claims": claims}
        result = {"email": email, "tenant": tenant, **result}
        RESULTS.mkdir(exist_ok=True)
        (RESULTS / f"login-{email}.json").write_text(json.dumps(result, indent=2))
        page = json.dumps(result, indent=2).replace("&", "&amp;").replace("<", "&lt;")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(
            f"<!doctype html><title>Sign-in result</title><pre>{page}</pre>".encode()
        )
        print(json.dumps(result, indent=2))
        self.server.done = True

    def log_message(self, *args):
        pass


server = HTTPServer(("127.0.0.1", 8080), Callback)
server.done = False
print("Open this URL in your browser and sign in:\n" + authorize_url, flush=True)
while not server.done:
    server.handle_request()
