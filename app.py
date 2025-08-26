from flask import Flask, request, jsonify
import requests
import os

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