import os
from flask import Flask, request

app = Flask(__name__)

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "SantanaESSEC2526@")

@app.route("/", methods=["GET"])
def index():
    return "ok", 200

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        # Vérification du webhook par Meta
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")

        if mode == "subscribe" and token == VERIFY_TOKEN:
            return challenge or "", 200
        else:
            return "Bad verify token", 403

    elif request.method == "POST":
        data = request.json
        print("Webhook reçu:", data, flush=True)
        # Ici tu pourras appeler scanner.send_message() plus tard
        return "EVENT_RECEIVED", 200

    return "", 400

if __name__ == "__main__":
    port = int(os.getenv("PORT", 3000))
    app.run(host="0.0.0.0", port=port)