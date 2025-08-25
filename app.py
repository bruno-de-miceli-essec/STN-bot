import os
import requests
from flask import Flask, request

# --- Basic Auth helpers and environment variables ---
import base64
import functools
import hmac
from flask import Response

ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASS", "password")

def _ct_eq(a, b):
    """Constant-time string comparison."""
    return hmac.compare_digest(a, b)

def _check_basic_auth(auth_header):
    """Check basic auth header against ADMIN_USER and ADMIN_PASS."""
    if not auth_header or not auth_header.startswith("Basic "):
        return False
    try:
        encoded = auth_header.split(" ", 1)[1].strip()
        decoded = base64.b64decode(encoded).decode("utf-8")
        username, password = decoded.split(":", 1)
        return _ct_eq(username, ADMIN_USER) and _ct_eq(password, ADMIN_PASS)
    except Exception:
        return False

def requires_auth(exempt_paths=None):
    """Decorator for routes that require HTTP Basic Auth, with optional path exemption."""
    if exempt_paths is None:
        exempt_paths = []
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            # Exempt specified paths (e.g., /webhook)
            if request.path in exempt_paths:
                return f(*args, **kwargs)
            auth_header = request.headers.get("Authorization")
            if not _check_basic_auth(auth_header):
                return Response(
                    "Authentication required", 401,
                    {"WWW-Authenticate": 'Basic realm="Login Required"'}
                )
            return f(*args, **kwargs)
        return wrapper
    return decorator

app = Flask(__name__)

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "SantanaESSEC2526@")
PAGE_TOKEN = os.getenv("PAGE_TOKEN")


# Fonction pour envoyer un message via l'API Messenger
def send_message(recipient_id, text):
    url = "https://graph.facebook.com/v16.0/me/messages"
    headers = {"Content-Type": "application/json"}
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": text}
    }
    params = {"access_token": PAGE_TOKEN}
    try:
        response = requests.post(url, headers=headers, params=params, json=payload)
        response.raise_for_status()
    except Exception as e:
        print(f"Erreur lors de l'envoi du message: {e}", flush=True)

@app.route("/", methods=["GET"])
@requires_auth(exempt_paths=["/webhook"])
def index():
    return "ok", 200

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        # Vérification du webhook par Meta
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")

        if mode == "subscribe" and token == VERIFY_TOKEN:
            return challenge or "", 200
        else:
            return "Bad verify token", 403

    elif request.method == "POST":
        data = request.json
        # Print only minimal info: sender id and presence of text
        if data is not None and "entry" in data:
            for entry in data["entry"]:
                messaging_events = entry.get("messaging", [])
                for event in messaging_events:
                    sender_id = event["sender"]["id"]
                    has_text = "message" in event and "text" in event["message"]
                    print(f"Webhook reçu: sender_id={sender_id}, has_text={has_text}", flush=True)
                    # Vérifie si c'est le premier message (champ 'message' présent)
                    if "message" in event:
                        send_message(sender_id, "Connexion avec le bot BDE Santana établie !")
        return "EVENT_RECEIVED", 200

    return "", 400

if __name__ == "__main__":
    port = int(os.getenv("PORT", 3000))
    app.run(host="0.0.0.0", port=port)