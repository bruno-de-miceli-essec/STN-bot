import os
import requests
from quart import make_response, Response, Quart, request, jsonify
from dotenv import load_dotenv

# Chargement des variables d’environnement
load_dotenv()

app = Quart(__name__)

# === CONSTANTES ===
VERIFY_TOKEN = os.getenv("FB_VERIFY_TOKEN")
PAGE_ACCESS_TOKEN = os.getenv("FB_PAGE_ACCESS_TOKEN")
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_RESPONSES_DATABASE_ID = os.getenv("NOTION_RESPONSES_DATABASE_ID")

NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28"
}


# === UTILS ===
def send_messenger_message(psid, message):
    url = "https://graph.facebook.com/v18.0/me/messages"
    params = {"access_token": PAGE_ACCESS_TOKEN}
    payload = {
        "recipient": {"id": psid},
        "message": {"text": message}
    }
    response = requests.post(url, params=params, json=payload)
    if response.status_code != 200:
        print(f"❌ Erreur lors de l’envoi à {psid} : {response.text}")
    else:
        print(f"✅ Message envoyé à {psid}")


def query_notion_database(database_id):
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    response = requests.post(url, headers=NOTION_HEADERS)
    if response.status_code != 200:
        raise Exception(f"❌ Requête Notion échouée : {response.text}")
    return response.json()


# === ROUTES ===

@app.route("/", methods=["GET"])
async def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        print("✅ Webhook vérifié")
        return await make_response(challenge, 200)
    else:
        print("❌ Échec de la vérification du webhook")
        return await make_response("Forbidden", 403)


@app.route("/webhook", methods=["POST"])
async def handle_messages():
    data = await request.get_json()
    for entry in data.get("entry", []):
        for messaging_event in entry.get("messaging", []):
            if messaging_event.get("message"):
                sender_id = messaging_event["sender"]["id"]
                message_text = messaging_event["message"].get("text", "")
                print(f"📩 Message reçu de {sender_id} : {message_text}")
                send_messenger_message(sender_id, "Merci pour ton message 😇")
    return jsonify(status="ok")


@app.route("/forms-trigger", methods=["POST"])
async def handle_forms_trigger():
    print("🚀 Webhook Forms Trigger reçu")
    await check_responses_and_send_messages()
    return jsonify(status="messages sent")


# === LOGIQUE PRINCIPALE ===
async def check_responses_and_send_messages():
    print("📥 Lancement de check_responses_and_send_messages()")
    try:
        data = query_notion_database(NOTION_RESPONSES_DATABASE_ID)
        results = data.get("results", [])
        print(f"🔍 {len(results)} entrées trouvées dans Notion")

        for result in results:
            try:
                props = result["properties"]
                psid = props["psid"]["rich_text"][0]["plain_text"]
                has_not_replied = props["n'a pas répondu"]["checkbox"]

                if has_not_replied:
                    message = "N'oublie pas de remplir le formulaire 😇"
                    send_messenger_message(psid, message)
                    print(f"📤 Message envoyé à {psid}")
                else:
                    print(f"✔️ {psid} a déjà répondu, aucun message envoyé.")

            except Exception as e:
                print(f"⚠️ Erreur lors du traitement d’une ligne : {e}")

    except Exception as e:
        print(f"❌ Erreur globale dans check_responses_and_send_messages : {e}")


# === LANCEMENT LOCAL ===
if __name__ == "__main__":
    app.run()