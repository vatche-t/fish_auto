import os
import sys
from app.extractor import PayslipExtractor
from app.db_export import init_db, save_to_db
from app.lookup import get_email
from app.emailer import send_email


def process_pdf(pdf_path):
    """
    Process a single PDF payslip: extract data, save to database, and send email if possible.

    Args:
        pdf_path (str): Path to the PDF file to process.
    """
    print(f"Processing file: {pdf_path}")
    try:
        # Create an instance of PayslipExtractor and extract data
        extractor = PayslipExtractor()
        payslip_data = extractor.extract_from_file(pdf_path)
        payslip_dict = payslip_data.to_dict()  # Convert to dictionary for consistency

        # Save the extracted data to the database
        save_to_db(payslip_dict)

        # # Look up email using the national code and send email if found
        # email = get_email(payslip_dict["national_code"])
        # if email:
        #     send_email(email, pdf_path)
        #     print(f"Email successfully sent to: {email}")
        # else:
        #     print(f"No email found for national code: {payslip_dict['national_code']}")
    except Exception as e:
        print(f"Error processing {pdf_path}: {str(e)}")


if __name__ == "__main__":
    # Initialize the database connection
    try:
        init_db()  # Set up database connection and create table if needed
    except Exception as e:
        print(f"Failed to initialize database: {str(e)}")
        sys.exit(1)

    # Process all PDF files in the input directory
    input_dir = "input_files"
    for filename in os.listdir(input_dir):
        if filename.lower().endswith(".pdf"):
            pdf_path = os.path.join(input_dir, filename)
            process_pdf(pdf_path)
