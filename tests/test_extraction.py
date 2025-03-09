import sys
import os

# Add the project's root directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
sys.path.insert(0, project_root)

from app.extractor import extract_data_from_pdf
import json


def test_extraction():
    pdf_path = os.path.join(project_root, "input_files", "واچه تروسیان.pdf")

    extracted_data = extract_data_from_pdf(pdf_path)

    print(json.dumps(extracted_data, ensure_ascii=False, indent=4))


if __name__ == "__main__":
    test_extraction()
