# scanner.py — logique métier (AUCUNE UI ici)
import os
import asyncio
import datetime
from typing import Set
import requests
from dotenv import load_dotenv
from notion_client import AsyncClient

# Charger .env (sans écraser l’existant)
load_dotenv(dotenv_path=".env", override=False)

# --- Config ---
FORMS_GATEWAY_URL = os.getenv("FORMS_GATEWAY_URL")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
PAGE_TOKEN = os.getenv("PAGE_TOKEN")

# Options d’exécution
DRY_RUN = os.getenv("DRY_RUN", "false").lower() in {"1", "true", "yes"}
MIN_REMINDER_DAYS = int(os.getenv("MIN_REMINDER_DAYS", "0") or 0)
RATE_LIMIT_MS = int(os.getenv("RATE_LIMIT_MS", "0") or 0)


# --------------------------- Gateway Forms ---------------------------
def get_form_emails_from_gateway_by_id(form_id: str) -> Set[str]:
    """Appelle la gateway Apps Script et renvoie un set d'emails (lowercase)."""
    if not FORMS_GATEWAY_URL:
        return set()
    try:
        resp = requests.get(FORMS_GATEWAY_URL, params={"formId": form_id}, timeout=20)
        resp.raise_for_status()
        payload = resp.json() or {}
        emails = payload.get("emails") or []
        people = payload.get("people") or []
        extracted = []
        extracted.extend([str(e).strip().lower() for e in emails if e])
        for p in people:
            em = str(p.get("email", "")).strip().lower()
            if em:
                extracted.append(em)
        return set(extracted)
    except Exception as e:
        print(f"(Gateway) Erreur lors de la récupération des emails pour formId={form_id}: {e}")
        return set()


async def collect_emails_via_gateway_from_notion_forms(notion: AsyncClient) -> Set[str]:
    """Parcourt la DB Notion, récupère les Form ID (rich text) et agrège les emails via la gateway."""
    form_ids: Set[str] = set()
    resp = await notion.databases.query(database_id=str(NOTION_DATABASE_ID))
    results = resp.get("results", [])
    for page in results:
        props = page.get("properties", {})
        form_id_prop = props.get("Form ID")
        fid = None
        if form_id_prop and form_id_prop.get("rich_text"):
            fid = (form_id_prop["rich_text"][0].get("plain_text") or "").strip()
        if fid:
            form_ids.add(fid)
    print(f"(Gateway) formIds détectés: {sorted(form_ids)}")

    all_emails: Set[str] = set()
    for fid in form_ids:
        all_emails |= get_form_emails_from_gateway_by_id(fid)
    print(f"(Gateway) emails récupérés: {len(all_emails)}")
    if not all_emails:
        print("(Gateway) Aucun email récupéré depuis les Forms référencés en Notion")
    return all_emails


# --------------------------- Messenger ---------------------------
def send_message(psid: str | None, text: str) -> None:
    if psid is None:
        print("⚠️ PSID manquant, message non envoyé")
        return
    if PAGE_TOKEN is None:
        print("⚠️ PAGE_TOKEN manquant, message non envoyé")
        return
    url = f"https://graph.facebook.com/v18.0/me/messages?access_token={PAGE_TOKEN}"
    payload = {
        "recipient": {"id": psid},
        "message": {"text": text},
        "tag": "CONFIRMED_EVENT_UPDATE",
    }
    try:
        r = requests.post(url, json=payload, timeout=15)
        if r.status_code != 200:
            print(f"❌ Erreur API: {r.status_code} - {r.text}")
        else:
            print(f"✅ Message envoyé à {psid}")
    except Exception as e:
        print(f"❌ Exception lors de l'envoi: {e}")


# --------------------------- Flux Notion ---------------------------
async def sync_notion_checkbox_from_forms() -> int:
    """Coche la case 'A répondu' pour les emails présents dans les réponses de Form."""
    notion = AsyncClient(auth=NOTION_TOKEN)
    try:
        emails = await collect_emails_via_gateway_from_notion_forms(notion)
        if not emails:
            print("(Sync) Aucun email récupéré via la gateway — synchro ignorée")
            return 0
        resp = await notion.databases.query(database_id=str(NOTION_DATABASE_ID))
        results = resp.get("results", [])
        updated = 0
        matched = 0
        for page in results:
            props = page.get("properties", {})

            email_prop = props.get("Email")
            email = email_prop.get("email") if isinstance(email_prop, dict) else None

            answered_prop = props.get("A répondu")
            answered = answered_prop.get("checkbox", False) if isinstance(answered_prop, dict) else False

            if email and email.lower() in emails:
                matched += 1
                if not answered:
                    page_id = page["id"]
                    await notion.pages.update(page_id=page_id, properties={"A répondu": {"checkbox": True}})
                    updated += 1
        print(f"(Sync) {matched} correspondances trouvées. {updated} nouvelles réponses mises à jour dans Notion")
        return updated
    finally:
        pass


