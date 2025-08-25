from __future__ import annotations
import os
from functools import wraps
from typing import Callable

from flask import Flask, request, Response

from db import init_db, SessionLocal
import models  # ensure models are registered
import scanner as s

# --- App init & DB bootstrap ---
app = Flask(__name__)
init_db()

ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASS", "changeme")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "devtoken")

# --- Basic Auth decorator ---
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

# --- Root ---
@app.get("/")
@requires_auth()
def root() -> tuple[str, int]:
    return (
        """<!doctype html>
<html lang=\"fr\"><head><meta charset=\"utf-8\"><title>STN-bot</title>
<style>
body{font-family:system-ui,-apple-system,Arial;margin:2rem}
.card{border:1px solid #ccc;border-radius:8px;padding:1rem;display:inline-block}
.btn{padding:.6rem 1.1rem;border:1px solid #888;border-radius:6px;background:#eee;cursor:pointer;text-decoration:none;color:#000}
.btn:hover{background:#e2e2e2}
.nav a{margin-right:1rem}
</style></head><body>
<h2>STN-bot</h2>
<div class=\"card\">
<p>Instance en ligne : statut <b>OK</b></p>
<a class=\"btn\" href=\"/admin\">Accès admin</a>
</div>
</body></html>""",
        200,
    )

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
        # Réponse 200 immédiate pour Meta
        return "EVENT_RECEIVED", 200
    except Exception as e:
        print(f"/webhook error: {e}")
        return "", 500

# --- Admin pages ---

def _admin_html(body: str, status: str = "") -> str:
    return f"""<!doctype html>
<html lang='fr'><head><meta charset='utf-8'><title>Admin</title>
<style>
body {{ font-family: system-ui, -apple-system, Arial; margin: 2rem; }}
.status {{ background:#f0f0f0; border:1px solid #bbb; padding:.5rem 1rem; border-radius:6px; margin-bottom:1rem; }}
button {{ padding:.6rem 1.1rem; border:1px solid #888; border-radius:6px; background:#eee; cursor:pointer; }}
button:hover {{ background:#e2e2e2; }}
form {{ display:inline-block; margin-right: .5rem; }}
.nav a {{ margin-right: 1rem; text-decoration:none; }}
</style></head>
<body>
<h2>Admin Panel</h2>
<div class='nav'><a href='/admin'>Accueil</a><a href='/admin/forms'>Forms</a></div>
<div class='status'>{status}</div>
{body}
</body></html>"""

@app.get("/admin")
@requires_auth()
def admin_home():
    body = (
        "<form method='post' action='/admin/sync'><button type='submit'>Synchroniser les réponses</button></form>\n"
        "<form method='post' action='/admin/send'><button type='submit'>Envoyer les rappels</button></form>"
    )
    return _admin_html(body)

@app.post("/admin/sync")
@requires_auth()
def admin_sync():
    try:
        updated = s.run_sync_from_forms_sync()
        return _admin_html("<p>Synchronisation OK.</p>", f"Mises à jour Notion: {updated}")
    except Exception as e:
        return _admin_html("", f"Erreur sync: {e}"), 500

@app.post("/admin/send")
@requires_auth()
def admin_send():
    try:
        sent = s.run_send_reminders_sync()
        return _admin_html("<p>Envoi terminé.</p>", f"Rappels envoyés: {sent}")
    except Exception as e:
        return _admin_html("", f"Erreur envoi: {e}"), 500

@app.get("/admin/forms")
@requires_auth()
def admin_forms_list():
    forms = s.get_forms_summary()
    rows = "".join(
        f"<tr><td>{f['id']}</td><td>{f.get('title') or ''}</td><td>{f['google_form_id']}</td><td>{f['responses_count']}</td>"
        f"<td><form method='post' action='/admin/form/{f['id']}/sync' style='display:inline'><button type='submit'>Sync</button></form> "
        f"<a href='/admin/form/{f['id']}'>Voir</a></td></tr>" for f in forms
    )
    body = f"""
    <table border='1' cellpadding='6' cellspacing='0'>
      <tr><th>ID</th><th>Nom</th><th>Form ID</th><th>#Réponses</th><th>Actions</th></tr>
      {rows}
    </table>
    """
    return _admin_html(body)

@app.get("/admin/form/<int:form_id>")
@requires_auth()
def admin_form_detail(form_id: int):
    with SessionLocal() as db:
        f = db.query(models.Form).filter(models.Form.id == form_id).first()
        if not f:
            return _admin_html("<p>Form introuvable</p>"), 404
        responses = (
            db.query(models.Response)
            .filter(models.Response.form_id == form_id)
            .order_by(models.Response.submitted_at.desc())
            .all()
        )
        rows = "".join(
            f"<tr><td>{r.email}</td><td>{r.submitted_at}</td></tr>" for r in responses
        )
        body = f"""
        <h3>{f.title or f.google_form_id}</h3>
        <form method='post' action='/admin/form/{form_id}/sync'><button type='submit'>Resynchroniser</button></form>
        <table border='1' cellpadding='6' cellspacing='0'>
          <tr><th>Email</th><th>Reçu le</th></tr>
          {rows}
        </table>
        """
        return _admin_html(body)

@app.post("/admin/form/<int:form_id>/sync")
@requires_auth()
def admin_form_sync(form_id: int):
    try:
        updated = s.run_sync_single_form_sync(form_id)
        return _admin_html("<p>Resync terminé.</p>", f"Mises à jour Notion: {updated}")
    except Exception as e:
        return _admin_html("", f"Erreur resync: {e}"), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "3000")))
