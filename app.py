# app.py — serveur Flask (Render): webhook Messenger + interface admin
import os
import base64
import functools
import hmac
import requests
from flask import Flask, request, Response
from db import Base, engine
import models  # noqa: F401 (garantit l’import des modèles)
import scanner as s  # logique Notion/Forms/Send

app = Flask(__name__)

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "SantanaESSEC2526@")
PAGE_TOKEN = os.getenv("PAGE_TOKEN")
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASS", "password")

# --- Basic Auth helpers ------------------------------------------------------
def _ct_eq(a: str, b: str) -> bool:
    try:
        return hmac.compare_digest(a or "", b or "")
    except Exception:
        return False


def _check_basic_auth(auth_header: str | None) -> bool:
    if not auth_header or not auth_header.startswith("Basic "):
        return False
    try:
        encoded = auth_header.split(" ", 1)[1].strip()
        decoded = base64.b64decode(encoded).decode("utf-8")
        username, password = decoded.split(":", 1)
        return _ct_eq(username, ADMIN_USER) and _ct_eq(password, ADMIN_PASS)
    except Exception:
        return False


def requires_auth(exempt_paths: tuple[str, ...] = ("/webhook",)):
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            # Exemption (webhook doit rester public)
            for p in exempt_paths:
                if request.path.startswith(p):
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


# --- UI admin ---------------------------------------------------------------

def render_admin(status_msg: str = "") -> str:
    return f"""<!doctype html>
<html lang=\"fr\"><head><meta charset=\"utf-8\"><title>Admin Panel</title>
<style>
body {{ font-family: system-ui, -apple-system, Arial; margin: 2rem; }}
.status {{ background:#f0f0f0; border:1px solid #bbb; padding:.5rem 1rem; border-radius:6px; margin-bottom:1rem; }}
button {{ padding:.6rem 1.1rem; border:1px solid #888; border-radius:6px; background:#eee; cursor:pointer; }}
button:hover {{ background:#e2e2e2; }}
form {{ display:inline-block; margin-right: .5rem; }}
</style></head>
<body>
<h2>Admin Panel</h2>
<div class=\"status\">{status_msg}</div>
<form method=\"post\" action=\"/admin/sync\"><button type=\"submit\">Synchroniser les réponses</button></form>
<form method=\"post\" action=\"/admin/send\"><button type=\"submit\">Envoyer les rappels</button></form>
</body></html>"""


@app.route("/admin", methods=["GET"])  
@requires_auth()
def admin_panel():
    return render_admin()


@app.route("/admin/sync", methods=["POST"])  
@requires_auth()
def admin_sync():
    updated = s.run_sync_from_forms_sync()
    return render_admin(f"Synchronisation OK — {updated} nouvelles réponses mises à jour dans Notion")


@app.route("/admin/send", methods=["POST"])  
@requires_auth()
def admin_send():
    sent = s.run_send_reminders_sync()
    return render_admin(f"Rappels envoyés : {sent}")


# --- Messenger webhook -------------------------------------------------------

def send_message(recipient_id: str, text: str) -> None:
    if not PAGE_TOKEN:
        print("(Webhook) PAGE_TOKEN manquant — message d'accueil non envoyé")
        return
    url = "https://graph.facebook.com/v17.0/me/messages"
    payload = {"recipient": {"id": recipient_id}, "message": {"text": text}}
    try:
        resp = requests.post(url, params={"access_token": PAGE_TOKEN}, json=payload, timeout=20)
        if not resp.ok:
            print(f"(Webhook) Erreur send_message {resp.status_code}: {resp.text}")
    except Exception as e:
        print(f"(Webhook) Exception send_message: {e}")


@app.route("/", methods=["GET"])  
@requires_auth()
def index():
    return "ok", 200


@app.route("/webhook", methods=["GET", "POST"])  
def webhook():
    if request.method == "GET":
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        if mode == "subscribe" and token == VERIFY_TOKEN:
            return challenge or "", 200
        return "Bad verify token", 403

    # POST
    data = request.json or {}
    try:
        for entry in data.get("entry", []):
            for event in entry.get("messaging", []):
                sender_id = event.get("sender", {}).get("id")
                has_text = bool(event.get("message", {}).get("text"))
                print(f"Webhook reçu: sender_id={sender_id}, has_text={has_text}")
                # Premier message: on envoie l'accusé de connexion une seule fois
                if sender_id and "message" in event:
                    send_message(sender_id, "Connexion avec le bot BDE Santana établie !")
    except Exception as e:
        print(f"(Webhook) Parse error: {e}")
    return "EVENT_RECEIVED", 200

with engine.begin() as conn:
    Base.metadata.create_all(bind=conn)

if __name__ == "__main__":
    port = int(os.getenv("PORT", "3000"))
    app.run(host="0.0.0.0", port=port)