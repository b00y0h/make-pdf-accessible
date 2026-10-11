"""Signs in through Cognito with the test university and prints what Cognito hands our app.

Starts a local callback server on :8080, prints the sign-in URL (open it in a browser), and after
the redirect exchanges the code for tokens and saves the ID token's claims, or Cognito's error,
to results/last-login.json.

    python3 prototypes/shibboleth-cognito/scripts/test_login.py
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

HERE = Path(__file__).resolve().parent.parent
OUTPUTS = json.loads((HERE / "terraform" / "outputs.json").read_text())
DOMAIN = OUTPUTS["domain"]["value"]
CLIENT_ID = OUTPUTS["client_id"]["value"]
PROVIDER = OUTPUTS["provider_name"]["value"]
CALLBACK = OUTPUTS["callback_url"]["value"]
RESULTS = HERE / "results"

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
        "identity_provider": PROVIDER,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": state,
    }
)


def decode_jwt_payload(token):
    payload = token.split(".")[1]
    return json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))


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
        query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        if not self.path.startswith("/callback"):
            self.send_response(404)
            self.end_headers()
            return
        if "error" in query:
            result = {
                "outcome": "error",
                "error": query.get("error", [""])[0],
                "error_description": query.get("error_description", [""])[0],
            }
        elif query.get("state", [""])[0] != state:
            result = {"outcome": "error", "error": "state mismatch"}
        else:
            tokens = exchange(query["code"][0])
            result = {
                "outcome": "signed_in",
                "id_token_claims": decode_jwt_payload(tokens["id_token"]),
            }

        RESULTS.mkdir(exist_ok=True)
        (RESULTS / "last-login.json").write_text(json.dumps(result, indent=2))
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
print("Open this URL to sign in as the test university:\n" + authorize_url, flush=True)
(RESULTS).mkdir(exist_ok=True)
(RESULTS / "authorize-url.txt").write_text(authorize_url)
while not server.done:
    server.handle_request()
sys.exit(0)
