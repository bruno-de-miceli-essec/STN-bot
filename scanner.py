# scanner.py — logique Notion + Forms + envoi Messenger
from __future__ import annotations
import os
import asyncio
import time
from typing import Dict, List, Set
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from notion_client import AsyncClient

# --- Configuration via variables d'environnement ---
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
FORMS_GATEWAY_URL = os.getenv("FORMS_GATEWAY_URL")  # Apps Script /exec qui renvoie des emails par formId
PAGE_TOKEN = os.getenv("PAGE_TOKEN")

DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"
MIN_REMINDER_DAYS = int(os.getenv("MIN_REMINDER_DAYS", "0"))  # réservé si tu veux filtrer selon une date
RATE_LIMIT_MS = int(os.getenv("RATE_LIMIT_MS", "0"))  # délai entre envois pour FB

if not NOTION_TOKEN or not NOTION_DATABASE_ID:
    # Laisse passer l'import côté app.py, mais garde une info utile pour /admin
    print("[scanner] WARN: NOTION_TOKEN/NOTION_DATABASE_ID non définis")


# --- Helpers Forms -----------------------------------------------------------
def get_form_emails_from_gateway_by_id(form_id: str) -> Set[str]:
    """Appelle la gateway Apps Script pour récupérer les emails d'un form donné.
    Retourne un set d'emails (lowercased)."""
    if not FORMS_GATEWAY_URL or not form_id:
        return set()
    try:
        resp = requests.get(FORMS_GATEWAY_URL, params={"formId": form_id}, timeout=20)
        resp.raise_for_status()
        data = resp.json() or []
        emails = {str(x).strip().lower() for x in data if x}
        return emails
    except Exception as e:
        print(f"(Gateway) Erreur lors de la récupération des emails pour formId={form_id}: {e}")
        return set()


# --- Helpers Notion ----------------------------------------------------------
async def _fetch_all_pages(notion: AsyncClient) -> List[dict]:
    """Récupère toutes les pages de la DB (pagination)."""
    results: List[dict] = []
    start_cursor = None
    while True:
        resp = await notion.databases.query(
            database_id=str(NOTION_DATABASE_ID), start_cursor=start_cursor
        )
        results.extend(resp.get("results", []))
        if not resp.get("has_more"):
            break
        start_cursor = resp.get("next_cursor")
    return results


def _extract_prop_text(props: dict, name: str) -> str | None:
    p = props.get(name)
    if not isinstance(p, dict):
        return None
    if p.get("rich_text"):
        return (p["rich_text"][0].get("plain_text") or "").strip()
    if p.get("title"):
        return (p["title"][0].get("plain_text") or "").strip()
    if p.get("url"):
        return (p.get("url") or "").strip()
    return None


def _extract_prop_email(props: dict, name: str = "Email") -> str | None:
    p = props.get(name)
    if isinstance(p, dict) and p.get("email"):
        return (p.get("email") or "").strip().lower()
    return None


def _extract_prop_checkbox(props: dict, name: str) -> bool:
    p = props.get(name)
    if isinstance(p, dict):
        return bool(p.get("checkbox", False))
    return False


