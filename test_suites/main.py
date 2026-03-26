"""
main.py
-------
Entry point. Orchestrates the full pipeline:
  1. Load config
  2. Fetch itinerary emails from Outlook
  3. Parse hotel details from each email
  4. Write results to JSON in /output

Usage:
    cd itinerary_extractor/test_suites
    python main.py
"""

import sys
import os

# Allow imports from /libraries regardless of working directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "libraries"))

from config_loader import load_config
from outlook_reader import fetch_itinerary_emails, get_email_metadata, get_html_body
from hotel_parser import html_to_lines, parse_hotels
from json_writer import build_record, save_to_json


def main():
    print("=" * 55)
    print("  Itinerary Hotel Extractor")
    print("=" * 55)

    # ── 1. Load config ──
    config = load_config()
    outlook_cfg = config["outlook"]
    output_cfg  = config["output"]

    output_dir = os.path.join(os.path.dirname(__file__), "..", "output")

    # ── 2. Fetch matching emails from Outlook ──
    emails = fetch_itinerary_emails(
        keyword=outlook_cfg["subject_keyword"],
        sort_descending=outlook_cfg["sort_descending"],
    )

    if not emails:
        print("No itinerary emails found. Exiting.")
        return

    # ── 3. Parse hotels from each email ──
    all_records = []
    total_hotels = 0

    for msg in emails:
        metadata = get_email_metadata(msg)
        html     = get_html_body(msg)
        lines    = html_to_lines(html)
        hotels   = parse_hotels(lines)

        record = build_record(metadata, hotels)
        all_records.append(record)
        total_hotels += len(hotels)

        print(f"\n📧  {metadata['subject']}")
        if hotels:
            for h in hotels:
                print(f"   🏨  {h['hotel_name']}")
                print(f"       Check-in  : {h['check_in']}")
                print(f"       Check-out : {h['check_out']}")
                print(f"       Conf #    : {h['confirmation_number']}")
                print(f"       Rate      : ${h['rate_usd']} USD")
        else:
            print("   (no hotel bookings found in this email)")

    # ── 4. Save to JSON ──
    output_path = save_to_json(
        all_records,
        output_dir=output_dir,
        filename=output_cfg["filename"],
        indent=output_cfg["indent"],
        encoding=output_cfg["encoding"],
    )

    print(f"\n{'=' * 55}")
    print(f"  Done — {total_hotels} hotel(s) across {len(all_records)} email(s)")
    print(f"  Output → {os.path.abspath(output_path)}")
    print("=" * 55)


if __name__ == "__main__":
    main()
