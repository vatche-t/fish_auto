import os
import sys
import time
import threading
import requests
import logging
from app.extractor import PayslipExtractor
from app.db_export import init_db, save_to_db, Payslip

# Set up logger for debugging
logger = logging.getLogger("PayrollDebug")
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# BOT_TOKEN should be set in your environment (e.g. in your .env file)
BOT_TOKEN = os.getenv("BOT_TOKEN")
BASE_URL = f"https://tapi.bale.ai/bot{BOT_TOKEN}/"

# --- Bale Bot Helper Functions ---
def send_message(chat_id, text):
    """Send a text message via Bale Bot API."""
    url = BASE_URL + "sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    logger.debug(f"Sending message to {chat_id}: {text}")
    requests.post(url, json=payload)

def send_document(chat_id, file_path, caption=None):
    """Send a PDF file via Bale Bot API."""
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
    """
    Process a single PDF payslip: extract data from inside the PDF,
    store the extracted data along with the file path in the database,
    and if a chat_id is already registered for the extracted national code,
    send the payroll summary and file to that user.
    """
    logger.debug(f"Processing file: {pdf_path}")
    try:
        extractor = PayslipExtractor()
        payslip_data = extractor.extract_from_file(pdf_path)
        payslip_dict = payslip_data.to_dict()
        # Use absolute path for clarity
        abs_pdf_path = os.path.abspath(pdf_path)
        payslip_dict["pdf_path"] = abs_pdf_path
        logger.debug(f"Extracted data: {payslip_dict}")
        logger.debug(f"Storing pdf_path: {abs_pdf_path}")
        save_to_db(payslip_dict)
        
        national_code = payslip_dict.get("national_code")
        if national_code:
            logger.debug(f"Looking up record for national code: {national_code}")
            record = (Payslip
                      .select()
                      .where((Payslip.national_code == national_code) & (Payslip.chat_id.is_null(False)))
                      .first())
            if record:
                logger.debug(f"Found record with chat_id {record.chat_id} and pdf_path {record.pdf_path}")
                send_bot_update(record.chat_id, record)
            else:
                logger.debug(f"No record with chat_id found for national code {national_code}")
        else:
            logger.debug("No national code extracted from PDF.")
    except Exception as e:
        logger.error(f"Error processing {pdf_path}: {str(e)}")

def process_all_pdfs():
    """Process all PDF files in the 'input_files' directory."""
    input_dir = "input_files"
    logger.debug(f"Scanning directory {input_dir} for PDF files.")
    for filename in os.listdir(input_dir):
        if filename.lower().endswith(".pdf"):
            pdf_path = os.path.join(input_dir, filename)
            process_pdf(pdf_path)

# --- Bot Update Function ---
def send_bot_update(chat_id, record):
    """
    Use the stored pdf_path from the record to re-extract payroll info,
    build a summary, and send both the summary and the PDF file to the user.
    """
    pdf_path = getattr(record, "pdf_path", None)
    logger.debug(f"send_bot_update: Retrieved pdf_path = {pdf_path}")
    if not pdf_path or not os.path.exists(pdf_path):
        logger.debug("File does not exist at the stored pdf_path.")
        send_message(chat_id, "فایل حقوقی شما یافت نشد.")
        return

    extractor = PayslipExtractor()
    payslip_data = extractor.extract_from_file(pdf_path)
    summary = (
        f"نام: {payslip_data.name}\n"
        f"نام خانوادگی: {payslip_data.family_name}\n"
        f"حقوق کل: {payslip_data.total_salary}\n"
        f"پرداخت خالص: {payslip_data.net_payment}\n"
    )
    logger.debug(f"Sending summary to {chat_id}: {summary}")
    send_message(chat_id, summary)
    send_document(chat_id, pdf_path, caption="فایل حقوقی شما")

# --- Bot Long Polling Functions ---
def get_updates(offset=None, timeout=20):
    """Poll the Bale API for new updates using getUpdates."""
    url = BASE_URL + "getUpdates"
    params = {"timeout": timeout}
    if offset is not None:
        params["offset"] = offset
    logger.debug(f"Polling getUpdates with params: {params}")
    response = requests.get(url, params=params)
    logger.debug(f"getUpdates response: {response.text}")
    return response.json()

def process_update(update):
    """Process a single update from Bale."""
    if "message" in update:
        message = update["message"]
        chat_id = message["chat"]["id"]
        text = message.get("text", "").strip()
        logger.debug(f"Received update from chat {chat_id}: {text}")
        if text.lower() == "/start":
            send_message(chat_id, "سلام! لطفاً کد ملی خود را وارد کنید:")
        else:
            if len(text) == 10 and text.isdigit():
                logger.debug(f"Processing national code input: {text} from chat {chat_id}")
                updated = (Payslip
                           .update(chat_id=str(chat_id))
                           .where(Payslip.national_code == text)
                           .execute())
                if updated:
                    send_message(chat_id, f"کد ملی {text} ثبت شد. شناسه چت شما ذخیره گردید.")
                    record = (Payslip
                              .select()
                              .where((Payslip.national_code == text) & (Payslip.chat_id.is_null(False)))
                              .first())
                    if record:
                        logger.debug(f"Record found for national code {text}: chat_id {record.chat_id}, pdf_path {record.pdf_path}")
                        send_bot_update(chat_id, record)
                    else:
                        logger.debug(f"No record found after updating chat_id for national code {text}")
                else:
                    send_message(chat_id, "برای این کد ملی سابقه‌ای یافت نشد. لطفاً بعداً دوباره تلاش کنید.")
            else:
                send_message(chat_id, "لطفاً یک کد ملی ۱۰ رقمی معتبر ارسال کنید.")

def run_bot():
    """Continuously poll the Bale API for new updates."""
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
        init_db()  # Initialize the database (and create tables if needed)
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        sys.exit(1)
    
    # Start the Bale bot polling in a background thread.
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # Process all payroll PDF files.
    process_all_pdfs()
    
    # Keep the main thread alive so that the bot continues to poll.
    while True:
        time.sleep(1)
