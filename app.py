import os
import requests
from flask import Flask, request, abort
from dotenv import load_dotenv

load_dotenv()

NOTION_WEBHOOK_SECRET = os.getenv("NOTION_WEBHOOK_SECRET")
NOTION_PEOPLE_DB_ID = os.getenv("NOTION_PEOPLE_DB_ID")
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
PAGE_TOKEN = os.getenv("PAGE_TOKEN")

app = Flask(__name__)

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

def get_unchecked_people():
    url = f"https://api.notion.com/v1/databases/{NOTION_PEOPLE_DB_ID}/query"
    payload = {
        "filter": {
            "property": "Rappel envoyé",
            "checkbox": {
                "equals": False
            }
        }
    }
    response = requests.post(url, headers=HEADERS, json=payload)
    response.raise_for_status()
    return response.json().get("results", [])

def get_messenger_id(notion_user):
    props = notion_user["properties"]
    messenger_prop = props.get("Messenger ID")
    if messenger_prop and messenger_prop.get("rich_text"):
        return messenger_prop["rich_text"][0]["plain_text"]
    return None

def mark_as_reminded(page_id):
    url = f"https://api.notion.com/v1/pages/{page_id}"
    payload = {
        "properties": {
            "Rappel envoyé": {
                "checkbox": True
            }
        }
    }
    response = requests.patch(url, headers=HEADERS, json=payload)
    response.raise_for_status()

def send_message(psid, text):
    url = "https://graph.facebook.com/v17.0/me/messages"
    payload = {
        "messaging_type": "UPDATE",
        "recipient": {"id": psid},
        "message": {"text": text}
    }
    params = {"access_token": PAGE_TOKEN}
    response = requests.post(url, params=params, json=payload)
    response.raise_for_status()

@app.route("/", methods=["GET"])
def index():
    return "App is running!"

@app.route("/notion-webhook", methods=["POST"])
def notion_webhook():
    if request.headers.get("Authorization") != NOTION_WEBHOOK_SECRET:
        abort(401)

    people = get_unchecked_people()
    for person in people:
        psid = get_messenger_id(person)
        if psid:
            try:
                send_message(psid, "Petit rappel pour compléter le formulaire !")
                mark_as_reminded(person["id"])
            except Exception as e:
                print(f"Erreur pour {psid}: {e}")

    return "OK", 200

if __name__ == "__main__":
    app.run(debug=True)