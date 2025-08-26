# scanner.py — Notion-only logic (Option A)
from __future__ import annotations
import os
import asyncio
import time
from typing import Dict, List, Set, Optional
from datetime import datetime

import requests
from notion_client import AsyncClient

# --- Env ---
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_FORMS_DB_ID = os.getenv("NOTION_FORMS_DB_ID")
NOTION_PEOPLE_DB_ID = os.getenv("NOTION_PEOPLE_DB_ID")
NOTION_RESPONSES_DB_ID = os.getenv("NOTION_RESPONSES_DB_ID")
FORMS_GATEWAY_URL = os.getenv("FORMS_GATEWAY_URL")  # Apps Script /exec?formId=...
PAGE_TOKEN = os.getenv("PAGE_TOKEN")

DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"
RATE_LIMIT_MS = int(os.getenv("RATE_LIMIT_MS", "0"))

if not NOTION_TOKEN:
    print("[scanner] WARN: NOTION_TOKEN manquant")

# --- Gateway parsing ---
def _parse_ts(val: str | None) -> Optional[datetime]:
    if not val:
        return None
    try:
        return datetime.fromisoformat(val.replace("Z", "+00:00"))
    except Exception:
        return None

def get_form_email_map_from_gateway(form_id: str) -> Dict[str, Optional[datetime]]:
    mapping: Dict[str, Optional[datetime]] = {}
    if not FORMS_GATEWAY_URL or not form_id:
        return mapping
    try:
        resp = requests.get(FORMS_GATEWAY_URL, params={"formId": form_id}, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        # list of strings
        if isinstance(data, list) and all(not isinstance(x, dict) for x in data):
            for x in data:
                em = str(x).strip().lower()
                if em:
                    mapping[em] = None
            return mapping
        # list of objects
        if isinstance(data, list):
            for obj in data:
                if not isinstance(obj, dict):
                    continue
                em = str(obj.get("email", "")).strip().lower()
                ts = _parse_ts(obj.get("submitted_at") or obj.get("timestamp") or obj.get("ts"))
                if em:
                    mapping[em] = ts
            return mapping
        # object with key holding the list
        if isinstance(data, dict):
            for key in ("items", "rows", "emails", "data", "responses"):
                if key in data and isinstance(data[key], list):
                    inner = data[key]
                    if inner and isinstance(inner[0], dict):
                        for obj in inner:
                            em = str(obj.get("email", "")).strip().lower()
                            ts = _parse_ts(obj.get("submitted_at") or obj.get("timestamp") or obj.get("ts"))
                            if em:
                                mapping[em] = ts
                    else:
                        for x in inner:
                            em = str(x).strip().lower()
                            if em:
                                mapping[em] = None
                    return mapping
        return mapping
    except Exception as e:
        print(f"(Gateway) Erreur formId={form_id}: {e}")
        return mapping

# --- Notion helpers ---
async def _notion_query_all(notion: AsyncClient, database_id: str, filter_: Optional[dict] = None) -> List[dict]:
    results: List[dict] = []
    start_cursor = None
    while True:
        kwargs = {"database_id": database_id, "start_cursor": start_cursor}
        if filter_:
            kwargs["filter"] = filter_
        resp = await notion.databases.query(**kwargs)
        results.extend(resp.get("results", []))
        if not resp.get("has_more"):
            break
        start_cursor = resp.get("next_cursor")
    return results

def _get_title_text(page: dict, title_prop: str = "Name") -> str:
    props = page.get("properties", {})
    p = props.get(title_prop) or {}
    arr = p.get("title") or []
    if arr and isinstance(arr, list):
        return (arr[0].get("plain_text") or "").strip()
    return ""

async def _find_form_page_by_google_form_id(notion: AsyncClient, google_form_id: str) -> Optional[dict]:
    if not NOTION_FORMS_DB_ID:
        return None
    flt = {"property": "Form ID", "rich_text": {"equals": google_form_id}}
    items = await _notion_query_all(notion, NOTION_FORMS_DB_ID, filter_=flt)
    return items[0] if items else None

async def _people_email_map(notion: AsyncClient) -> Dict[str, str]:
    """Return {person_page_id: email} from People DB."""
    mapping: Dict[str, str] = {}
    if not NOTION_PEOPLE_DB_ID:
        return mapping
    people = await _notion_query_all(notion, NOTION_PEOPLE_DB_ID)
    for p in people:
        props = p.get("properties", {})
        email_prop = props.get("Email") or {}
        email_val = (email_prop.get("email") or "").strip().lower()
        if email_val:
            mapping[p["id"]] = email_val
    return mapping

async def _people_psid_map(notion: AsyncClient) -> Dict[str, str]:
    """Return {person_page_id: psid} from People DB."""
    mapping: Dict[str, str] = {}
    if not NOTION_PEOPLE_DB_ID:
        return mapping
    people = await _notion_query_all(notion, NOTION_PEOPLE_DB_ID)
    for p in people:
        props = p.get("properties", {})
        psid_prop = props.get("PSID Messenger") or props.get("PSID") or {}
        psid_val = (psid_prop.get("rich_text", [{}])[0].get("plain_text") or "").strip()
        if not psid_val and isinstance(psid_prop, dict) and psid_prop.get("rich_text") is None:
            # If PSID is stored as plain text property type (title/rich_text fallback)
            psid_val = (psid_prop.get("plain_text") or "").strip()
        if psid_val:
            mapping[p["id"]] = psid_val
    return mapping

# --- Bootstrap: create Responses rows for all People for a specific Form ---
async def bootstrap_form_async(google_form_id: str) -> int:
    if not (NOTION_TOKEN and NOTION_FORMS_DB_ID and NOTION_PEOPLE_DB_ID and NOTION_RESPONSES_DB_ID):
        raise RuntimeError("Notion DB IDs or token missing")

    notion = AsyncClient(auth=NOTION_TOKEN)
    created = 0
    try:
        form_page = await _find_form_page_by_google_form_id(notion, google_form_id)
        if not form_page:
            raise RuntimeError(f"Form with Form ID={google_form_id} not found in Notion")
        form_page_id = form_page["id"]
        form_title = _get_title_text(form_page, title_prop="Nom du formulaire") or _get_title_text(form_page) or google_form_id

        people_pages = await _notion_query_all(notion, NOTION_PEOPLE_DB_ID)
        people_ids = [p["id"] for p in people_pages]

        resp_filter = {"property": "Form", "relation": {"contains": form_page_id}}
        existing_responses = await _notion_query_all(notion, NOTION_RESPONSES_DB_ID, filter_=resp_filter)
        existing_person_ids: Set[str] = set()
        for r in existing_responses:
            props = r.get("properties", {})
            rel = props.get("Person") or {}
            for it in (rel.get("relation") or []):
                pid = it.get("id")
                if pid:
                    existing_person_ids.add(pid)

        for pid in people_ids:
            if pid in existing_person_ids:
                continue
            props = {
                "Name": {"title": [{"text": {"content": form_title}}]},
                "Form": {"relation": [{"id": form_page_id}]},
                "Person": {"relation": [{"id": pid}]},
                "A répondu": {"checkbox": False},
            }
            try:
                await notion.pages.create(parent={"database_id": NOTION_RESPONSES_DB_ID}, properties=props)
                created += 1
            except Exception as ce:
                print(f"(Bootstrap) Create response row failed for person {pid}: {ce}")
        print(f"(Bootstrap) Created {created} response rows for form {google_form_id}")
        return created
    finally:
        try:
            maybe_close = getattr(notion, "close", None) or getattr(notion, "aclose", None)
            if callable(maybe_close):
                res = maybe_close()
                if asyncio.iscoroutine(res):
                    await res
        except Exception:
            pass

# --- Sync: mark responses for one Form ---
async def sync_form_async(google_form_id: str) -> int:
    if not (NOTION_TOKEN and NOTION_FORMS_DB_ID and NOTION_RESPONSES_DB_ID):
        raise RuntimeError("Notion DB IDs or token missing")

    notion = AsyncClient(auth=NOTION_TOKEN)
    updated = 0
    try:
        form_page = await _find_form_page_by_google_form_id(notion, google_form_id)
        if not form_page:
            raise RuntimeError(f"Form with Form ID={google_form_id} not found in Notion")
        form_page_id = form_page["id"]

        # 1) Gateway map {email -> submitted_at}
        email_map = get_form_email_map_from_gateway(google_form_id)
        if not email_map:
            print(f"(Sync) Aucun email renvoyé pour form={google_form_id}")

        # 2) People map {person_id -> email}
        person_email = await _people_email_map(notion)
        # 3) Responses for this form
        resp_filter = {"property": "Form", "relation": {"contains": form_page_id}}
        responses = await _notion_query_all(notion, NOTION_RESPONSES_DB_ID, filter_=resp_filter)

        # 4) Update each response if that person's email is in email_map
        for r in responses:
            props = r.get("properties", {})
            rel = props.get("Person") or {}
            rel_arr = rel.get("relation") or []
            if not rel_arr:
                continue
            pid = rel_arr[0].get("id")
            if not pid:
                continue
            email = person_email.get(pid, "")
            if not email:
                continue
            if email in email_map:
                submitted_at = email_map[email] or datetime.utcnow()
                answered_prop = props.get("A répondu") or {}
                already = bool(answered_prop.get("checkbox", False))
                if not already:
                    try:
                        await notion.pages.update(
                            page_id=r["id"],
                            properties={
                                "A répondu": {"checkbox": True},
                                "Date de réponse": {"date": {"start": submitted_at.isoformat()}},
                            },
                        )
                        updated += 1
                    except Exception as e:
                        print(f"(Sync) Update failed for response {r.get('id')}: {e}")
        print(f"(Sync) Mises à jour: {updated}")
        return updated
    finally:
        try:
            maybe_close = getattr(notion, "close", None) or getattr(notion, "aclose", None)
            if callable(maybe_close):
                res = maybe_close()
                if asyncio.iscoroutine(res):
                    await res
        except Exception:
            pass

# --- Send: reminders for one Form ---
def _fb_send_message(psid: str, text: str) -> bool:
    if not PAGE_TOKEN:
        print("(Send) PAGE_TOKEN manquant — envoi ignoré")
        return False
    url = "https://graph.facebook.com/v17.0/me/messages"
    payload = {"recipient": {"id": psid}, "message": {"text": text}}
    try:
        resp = requests.post(url, params={"access_token": PAGE_TOKEN}, json=payload, timeout=20)
        if not resp.ok:
            print(f"(Send) Erreur API FB {resp.status_code}: {resp.text}")
        return resp.ok
    except Exception as e:
        print(f"(Send) Exception API FB: {e}")
        return False

async def send_reminders_for_form_async(google_form_id: str) -> int:
    if not (NOTION_TOKEN and NOTION_FORMS_DB_ID and NOTION_RESPONSES_DB_ID):
        raise RuntimeError("Notion DB IDs or token missing")

    notion = AsyncClient(auth=NOTION_TOKEN)
    sent = 0
    try:
        form_page = await _find_form_page_by_google_form_id(notion, google_form_id)
        if not form_page:
            raise RuntimeError(f"Form with Form ID={google_form_id} not found in Notion")
        form_page_id = form_page["id"]
        # Retrieve form link for message
        form_link = ""
        props = form_page.get("properties", {})
        link_prop = props.get("Lien") or props.get("Form Link") or {}
        if isinstance(link_prop, dict):
            form_link = (link_prop.get("url") or "").strip()

        person_psid = await _people_psid_map(notion)
        # Responses needing reminders
        resp_filter = {"property": "Form", "relation": {"contains": form_page_id}}
        responses = await _notion_query_all(notion, NOTION_RESPONSES_DB_ID, filter_=resp_filter)

        for r in responses:
            props = r.get("properties", {})
            # Skip answered
            answered = bool((props.get("A répondu") or {}).get("checkbox", False))
            if answered:
                continue
            rel = props.get("Person") or {}
            rel_arr = rel.get("relation") or []
            if not rel_arr:
                continue
            pid = rel_arr[0].get("id")
            if not pid:
                continue
            psid = person_psid.get(pid, "")
            if not psid:
                continue

            # Compose message
            link_txt = form_link or "(lien indisponible)"
            msg = (
                "Bonjour 👋, petit rappel pour compléter le formulaire.\n"
                f"Lien : {link_txt}"
            )

            if DRY_RUN:
                print(f"(DRY_RUN) [PSID={psid}] {msg}")
                sent += 1
                try:
                    await notion.pages.update(
                        page_id=r["id"],
                        properties={
                            "Dernier rappel": {"date": {"start": datetime.utcnow().isoformat()}}
                        },
                    )
                except Exception as ue:
                    print(f"(Send) Update dernier rappel failed for response {r.get('id')}: {ue}")
            else:
                if _fb_send_message(psid, msg):
                    sent += 1
                    try:
                        await notion.pages.update(
                            page_id=r["id"],
                            properties={
                                "Dernier rappel": {"date": {"start": datetime.utcnow().isoformat()}}
                            },
                        )
                    except Exception as ue:
                        print(f"(Send) Update dernier rappel failed for response {r.get('id')}: {ue}")
                    if RATE_LIMIT_MS > 0:
                        time.sleep(RATE_LIMIT_MS / 1000.0)
        print(f"(Send) Rappels envoyés: {sent}")
        return sent
    finally:
        try:
            maybe_close = getattr(notion, "close", None) or getattr(notion, "aclose", None)
            if callable(maybe_close):
                res = maybe_close()
                if asyncio.iscoroutine(res):
                    await res
        except Exception:
            pass

# --- Sync wrappers (sync versions for Flask routes) ---
def bootstrap_form(google_form_id: str) -> int:
    return asyncio.run(bootstrap_form_async(google_form_id))

def sync_form(google_form_id: str) -> int:
    return asyncio.run(sync_form_async(google_form_id))

def send_reminders_for_form(google_form_id: str) -> int:
    return asyncio.run(send_reminders_for_form_async(google_form_id))