# --- SYNC: Forms -> Notion ---------------------------------------------------
async def sync_notion_checkbox_from_forms() -> int:
    """Coche 'A répondu' si — et seulement si — l'email a répondu AU form lié à la ligne."""
    notion = AsyncClient(auth=NOTION_TOKEN)
    try:
        pages = await _fetch_all_pages(notion)

        # Collecte des Form IDs uniques présents en DB
        unique_fids: Set[str] = set()
        for page in pages:
            props = page.get("properties", {})
            fid = _extract_prop_text(props, "Form ID")
            if fid:
                unique_fids.add(fid)

        if not unique_fids:
            print("(Sync) Aucun Form ID détecté dans Notion — synchro ignorée")
            return 0

        # Récupération des emails par Form ID en parallèle (I/O bound)
        form_id_to_emails: Dict[str, Set[str]] = {}
        with ThreadPoolExecutor(max_workers=min(8, len(unique_fids))) as pool:
            futures = {pool.submit(get_form_emails_from_gateway_by_id, fid): fid for fid in unique_fids}
            for fut in as_completed(futures):
                fid = futures[fut]
                try:
                    form_id_to_emails[fid] = fut.result() or set()
                except Exception as e:
                    print(f"(Gateway) Erreur pour formId={fid}: {e}")
                    form_id_to_emails[fid] = set()

        print(f"(Gateway) formIds détectés: {sorted(unique_fids)}")
        total_emails = sum(len(v) for v in form_id_to_emails.values())
        print(f"(Gateway) emails récupérés (agrégés): {total_emails}")

        updated = 0
        matched = 0

        for page in pages:
            props = page.get("properties", {})
            email = _extract_prop_email(props, "Email")
            fid = _extract_prop_text(props, "Form ID")
            answered = _extract_prop_checkbox(props, "A répondu")

            if not (email and fid):
                continue

            emails_for_form = form_id_to_emails.get(fid, set())
            if email in emails_for_form:
                matched += 1
                if not answered:
                    # Coche la case
                    try:
                        await notion.pages.update(
                            page_id=page["id"],
                            properties={"A répondu": {"checkbox": True}},
                        )
                        updated += 1
                    except Exception as e:
                        print(f"(Sync) Erreur mise à jour page {page.get('id')}: {e}")

        print(f"(Sync) {matched} correspondances trouvées. {updated} nouvelles réponses mises à jour dans Notion")
        return updated
    finally:
        # Graceful close (handles libraries without .close or with sync/async close)
        try:
            maybe_close = getattr(notion, "close", None) or getattr(notion, "aclose", None)
            if callable(maybe_close):
                result = maybe_close()
                if asyncio.iscoroutine(result):
                    await result
        except Exception:
            pass


# --- SEND: Notion -> Messenger ----------------------------------------------
def _fb_send_message(psid: str, text: str) -> bool:
    if not PAGE_TOKEN:
        print("(Send) PAGE_TOKEN manquant — envoi ignoré")
        return False
    url = "https://graph.facebook.com/v17.0/me/messages"
    payload = {"recipient": {"id": psid}, "message": {"text": text}}
    try:
        resp = requests.post(url, params={"access_token": PAGE_TOKEN}, json=payload, timeout=20)
        ok = resp.ok
        if not ok:
            print(f"(Send) Erreur API FB {resp.status_code}: {resp.text}")
        return ok
    except Exception as e:
        print(f"(Send) Exception API FB: {e}")
        return False


async def send_reminders() -> int:
    """Envoie des rappels aux lignes sans 'A répondu' et avec PSID présent."""
    notion = AsyncClient(auth=NOTION_TOKEN)
    sent = 0
    try:
        pages = await _fetch_all_pages(notion)
        for page in pages:
            props = page.get("properties", {})
            answered = _extract_prop_checkbox(props, "A répondu")
            if answered:
                continue
            # Besoin d'un PSID + lien Form pour un rappel utile
            psid = _extract_prop_text(props, "PSID")
            form_link = _extract_prop_text(props, "Form Link")
            sent_date = _extract_prop_text(props, "Date d'envoi") or _extract_prop_text(props, "Date d’envoi")
            email = _extract_prop_email(props, "Email") or ""

            if not psid:
                continue

            # Compose le message
            date_txt = sent_date or "(date non renseignée)"
            link_txt = form_link or "(Pas de lien fourni)"
            msg = (
                f"Bonjour 👋, tu n’as pas encore rempli le formulaire envoyé le {date_txt}.\n"
                f"Merci de le remplir ici : {link_txt}"
            )

            if DRY_RUN:
                print(f"(DRY_RUN) [PSID={psid}] {msg}")
                sent += 1
            else:
                if _fb_send_message(psid, msg):
                    sent += 1
                    if RATE_LIMIT_MS > 0:
                        time.sleep(RATE_LIMIT_MS / 1000.0)
        print(f"(Send) Rappels envoyés : {sent}")
        return sent
    finally:
        # Graceful close (handles libraries without .close or with sync/async close)
        try:
            maybe_close = getattr(notion, "close", None) or getattr(notion, "aclose", None)
            if callable(maybe_close):
                result = maybe_close()
                if asyncio.iscoroutine(result):
                    await result
        except Exception:
            pass


# --- Wrappers synchrones pour app.py (/admin) -------------------------------
def run_sync_from_forms_sync() -> int:
    return asyncio.run(sync_notion_checkbox_from_forms())


def run_send_reminders_sync() -> int:
    return asyncio.run(send_reminders())