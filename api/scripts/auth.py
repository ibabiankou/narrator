import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

from requests_oauthlib import OAuth2Session

# Configuration - Replace with your Keycloak/API details
client_id = "nnarrator-webapp"
authorization_base_url = "https://iam.nnarrator.eu/realms/nnarrator/protocol/openid-connect/auth"
token_url = "https://iam.nnarrator.eu/realms/nnarrator/protocol/openid-connect/token"
redirect_uri = "http://127.0.0.1:8080/callback"
scope = ["openid", "profile", "email"]

# This variable will store the captured URL
captured_url = None


class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global captured_url
        captured_url = self.path
        print(f"Captured response: {captured_url}")

        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"<h1>Authentication Successful!</h1><p>You can close this window now.</p>")

    def log_message(self, format, *args):
        return  # Silences the local server logs in console


def session() -> OAuth2Session:
    oauth = OAuth2Session(client_id, redirect_uri=redirect_uri, scope=scope, pkce="S256")
    authorization_url, state = oauth.authorization_url(authorization_base_url)

    # 1. Start a local server on port 8080
    server = HTTPServer(("127.0.0.1", 8080), CallbackHandler)

    print(f"Opening browser for login...")
    webbrowser.open(authorization_url)

    # 2. Wait for exactly one request (the redirect)
    server.handle_request()

    full_redirect_url = f"https://localhost:8080{captured_url}"

    token = oauth.fetch_token(
        token_url,
        authorization_response=full_redirect_url,
    )

    print("\n--- Success! ---")
    print(f"Access Token obtained: {token['access_token'][:30]}...")

    return oauth