async def send_reminders() -> int:
    """Envoie les rappels aux entrées Notion avec 'A répondu' == False."""
    notion = AsyncClient(auth=NOTION_TOKEN)
    try:
        resp = await notion.databases.query(database_id=str(NOTION_DATABASE_ID))
        results = resp.get("results", [])
        sent = 0
        for page in results:
            props = page.get("properties", {})

            email_prop = props.get("Email")
            email = email_prop.get("email") if isinstance(email_prop, dict) else None

            psid_prop = props.get("PSID")
            psid = psid_prop["rich_text"][0]["plain_text"] if psid_prop and psid_prop.get("rich_text") else None

            # IMPORTANT: URL publique à envoyer aux membres
            form_link_prop = props.get("Form Link")
            form_link = form_link_prop.get("url") if isinstance(form_link_prop, dict) else None

            answered_prop = props.get("A répondu")
            answered = answered_prop.get("checkbox", False) if isinstance(answered_prop, dict) else False

            date_prop = props.get("Date envoi")
            date_field = date_prop.get("date") if isinstance(date_prop, dict) else None
            date_envoi = date_field.get("start") if isinstance(date_field, dict) else None

            last_reminder_prop = props.get("Dernier rappel")
            last_reminder_field = last_reminder_prop.get("date") if isinstance(last_reminder_prop, dict) else None
            last_reminder = last_reminder_field.get("start") if isinstance(last_reminder_field, dict) else None

            # Règle d’intervalle minimal
            skip_due_to_interval = False
            if MIN_REMINDER_DAYS and last_reminder:
                try:
                    lr_dt = datetime.datetime.fromisoformat(last_reminder.replace("Z", "+00:00"))
                    now_dt = datetime.datetime.now(datetime.timezone.utc)
                    delta_days = (now_dt - lr_dt).days
                    if delta_days < MIN_REMINDER_DAYS:
                        skip_due_to_interval = True
                except Exception:
                    skip_due_to_interval = False

            if (not answered) and not skip_due_to_interval:
                # Construire le message
                date_txt = date_envoi or ""
                link_txt = form_link or "(Pas de lien fourni)"
                message = (
                    f"Message for {email} ({psid}):\n"
                    f"Bonjour 👋, tu n’as pas encore rempli le formulaire envoyé le {date_txt}.\n"
                    f"Merci de le remplir ici : {link_txt}"
                )
                print(message)

                if DRY_RUN:
                    print("[DRY_RUN] Envoi simulé — aucun message réellement envoyé.")
                else:
                    send_message(psid, message)
                    # Mettre à jour 'Dernier rappel'
                    try:
                        page_id = page["id"]
                        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
                        await notion.pages.update(page_id=page_id, properties={
                            "Dernier rappel": {"date": {"start": now_iso}}
                        })
                    except Exception as e:
                        print(f"⚠️ Impossible de mettre à jour 'Dernier rappel' : {e}")
                    sent += 1

                if RATE_LIMIT_MS:
                    await asyncio.sleep(RATE_LIMIT_MS / 1000.0)

        mode = "simulation" if DRY_RUN else "réel"
        print(f"(Send) Rappels envoyés ({mode}) : {sent}")
        return sent
    finally:
        pass


# --------------------------- Wrappers sync pour Streamlit ---------------------------
def run_sync_from_forms_sync() -> int:
    """Wrapper synchrone pour Streamlit : retourne le nombre de cases mises à jour."""
    try:
        return asyncio.run(sync_notion_checkbox_from_forms())
    except RuntimeError as e:
        if "asyncio.run() cannot be called from a running event loop" in str(e):
            loop = asyncio.new_event_loop()
            try:
                asyncio.set_event_loop(loop)
                return loop.run_until_complete(sync_notion_checkbox_from_forms())
            finally:
                loop.close()
        raise


def run_send_reminders_sync() -> int:
    """Wrapper synchrone pour Streamlit : retourne le nombre de rappels envoyés."""
    try:
        return asyncio.run(send_reminders())
    except RuntimeError as e:
        if "asyncio.run() cannot be called from a running event loop" in str(e):
            loop = asyncio.new_event_loop()
            try:
                asyncio.set_event_loop(loop)
                return loop.run_until_complete(send_reminders())
            finally:
                loop.close()
        raise


# Exécution directe (debug)
if __name__ == "__main__":
    async def main():
        up = await sync_notion_checkbox_from_forms()
        se = await send_reminders()
        print(f"(Done) sync_updated={up}, sent={se}")
    asyncio.run(main())