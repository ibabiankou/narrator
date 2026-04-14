import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

import time
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


def load_images(book_id, attempts=10):
    images = []
    for i in range(attempts):
        images = request.get(f"https://nnarrator.eu/api/books/{book_id}/images").json()
        if len(images) > 0:
            return images
        else:
            time.sleep(3)

    return images


if __name__ == "__main__":
    request = session()

    books = request.get("https://nnarrator.eu/api/books/").json()
    print(books)

    # For each book without cover, extract images, load images, set cover.

    skip_ids = {"7aff0995-5a21-414f-bff7-c5e6774dc050"}

    for book_ind, book in enumerate(books):
        print(f"Processing book {book_ind+1}/{len(books)}... {book['id']} {book['title']}")
        if book["cover"]:
            print(f"Book {book['id']} already has a cover: {book['cover']}, skipping...")
            continue

        if book['id'] in skip_ids:
            print(f"Skipping book {book['id']} {book['cover']}...")
            continue

        # Check if already has images:
        book_images = load_images(book['id'], 1)
        if len(book_images) == 0:
            print(f"Triggering image extraction for book {book['title']}...")
            request.post(f"https://nnarrator.eu/api/processing/{book['id']}/extract-images")
            time.sleep(5)

            # Reload images
            book_images = load_images(book['id'], 30)
            if len(book_images) == 0:
                raise Exception(f"No images found for book {book['title']} after extraction.")

        print(f"Setting {book_images[0]} as cover for book {book['title']}...")
        request.post(f"https://nnarrator.eu/api/books/{book['id']}/metadata/cover",
                     json={"file_path": book_images[0]})

        time.sleep(0.5)

    print("Done...")
