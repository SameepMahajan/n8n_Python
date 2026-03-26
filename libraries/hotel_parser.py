"""
hotel_parser.py
---------------
Parses hotel booking details from the plain-text extracted
from an itinerary email's HTML body.

Strategy: SECTION-BASED parsing
---------------------------------
The email is split into booking sections using date headings as dividers.
Each section is then classified as a FLIGHT or HOTEL block based on its
"Status: Confirmed" line — hotel sections are parsed, flight sections are
skipped entirely. This means the parser is never affected by how many
flight segments appear before or after a hotel block.

Key fix: Fields and values are on SEPARATE lines in this email format:
    Address:                     ← label line
    295 Northern Avenue,...      ← value line (next line)
So we use a "pending label" approach to join them.
"""

import re
from bs4 import BeautifulSoup


# ─────────────────────────────────────────────
# HTML → lines
# ─────────────────────────────────────────────

def html_to_lines(html: str) -> list[str]:
    """
    Convert HTML email body to a cleaned list of non-empty text lines.
    Normalizes non-breaking spaces (\xa0) to regular spaces so all
    regex patterns match correctly.
    """
    soup = BeautifulSoup(html, "lxml")
    full_text = soup.get_text(separator="\n")
    full_tex = full_text.replace("\xa0", " ")  # non-breaking space fix
    return [line.strip() for line in full_text.splitlines() if line.strip()]


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _is_date_heading(line: str) -> bool:
    """
    Return True if the line is a standalone booking-section date heading.
    e.g. 'Tuesday 02 December 2025'  or  'Wednesday 18 February 2026'

    Lines like 'Duration: Tuesday 02 December 2025 - ...' are excluded
    because they start with a label prefix.
    """
    # Exclude lines that begin with a label (e.g. "Duration: ...")
    if re.match(r"^\w[\w\s]*:", line):
        return False
    return bool(re.match(
        r"^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)"
        r"\s+\d{1,2}\s+\w+\s+\d{4}\s*$",
        line, re.IGNORECASE
    ))


def _is_label_only(line: str) -> str | None:
    """
    If the line is a bare label with nothing after the colon (e.g. 'Address:'),
    return the label name. Otherwise return None.
    Known label-only lines in this email format:
        Address:, Check-In:, Check-Out:, Duration:, Rate:, Phone:, Fax:, Email:
    """
    match = re.match(
        r"^(Address|Check-In|Check-Out|Duration|Rate|Phone|Fax|Email)\s*:\s*$",
        line, re.IGNORECASE
    )
    return match.group(1).lower().replace("-", "_") if match else None


# ─────────────────────────────────────────────
# Step 1 — Split into sections
# ─────────────────────────────────────────────

def split_into_sections(lines: list[str]) -> list[list[str]]:
    """
    Split the flat line list into booking sections.
    A new section starts every time a standalone date heading is encountered.
    """
    sections = []
    current = []

    for line in lines:
        if _is_date_heading(line):
            if current:
                sections.append(current)
            current = [line]
        else:
            current.append(line)

    if current:
        sections.append(current)

    return sections


# ─────────────────────────────────────────────
# Step 2 — Classify each section
# ─────────────────────────────────────────────

def _classify_section(section: list[str]) -> str:
    """
    Return 'hotel', 'flight', or 'unknown' based on the Status line
    found anywhere inside the section.
    """
    for line in section:
        if re.search(r"Hotel Confirmation", line, re.IGNORECASE):
            return "hotel"
        if re.search(r"Airline Confirmation", line, re.IGNORECASE):
            return "flight"
    return "unknown"


# ─────────────────────────────────────────────
# Step 3 — Parse a hotel section
# ─────────────────────────────────────────────

