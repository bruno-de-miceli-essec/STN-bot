from __future__ import annotations
import os
from functools import wraps
from typing import Callable

from flask import Flask, request, Response

import scanner as s

# --- App init ---
app = Flask(__name__)

# --- Config ---
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASS", "changeme")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "devtoken")
NOTION_WEBHOOK_SECRET = os.getenv("NOTION_WEBHOOK_SECRET", "")

# --- Helpers (HTML) ---
def _page(title: str, body: str, status: str = "") -> str:
    return f"""<!doctype html>
<html lang='fr'>
<head><meta charset='utf-8'><title>{title}</title>
<style>
body {{ font-family: system-ui, -apple-system, Arial; margin: 2rem; }}
.status {{ background:#f0f0f0; border:1px solid #bbb; padding:.5rem 1rem; border-radius:6px; margin-bottom:1rem; }}
button, .btn {{ padding:.6rem 1.1rem; border:1px solid #888; border-radius:6px; background:#eee; cursor:pointer; text-decoration:none; color:#000 }}
button:hover, .btn:hover {{ background:#e2e2e2; }}
form {{ display:inline-block; margin-right: .5rem; }}
.nav a {{ margin-right: 1rem; text-decoration:none; }}
input[type=text] {{ padding:.4rem .6rem; width: 360px; }}
</style></head>
<body>
<h2>STN-bot</h2>
<div class='nav'><a href='/'>Accueil</a> <a href='/admin'>Admin</a></div>
<div class='status'>{status}</div>
{body}
</body></html>"""

# --- Basic Auth ---
def check_auth(username: str, password: str) -> bool:
    return username == ADMIN_USER and password == ADMIN_PASS

def authenticate() -> Response:
    return Response("Auth required", 401, {"WWW-Authenticate": "Basic realm=\"Login Required\""})

def requires_auth() -> Callable:
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(*args, **kwargs):
            auth = request.authorization
            if (
                not auth
                or not auth.username
                or not auth.password
                or not check_auth(auth.username, auth.password)
            ):
                return authenticate()
            return f(*args, **kwargs)
        return wrapper
    return decorator

# --- Notion Secret for webhooks ---
def requires_notion_secret() -> Callable:
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(*args, **kwargs):
            secret = request.headers.get("X-Notion-Secret")
            if not secret or secret != NOTION_WEBHOOK_SECRET:
                return Response("Unauthorized", 401)
            return f(*args, **kwargs)
        return wrapper
    return decorator

# --- Root ---
@app.get("/")
@requires_auth()
def root() -> tuple[str, int]:
    body = """
    <div class='card'>
      <p>Instance en ligne : statut <b>OK</b></p>
      <a class='btn' href='/admin'>Accès admin</a>
    </div>
    """
    return _page("STN-bot", body), 200

# --- Webhook (Meta) ---
@app.get("/webhook")
def webhook_verify():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return (challenge or ""), 200
    return ("Bad verify token", 403)

@app.post("/webhook")
def webhook_events():
    try:
        payload = request.get_json(force=True, silent=True) or {}
        print(f"Webhook reçu: {payload}")
        return "EVENT_RECEIVED", 200
    except Exception as e:
        print(f"/webhook error: {e}")
        return "", 500

# --- Notion triggers (Option A) ---
@app.post("/notion/trigger/bootstrap-form")
@requires_notion_secret()
def notion_bootstrap_form():
    try:
        payload = request.get_json(force=True, silent=True) or {}
        google_form_id = (payload.get("google_form_id") or payload.get("form_id") or "").strip()
        if not google_form_id:
            return Response("Missing google_form_id", 400)
        created = s.bootstrap_form(google_form_id)
        return _page("Bootstrap", f"<p>Bootstrap OK. Lignes créées: {created}</p>", f"form_id={google_form_id}"), 200
    except Exception as e:
        return _page("Erreur", "", f"Erreur bootstrap: {e}"), 500

@app.post("/notion/trigger/sync")
@requires_notion_secret()
def notion_sync_form():
    try:
        payload = request.get_json(force=True, silent=True) or {}
        google_form_id = (payload.get("google_form_id") or payload.get("form_id") or "").strip()
        if not google_form_id:
            return Response("Missing google_form_id", 400)
        updated = s.sync_form(google_form_id)
        return _page("Sync", f"<p>Synchronisation OK. Mises à jour: {updated}</p>", f"form_id={google_form_id}"), 200
    except Exception as e:
        return _page("Erreur", "", f"Erreur sync: {e}"), 500

@app.post("/notion/trigger/send")
@requires_notion_secret()
def notion_send_form():
    try:
        payload = request.get_json(force=True, silent=True) or {}
        google_form_id = (payload.get("google_form_id") or payload.get("form_id") or "").strip()
        if not google_form_id:
            return Response("Missing google_form_id", 400)
        sent = s.send_reminders_for_form(google_form_id)
        return _page("Send", f"<p>Envoi terminé. Rappels envoyés: {sent}</p>", f"form_id={google_form_id}"), 200
    except Exception as e:
        return _page("Erreur", "", f"Erreur envoi: {e}"), 500

# --- Admin minimal (manuel) ---
@app.get("/admin")
@requires_auth()
def admin_home():
    body = """
    <form method='post' action='/admin/bootstrap'>
      <input type='text' name='form_id' placeholder='Google Form ID' required />
      <button type='submit'>Créer fichier suivi (Responses)</button>
    </form>
    <form method='post' action='/admin/sync'>
      <input type='text' name='form_id' placeholder='Google Form ID' required />
      <button type='submit'>Synchroniser ce formulaire</button>
    </form>
    <form method='post' action='/admin/send'>
      <input type='text' name='form_id' placeholder='Google Form ID' required />
      <button type='submit'>Envoyer les rappels</button>
    </form>
    """
    return _page("Admin", body)

@app.post("/admin/bootstrap")
@requires_auth()
def admin_bootstrap():
    try:
        fid = (request.form.get("form_id") or "").strip()
        created = s.bootstrap_form(fid)
        return _page("Admin", "<p>Bootstrap OK.</p>", f"form_id={fid}, créées={created}")
    except Exception as e:
        return _page("Erreur", "", f"Erreur bootstrap: {e}"), 500

@app.post("/admin/sync")
@requires_auth()
def admin_sync():
    try:
        fid = (request.form.get("form_id") or "").strip()
        updated = s.sync_form(fid)
        return _page("Admin", "<p>Synchronisation OK.</p>", f"form_id={fid}, MAJ={updated}")
    except Exception as e:
        return _page("Erreur", "", f"Erreur sync: {e}"), 500

@app.post("/admin/send")
@requires_auth()
def admin_send():
    try:
        fid = (request.form.get("form_id") or "").strip()
        sent = s.send_reminders_for_form(fid)
        return _page("Admin", "<p>Envoi terminé.</p>", f"form_id={fid}, envoyés={sent}")
    except Exception as e:
        return _page("Erreur", "", f"Erreur envoi: {e}"), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "3000")))