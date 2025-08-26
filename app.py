from flask import Flask, request, jsonify
from scanner import handle_webhook

app = Flask(__name__)


@app.route("/notion-webhook", methods=["POST"])
def notion_webhook():
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No data received"}), 400

        # Traitement du webhook Notion
        result = handle_webhook(data)
        return jsonify({"status": "success", "detail": result}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)