def _parse_hotel_section(section: list[str]) -> dict:
    """
    Extract all hotel fields from a hotel section.

    Handles two formats:
      - Inline:  'Address: 295 Northern Avenue'   (label + value on same line)
      - Split:   'Address:'                        (label only)
                 '295 Northern Avenue'             (value on next line)
    """
    hotel = {
        "hotel_name": None,
        "confirmation_number": None,
        "address": None,
        "check_in": None,
        "check_out": None,
        "duration": None,
        "number_of_rooms": None,
        "rate_usd": None,
        "phone": None,
        "fax": None,
        "room_type": None,
        "cancel_policy": None,
        "guarantee": None,
    }

    pending_label = None  # tracks a bare label waiting for its value on the next line

    for idx, line in enumerate(section):

        # ── If previous line was a bare label, this line is its value ──
        if pending_label:
            label = pending_label
            pending_label = None

            if label == "address":
                hotel["address"] = line
            elif label == "check_in":
                hotel["check_in"] = line
            elif label == "check_out":
                hotel["check_out"] = line
            elif label == "duration":
                hotel["duration"] = line
            elif label == "rate":
                rate_match = re.match(r"([\d,.]+)\s*USD", line, re.IGNORECASE)
                hotel["rate_usd"] = rate_match.group(1) if rate_match else line
            elif label == "phone":
                hotel["phone"] = line
            elif label == "fax":
                hotel["fax"] = line
            continue  # value consumed, move to next line

        # ── Check if this line is a bare label ──
        label_key = _is_label_only(line)
        if label_key:
            pending_label = label_key
            continue

        # ── Confirmation number (also extracts hotel name from lines above) ──
        conf_match = re.search(
            r"Status:\s*Confirmed\s*-\s*Hotel Confirmation:\s*(\S+)",
            line, re.IGNORECASE
        )
        if conf_match:
            hotel["confirmation_number"] = conf_match.group(1)
            for back in range(idx - 1, -1, -1):
                candidate = section[back]
                if candidate and not _is_date_heading(candidate):
                    hotel["hotel_name"] = candidate
                    break
            continue

        # ── Inline label: value on same line (fallback) ──
        if re.match(r"Address:", line, re.IGNORECASE):
            hotel["address"] = re.sub(r"^Address:\s*", "", line, flags=re.IGNORECASE).strip()
        elif re.match(r"Check-In:", line, re.IGNORECASE):
            hotel["check_in"] = re.sub(r"^Check-In:\s*", "", line, flags=re.IGNORECASE).strip()
        elif re.match(r"Check-Out:", line, re.IGNORECASE):
            hotel["check_out"] = re.sub(r"^Check-Out:\s*", "", line, flags=re.IGNORECASE).strip()
        elif re.match(r"Duration:", line, re.IGNORECASE):
            val = re.sub(r"^Duration:\s*", "", line, flags=re.IGNORECASE).strip()
            if val:
                hotel["duration"] = val
        elif re.match(r"Rate:", line, re.IGNORECASE):
            raw = re.sub(r"^Rate:\s*", "", line, flags=re.IGNORECASE).strip()
            if raw:
                rate_match = re.match(r"([\d,.]+)\s*USD", raw, re.IGNORECASE)
                hotel["rate_usd"] = rate_match.group(1) if rate_match else raw
        elif re.match(r"Phone:", line, re.IGNORECASE):
            val = re.sub(r"^Phone:\s*", "", line, flags=re.IGNORECASE).strip()
            if val:
                hotel["phone"] = val
        elif re.match(r"Fax:", line, re.IGNORECASE):
            val = re.sub(r"^Fax:\s*", "", line, flags=re.IGNORECASE).strip()
            if val:
                hotel["fax"] = val
        elif re.match(r"NUMBER OF ROOMS:", line, re.IGNORECASE):
            hotel["number_of_rooms"] = re.sub(r"^NUMBER OF ROOMS:\s*", "", line, flags=re.IGNORECASE).strip()
        elif re.match(r"CANCEL", line, re.IGNORECASE):
            hotel["cancel_policy"] = line
        elif re.match(r"ROOM GUARANTEED", line, re.IGNORECASE):
            hotel["guarantee"] = line
        elif re.match(
            r"(HARBOR|ROOM TYPE|DELUXE|STANDARD|KING|QUEEN|DOUBLE|TWIN|SUITE)",
            line, re.IGNORECASE
        ):
            hotel["room_type"] = line

    return hotel


# ─────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────

def parse_hotels(lines: list[str], **kwargs) -> list[dict]:
    """
    Main entry point. Splits the email into sections, classifies each one,
    and parses only the hotel sections.
    """
    sections = split_into_sections(lines)
    hotels = []

    for section in sections:
        section_type = _classify_section(section)
        if section_type == "hotel":
            hotel = _parse_hotel_section(section)
            hotels.append(hotel)
            print(f"[HotelParser] Found hotel: {hotel['hotel_name']} | Conf: {hotel['confirmation_number']}")
        else:
            print(f"[HotelParser] Skipped {section_type} section: {section[0]}")

    return hotels
