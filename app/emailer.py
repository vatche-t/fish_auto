import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv
import os

load_dotenv()


def send_email(receiver_email, pdf_path):
    sender_email = os.getenv("EMAIL_ADDRESS")
    password = os.getenv("EMAIL_PASSWORD")
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT"))

    msg = EmailMessage()
    msg["From"] = sender_email
    msg["To"] = receiver_email
    msg["Subject"] = "Attached PDF Document"
    msg.set_content("Please find your document attached.")

    with open(pdf_path, "rb") as file:
        file_data = file.read()
        file_name = os.path.basename(pdf_path)
        msg.add_attachment(file_data, maintype="application", subtype="pdf", filename=file_name)

    with smtplib.SMTP(smtp_server, smtp_port) as smtp:
        smtp.starttls()
        smtp.login(sender_email, password)
        smtp.send_message(msg)
