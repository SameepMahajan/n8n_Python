"""
json_writer.py
--------------
Handles writing extracted hotel data to a JSON output file.
"""

import json
import os


def build_record(metadata: dict, hotels: list[dict]) -> dict:
    """Combine email metadata and hotel list into a single record."""
    return {
        "email_subject": metadata.get("subject"),
        "email_received": metadata.get("received"),
        "hotels": hotels,
    }
//saving in json
def save_to_json(records: list[dict], output_dir: str, filename: str,
                 indent: int = 2, encoding: str = "utf-8") -> str:
    """
    Write records to a JSON file inside output_dir.
    Returns the full path of the saved file.
    """
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, filename)

    with open(filepath, "w", encoding=encoding) as f:
        json.dump(records, f, indent=indent, ensure_ascii=False)

    print(f"[JsonWriter] Saved {len(records)} record(s) → {filepath}")
    return filepath
