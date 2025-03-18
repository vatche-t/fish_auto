import os
import logging

from dotenv import load_dotenv
from peewee import (
    Model,
    CharField,
    DateTimeField,
    PostgresqlDatabase
)

# Load environment variables from .env file
load_dotenv()

# Set up logging for database operations
logger = logging.getLogger("DBExport")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
logger.addHandler(handler)

# Database credentials from .env
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")  # Default to 5432 if not specified

# Validate environment variables (optional but recommended)
missing_vars = [var for var in ["DB_NAME", "DB_USER", "DB_PASSWORD", "DB_HOST"] 
                if not globals().get(var)]
if missing_vars:
    msg = f"Missing required environment variables: {', '.join(missing_vars)}"
    logger.error(msg)
    raise EnvironmentError(msg)

# Set up the PostgreSQL database connection with Peewee
database = PostgresqlDatabase(
    DB_NAME,
    user=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=DB_PORT
)

class Payslip(Model):
    """
    Peewee model for storing payslip data.
    Extend or modify fields as needed.
    """
    name = CharField(null=True)
    family_name = CharField(null=True)
    national_code = CharField(null=True)
    personnel_number = CharField(null=True)
    insurance_number = CharField(null=True)
    company_name = CharField(null=True)
    year = CharField(null=True)
    month = CharField(null=True)
    standard_working_days = CharField(null=True)
    base_salary = CharField(null=True)
    housing_allowance = CharField(null=True)
    food_allowance = CharField(null=True)
    total_salary = CharField(null=True)
    employee_insurance = CharField(null=True)
    food_expense = CharField(null=True)
    total_deductions = CharField(null=True)
    net_payment = CharField(null=True)
    net_payment_text = CharField(null=True)

    # New fields for bot usage
    chat_id = CharField(null=True)       # store user’s chat ID
    last_request_at = DateTimeField(null=True)
    pdf_path = CharField(null=True)

    class Meta:
        database = database

def init_db():
    """
    Initialize the database connection and create the table if it doesn’t exist.
    """
    try:
        database.connect(reuse_if_open=True)
        database.create_tables([Payslip], safe=True)
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        raise

def save_to_db(data_dict):
    """
    Save the extracted payslip data to the database.
    `data_dict` should be a dictionary matching the fields in the Payslip model.
    Example:
        data_dict = {
            "name": "Ali",
            "family_name": "Ahmadi",
            "national_code": "1234567890",
            ...
        }
    """
    try:
        Payslip.create(**data_dict)
        logger.info("Data saved to database successfully.")
    except Exception as e:
        logger.error(f"Error saving data to database: {str(e)}")
        raise
