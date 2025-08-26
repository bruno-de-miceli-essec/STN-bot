import os
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}


class FormManager:
    def __init__(self, database_id=DATABASE_ID):
        self.database_id = database_id
        self.headers = HEADERS
        self.base_url = "https://api.notion.com/v1/"

    def fetch_forms(self):
        url = f"{self.base_url}databases/{self.database_id}/query"
        has_more = True
        next_cursor = None
        results = []

        while has_more:
            payload = {"start_cursor": next_cursor} if next_cursor else {}
            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            data = response.json()
            results.extend(data.get("results", []))
            has_more = data.get("has_more", False)
            next_cursor = data.get("next_cursor")

        return results

    def parse_form(self, page):
        props = page.get("properties", {})
        return {
            "id": page["id"],
            "name": props.get("Nom du formulaire", {}).get("title", [{}])[0].get("plain_text", ""),
            "link": props.get("Lien du Google Form", {}).get("url", ""),
            "creator": props.get("Créateur", {}).get("people", [{}])[0].get("id", ""),
            "submitted": props.get("Soumis", {}).get("checkbox", False),
            "timestamp": props.get("Horodatage de soumission", {}).get("date", {}).get("start", None),
            "target": props.get("Destinataires", {}).get("multi_select", []),
        }

    def get_forms_by_user(self, user_id):
        pages = self.fetch_forms()
        return [self.parse_form(p) for p in pages if self.parse_form(p)["creator"] == user_id]

    def create_followup_form(self, original_form, target_user_id):
        url = f"{self.base_url}pages"
        new_data = {
            "parent": {"database_id": self.database_id},
            "properties": {
                "Nom du formulaire": {
                    "title": [{"text": {"content": f"[Relance] {original_form['name']}"}}]
                },
                "Lien du Google Form": {"url": original_form["link"]},
                "Créateur": {"people": [{"id": original_form["creator"]}]},
                "Soumis": {"checkbox": False},
                "Destinataires": {
                    "multi_select": [{"name": target_user_id}]
                },
            },
        }

        response = requests.post(url, headers=self.headers, json=new_data)
        response.raise_for_status()
        return response.json()

    def send_reminder(self, form):
        print(f"🔔 Rappel envoyé pour : {form['name']} à {form['target']}")

    def run_reminders(self):
        pages = self.fetch_forms()
        for page in pages:
            form = self.parse_form(page)
            if not form["submitted"]:
                self.send_reminder(form)

    def run_creation(self, creator_id, targets):
        forms = self.get_forms_by_user(creator_id)
        for form in forms:
            for target in targets:
                self.create_followup_form(form, target)
                print(f"✅ Formulaire de relance créé pour {target} : {form['name']}")

    def process_webhook(self, data):
        # Implémenter ici le traitement des événements webhook spécifiques si nécessaire
        return "Webhook reçu et traité"



# Ajout de la fonction handle_webhook accessible à l'import
def handle_webhook(data):
    form_manager = FormManager()
    return form_manager.process_webhook(data)