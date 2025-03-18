import os
import sys
import time
import threading
import requests
import logging
import pandas as pd
from datetime import datetime, timedelta
from app.extractor import PayslipExtractor
from app.db_export import init_db, Payslip

# Set up logger
logger = logging.getLogger("PayrollDebug")
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Bot configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
BASE_URL = f"https://tapi.bale.ai/bot{BOT_TOKEN}/"

# Load Excel file for validation
excel_file = "list.xlsx"
df = pd.read_excel(excel_file)
validation_data = df.set_index('شماره ملی')['شماره پرسنلی روی فیشش قبلی'].to_dict()

# Store user states for conversation flow
user_states = {}

# --- Bale Bot Helper Functions ---
def send_message(chat_id, text):
    """Send a text message to the specified chat ID."""
    url = BASE_URL + "sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    logger.debug(f"Sending message to {chat_id}: {text}")
    requests.post(url, json=payload)

def send_document(chat_id, file_path, caption=None):
    """Send a document to the specified chat ID."""
    url = BASE_URL + "sendDocument"
    data = {"chat_id": chat_id, "caption": caption if caption else ""}
    if os.path.exists(file_path):
        logger.debug(f"Sending document {file_path} to {chat_id}")
        with open(file_path, "rb") as doc_file:
            files = {"document": doc_file}
            requests.post(url, data=data, files=files)
    else:
        logger.debug(f"File not found at {file_path}")
        send_message(chat_id, "فایل حقوقی شما یافت نشد.")

# --- PDF Processing Functions ---
def process_pdf(pdf_path):
    """Process a PDF file, extract data, and store it in the database."""
    logger.debug(f"Processing file: {pdf_path}")
    try:
        extractor = PayslipExtractor()
        payslip_data = extractor.extract_from_file(pdf_path)
        payslip_dict = payslip_data.to_dict()
        abs_pdf_path = os.path.abspath(pdf_path)
        payslip_dict["pdf_path"] = abs_pdf_path
        logger.debug(f"Extracted data: {payslip_dict}")
        payslip = Payslip.create(**payslip_dict)
        
        # Check if the user is registered and send an update
        national_code = payslip.national_code
        registered_payslip = Payslip.select().where(
            Payslip.national_code == national_code,
            Payslip.chat_id.is_null(False)
        ).first()
        if registered_payslip:
            send_bot_update(registered_payslip.chat_id, payslip)
    except Exception as e:
        logger.error(f"Error processing {pdf_path}: {str(e)}")

def process_all_pdfs():
    """Scan the input directory and process all PDF files."""
    input_dir = "input_files"
    logger.debug(f"Scanning directory {input_dir} for PDF files.")
    for filename in os.listdir(input_dir):
        if filename.lower().endswith(".pdf"):
            pdf_path = os.path.join(input_dir, filename)
            process_pdf(pdf_path)

# --- Bot Update Function ---
def send_bot_update(chat_id, payslip):
    """Send a payroll summary and PDF to the user."""
    summary = (
        f"نام: {payslip.name}\n"
        f"نام خانوادگی: {payslip.family_name}\n"
        f"حقوق کل: {payslip.total_salary}\n"
        f"پرداخت خالص: {payslip.net_payment}\n"
    )
    send_message(chat_id, summary)
    send_document(chat_id, payslip.pdf_path, caption="فایل حقوقی شما")

# --- Bot Long Polling Functions ---
def get_updates(offset=None, timeout=20):
    """Fetch updates from the Bale API."""
    url = BASE_URL + "getUpdates"
    params = {"timeout": timeout}
    if offset is not None:
        params["offset"] = offset
    logger.debug(f"Polling getUpdates with params: {params}")
    response = requests.get(url, params=params)
    return response.json()

def process_update(update):
    """Process incoming bot updates."""
    if "message" in update:
        message = update["message"]
        chat_id = message["chat"]["id"]
        text = message.get("text", "").strip()
        logger.debug(f"Received update from chat {chat_id}: {text}")

        if text == "/start":
            user_states[chat_id] = {"state": "waiting_for_national_code"}
            send_message(chat_id, "سلام! لطفاً کد ملی خود را وارد کنید:")

        elif text == "/getpayslip":
            handle_getpayslip(chat_id)

        else:
            state_info = user_states.get(chat_id, {})
            state = state_info.get("state")
            if state == "waiting_for_national_code":
                handle_national_code(chat_id, text)
            elif state == "waiting_for_personnel_number":
                handle_personnel_number(chat_id, text, state_info["national_code"])
            else:
                send_message(chat_id, "لطفاً از دستورات موجود استفاده کنید: /start یا /getpayslip")

def handle_national_code(chat_id, text):
    """Handle national code input during registration."""
    text = str(text)
    if text in validation_data:
        user_states[chat_id] = {"state": "waiting_for_personnel_number", "national_code": text}
        send_message(chat_id, "لطفاً شماره پرسنلی خود را وارد کنید:")
    else:
        send_message(chat_id, "کد ملی شما در سیستم یافت نشد. لطفاً دوباره تلاش کنید.")
        user_states.pop(chat_id, None)

def handle_personnel_number(chat_id, text, national_code):
    """Handle personnel number input and complete registration."""
    if str(text) == str(validation_data.get(national_code)):
        Payslip.update(chat_id=str(chat_id)).where(Payslip.national_code == national_code).execute()
        send_message(chat_id, "ثبت نام شما با موفقیت انجام شد. برای دریافت فیش حقوقی از /getpayslip استفاده کنید.")
        user_states.pop(chat_id, None)
    else:
        send_message(chat_id, "شماره پرسنلی اشتباه است. لطفاً دوباره تلاش کنید.")
        user_states.pop(chat_id, None)

def handle_getpayslip(chat_id):
    """Handle the /getpayslip command with a 28-day cooldown."""
    payslip = Payslip.select().where(Payslip.chat_id == str(chat_id)).first()
    if not payslip:
        send_message(chat_id, "شما ثبت نام نکرده‌اید. لطفاً با /start ثبت نام کنید.")
        return

    if payslip.last_request_at and (datetime.now() - payslip.last_request_at) < timedelta(days=28):
        send_message(chat_id, "شما اخیراً درخواست داده‌اید. لطفاً 28 روز صبر کنید.")
        return

    latest_payslip = Payslip.select().where(Payslip.national_code == payslip.national_code).order_by(Payslip.id.desc()).first()
    if latest_payslip:
        send_bot_update(chat_id, latest_payslip)
        Payslip.update(last_request_at=datetime.now()).where(Payslip.chat_id == str(chat_id)).execute()
    else:
        send_message(chat_id, "هیچ فیش حقوقی برای شما یافت نشد.")

def run_bot():
    """Run the bot in a long-polling loop."""
    offset = None
    logger.debug("Bot is polling for updates...")
    while True:
        updates = get_updates(offset=offset)
        if updates.get("ok") and updates.get("result"):
            for update in updates["result"]:
                process_update(update)
                offset = update["update_id"] + 1
        time.sleep(1)

# --- Main Entry Point ---
if __name__ == "__main__":
    try:
        init_db()
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        sys.exit(1)
    
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    process_all_pdfs()
    
    while True:
        time.sleep(1)