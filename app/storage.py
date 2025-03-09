import json
import os


def save_to_json(data, json_path="data/extracted_data.json"):
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as file:
            existing_data = json.load(file)
    else:
        existing_data = []

    existing_data.append(data)

    with open(json_path, "w", encoding="utf-8") as file:
        json.dump(existing_data, file, ensure_ascii=False, indent=4)
