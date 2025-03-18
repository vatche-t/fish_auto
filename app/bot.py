# bot.py
import os
import requests
from flask import Flask, request, jsonify
from app.db_export import init_db, Payslip

BOT_TOKEN = os.getenv("BOT_TOKEN")
BASE_URL = f"https://tapi.bale.ai/bot{BOT_TOKEN}/"

app = Flask(__name__)

def send_message(chat_id, text):
    """Send a text message via Bale Bot API."""
    url = BASE_URL + "sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    requests.post(url, json=payload)

@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle incoming webhook updates from Bale."""
    update = request.get_json()
    if not update:
        return jsonify({"ok": False, "description": "No update found"}), 400

    if "message" in update:
        message = update["message"]
        chat_id = message["chat"]["id"]
        text = message.get("text", "").strip()

        # When the user sends /start, ask for their national code in Persian.
        if text.lower() == "/start":
            send_message(chat_id, "سلام! لطفاً کد ملی خود را وارد کنید:")
        else:
            # Validate if the message is a valid 10-digit national code.
            if len(text) == 10 and text.isdigit():
                # Update all Payslip records with the matching national code to include this chat_id.
                updated = (Payslip
                           .update(chat_id=str(chat_id))
                           .where(Payslip.national_code == text)
                           .execute())
                if updated:
                    send_message(chat_id, f"کد ملی {text} ثبت شد. شناسه چت شما ذخیره گردید.")
                else:
                    # If no payslip record exists, you could choose to create a placeholder,
                    # or simply inform the user that no payroll info is available.
                    send_message(chat_id, "برای این کد ملی سابقه‌ای یافت نشد. لطفاً بعداً دوباره تلاش کنید.")
            else:
                send_message(chat_id, "لطفاً یک کد ملی ۱۰ رقمی معتبر ارسال کنید.")
    return jsonify({"ok": True})

if __name__ == '__main__':
    init_db()  # Ensure the database is initialized (Payslip table exists)
    port = int(os.getenv("PORT", 5000))
    # Run the Flask server (ensure your deployment provides HTTPS)
    app.run(host='0.0.0.0', port=port)
