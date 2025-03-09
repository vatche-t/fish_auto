import fitz
import re
import logging
import unicodedata
from typing import Dict, Any, Optional
from dataclasses import dataclass

# Set up logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("PayslipExtractor")


@dataclass
class PayslipData:
    """Data class to store structured payslip information."""

    name: Optional[str] = None
    family_name: Optional[str] = None
    national_code: Optional[str] = None
    personnel_number: Optional[str] = None
    insurance_number: Optional[str] = None
    company_name: Optional[str] = None
    year: Optional[str] = None
    month: Optional[str] = None
    standard_working_days: Optional[str] = None
    base_salary: Optional[str] = None
    housing_allowance: Optional[str] = None
    food_allowance: Optional[str] = None
    total_salary: Optional[str] = None
    employee_insurance: Optional[str] = None
    food_expense: Optional[str] = None
    total_deductions: Optional[str] = None
    net_payment: Optional[str] = None
    net_payment_text: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert dataclass to dictionary."""
        return {k: v for k, v in self.__dict__.items() if v is not None}


class PayslipExtractor:
    """Persian payslip data extractor with detailed debugging."""

    def __init__(self, debug=True):
        self.logger = logger
        self.debug = debug

    def extract_from_file(self, pdf_path: str) -> PayslipData:
        """Extract payslip data from a PDF file."""
        try:
            with fitz.open(pdf_path) as doc:
                text = ""
                for page in doc:
                    text += page.get_text()
                self.logger.info("Successfully extracted text from PDF")
                if self.debug:
                    print("\n==== FULL EXTRACTED TEXT ====")
                    print(text)
                    print("============================\n")
                return self._process_text(text)
        except Exception as e:
            self.logger.error(f"Error extracting data: {str(e)}")
            raise

    def _extract_from_line(self, lines, keywords, pattern):
        """Extract value from a line containing any of the keywords."""
        for line in lines:
            if any(keyword in line for keyword in keywords):
                match = re.search(pattern, line)
                if match:
                    try:
                        return match.group(1).strip()
                    except IndexError:
                        self.logger.warning(f"No group found for pattern {pattern} in line: {line}")
                        return None
        return None

    def _process_text(self, text: str) -> PayslipData:
        """Process extracted text and populate PayslipData."""
        payslip = PayslipData()
        lines = text.splitlines()
        # Normalize text to handle Unicode variations
        clean_lines = [unicodedata.normalize("NFC", line.strip()) for line in lines if line.strip()]

        if self.debug:
            print("\n==== EXTRACTED LINES ====")
            for i, line in enumerate(clean_lines):
                print(f"Line {i}: {repr(line)}")
            print("=========================\n")

        # Extract Name and Family Name
        if len(clean_lines) >= 3:
            name_line = clean_lines[1]
            if ":" in name_line:
                parts = name_line.split(":")
                payslip.name = parts[0].strip()  # Set name to the part before the first colon
                payslip.family_name = clean_lines[2].strip()  # Set family name to the next line

        if self.debug:
            print(f"Extracted name: {payslip.name}")
            print(f"Extracted family name: {payslip.family_name}")

        # Define extraction rules for other fields
        extraction_rules = {
            "national_code": (["ﮐﺪ ﻣﻠﯽ"], r"(\d{10})"),
            "personnel_number": (["ﭘﺮﺳﻨﻠﯽ"], r"(\d+)"),
            "insurance_number": (["ﺑﯿﻤﻪ"], r"(\d+)"),
            "company_name": (["ﺷﺮﮐﺖ"], r"ﺷﺮﮐﺖ\s+([\u0600-\u06FF\s]+)"),
            "year": ([], r"^(\d{4})$"),  # First line if 4 digits
            "month": (["ﺑﻬﻤﻦ"], r"(ﺑﻬﻤﻦ)"),
            "standard_working_days": (["ﮐﺎﺭﮐﺮﺩ ﻋﺎﺩﯼ"], r"(\d+[\/\.]\d+|\d+)"),
            "base_salary": (["ﺣﻘﻮﻕ ﭘﺎﯾﻪ"], r"([\d,]+)"),
            "housing_allowance": (["ﺣﻖ ﻣﺴﮑﻦ"], r"([\d,]+)"),
            "food_allowance": (["ﺧﻮﺍﺭﻭﺑﺎﺭ"], r"([\d,]+)"),
            "total_salary": (["ﺣﻘﻮﻕ ﻭ ﻣﺰﺍﯾﺎ"], r"([\d,]+)"),
            "employee_insurance": (["ﺑﯿﻤﻪ ﺳﻬﻢ ﮐﺎﺭﻣﻨﺪ"], r"([\d,]+)"),
            "food_expense": (["ﻫﺰﯾﻨﻪ ﻏﺬﺍ"], r"([\d,]+)"),
            "total_deductions": (["ﺟﻤﻊ ﮐﺴﻮﺭ"], r"([\d,]+)"),
            "net_payment": (["ﺧﺎﻟﺺ ﭘﺮﺩﺍﺧﺘﯽ"], r"([\d,]+)"),
            "net_payment_text": (["ﺧﺎﻟﺺ ﭘﺮﺩﺍﺧﺘﯽ"], r"[\d,]+([^\n\r]+)"),
        }

        # Apply extraction rules
        for field, (keywords, pattern) in extraction_rules.items():
            if field == "year" and re.match(r"^\d{4}$", clean_lines[0]):
                payslip.year = clean_lines[0]
            else:
                value = self._extract_from_line(clean_lines, keywords, pattern)
                if value:
                    if field in [
                        "base_salary",
                        "housing_allowance",
                        "food_allowance",
                        "total_salary",
                        "employee_insurance",
                        "food_expense",
                        "total_deductions",
                        "net_payment",
                    ]:
                        value = value.replace(",", "")
                    setattr(payslip, field, value)
            if self.debug and getattr(payslip, field):
                print(f"Extracted {field}: {getattr(payslip, field)}")

        return payslip

    def extract_to_dict(self, pdf_path: str) -> Dict[str, Any]:
        """Extract payslip data and return it as a dictionary."""
        payslip_data = self.extract_from_file(pdf_path)
        return payslip_data.to_dict()


# Example usage
if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) != 2:
        print("Usage: python payslip_extractor.py <pdf_file_path>")
        sys.exit(1)

    pdf_file = sys.argv[1]
    extractor = PayslipExtractor(debug=True)
    payslip_data = extractor.extract_from_file(pdf_file)
    result = payslip_data.to_dict()
    print("\n==== FINAL RESULT ====")
    print(json.dumps(result, ensure_ascii=False, indent=2))
