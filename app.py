from flask import Flask, request, jsonify
import requests
import os

def send_messages_to_unanswered():
    NOTION_TOKEN = os.getenv("NOTION_TOKEN")
    DATABASE_ID = os.getenv("NOTION_RESPONSES_DB_ID")

    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }

    query_url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    response = requests.post(query_url, headers=headers)
    if response.status_code != 200:
        print("Failed to fetch Notion database:", response.text)
        return

    results = response.json().get("results", [])
    for page in results:
        props = page.get("properties", {})
        psid_field = props.get("PSID", {}).get("rich_text", [])
        reponse_checkbox = props.get("n'a pas répondu", {}).get("checkbox", False)

        if reponse_checkbox and psid_field and "plain_text" in psid_field[0]:
            psid = psid_field[0]["plain_text"]
            print(f"Sending message to PSID: {psid}")
            send_message(psid, "Tu n’as pas encore répondu au formulaire !")

app = Flask(__name__)

# Clé API Messenger (stockée dans les variables d'env Render)
PAGE_TOKEN = os.getenv("PAGE_TOKEN")

@app.route('/')
def home():
    return '✅ Server is running!'

def send_message(psid, message):
    url = f"https://graph.facebook.com/v18.0/me/messages?access_token={PAGE_TOKEN}"
    payload = {
        "recipient": {"id": psid},
        "message": {"text": message}
    }
    response = requests.post(url, json=payload)
    return response.status_code, response.text

@app.route("/notion-webhook", methods=["POST"])
def notion_webhook():
    print("Webhook Notion reçu")
    data = request.json
    print(data)
    if not data:
        return jsonify({"error": "No JSON payload received"}), 400

    notion_psid = data.get("data", {}).get("properties", {}).get("PSID", {}).get("rich_text", [])
    if notion_psid and "plain_text" in notion_psid[0]:
        psid = notion_psid[0]["plain_text"]
    else:
        print("PSID not found in payload")
        return jsonify({"status": "PSID missing"}), 400

    message = data.get("message", "Hello from Notion!")

    print("psid",psid)
    status, response_text = send_message(psid, message)
    return jsonify({"status": status, "response": response_text}), status

if __name__ == "__main__":
    app.run(debug=True)


# Route pour déclencher l'envoi aux non-répondants
@app.route("/forms-trigger", methods=["POST"])
def forms_trigger():
    print("Webhook Forms reçu")
    send_messages_to_unanswered()
    return jsonify({"status": "messages sent"})