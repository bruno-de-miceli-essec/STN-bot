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
    if not data:
        return jsonify({"error": "No JSON payload received"}), 400
    psid = data.get("PSID")
    message = data.get("message", "Hello from Notion!")

    if not psid:
        return jsonify({"error": "Missing psid"}), 400

    status, response_text = send_message(psid, message)
    return jsonify({"status": status, "response": response_text}), status

if __name__ == "__main__":
    app.run(debug=True)