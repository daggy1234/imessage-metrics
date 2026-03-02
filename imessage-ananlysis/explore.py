"""
iMessage data extractor — reads chat.db and exports to messages.json.
Set FILTER_YEAR to a year or None for all-time.
"""

import sqlite3
import datetime
import json
import os
import re
import sys

FILTER_YEAR: int | None = 2025
# FILTER_YEAR = None

IMESSAGE_DB = os.path.expanduser("~/Library/Messages/chat.db")
CONTACTS_FILE = os.path.join(os.path.dirname(__file__), "contacts.json")
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "messages.json")

_APPLE_EPOCH = datetime.datetime(2001, 1, 1)
_APPLE_EPOCH_UNIX = int(_APPLE_EPOCH.timestamp())
_NS_PER_SEC = 1_000_000_000


def _year_bounds_ns(year: int) -> tuple[int, int]:
    start = datetime.datetime(year, 1, 1)
    end = datetime.datetime(year + 1, 1, 1)
    start_ns = int((start.timestamp() - _APPLE_EPOCH_UNIX) * _NS_PER_SEC)
    end_ns = int((end.timestamp() - _APPLE_EPOCH_UNIX) * _NS_PER_SEC)
    return start_ns, end_ns


def _apple_ns_to_str(ns: int | None) -> str:
    if ns is None:
        return ""
    unix_ts = (ns / _NS_PER_SEC) + _APPLE_EPOCH_UNIX
    try:
        return datetime.datetime.fromtimestamp(unix_ts).strftime("%Y-%m-%d %H:%M:%S")
    except (OSError, ValueError):
        return ""


def extract_body_attributed(attributed_body: bytes | None) -> str:
    if not attributed_body:
        return ""
    decoded = attributed_body.decode("utf-8", errors="replace")
    if "NSNumber" in decoded:
        decoded = decoded.split("NSNumber")[0]
        if "NSString" in decoded:
            decoded = decoded.split("NSString")[1]
            if "NSDictionary" in decoded:
                decoded = decoded.split("NSDictionary")[0]
                return decoded[6:-12]
    return ""


def _normalize_phone(raw: str) -> str:
    digits = re.sub(r"[^\d]", "", raw)
    if len(digits) == 10:
        digits = "1" + digits
    return "+" + digits


def _load_contacts(path: str) -> dict[str, str]:
    if not os.path.exists(path):
        return {}
    try:
        with open(path) as f:
            entries = json.load(f)
    except (json.JSONDecodeError, ValueError):
        return {}
    lookup: dict[str, str] = {}
    for entry in entries:
        name = entry.get("name", "")
        if not name:
            continue
        if "phone" in entry:
            lookup[_normalize_phone(entry["phone"])] = name
        if "email" in entry:
            lookup[entry["email"].lower()] = name
    return lookup


def read_messages(db_path: str, contacts: dict[str, str], *, self_number: str = "Me") -> list[dict]:
    if not os.path.exists(db_path):
        print(f"ERROR: database not found at {db_path}", file=sys.stderr)
        print("Make sure Full Disk Access is enabled for your terminal.", file=sys.stderr)
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT room_name, display_name FROM chat")
    gc_map = {row[0]: row[1] for row in cursor.fetchall()}

    query = """
        SELECT message.ROWID, message.date, message.text, message.attributedBody,
               handle.id, message.is_from_me, message.cache_roomnames
        FROM message
        LEFT JOIN handle ON message.handle_id = handle.ROWID
    """
    params: tuple = ()
    if FILTER_YEAR is not None:
        start_ns, end_ns = _year_bounds_ns(FILTER_YEAR)
        query += " WHERE message.date >= ? AND message.date < ?"
        params = (start_ns, end_ns)

    results = cursor.execute(query, params).fetchall()
    conn.close()

    messages = []
    for rowid, date, text, attributed_body, handle_id, is_from_me, cache_roomname in results:
        body = text if text else extract_body_attributed(attributed_body)
        identifier = handle_id or self_number
        if identifier and identifier != self_number:
            contact_name = contacts.get(_normalize_phone(identifier)) if identifier.startswith("+") else contacts.get(identifier.lower())
        else:
            contact_name = None
        messages.append({
            "rowid": rowid,
            "date": _apple_ns_to_str(date),
            "body": body,
            "phone_number": identifier,
            "contact_name": contact_name,
            "is_from_me": bool(is_from_me),
            "cache_roomname": cache_roomname,
            "group_chat_name": gc_map.get(cache_roomname),
        })

    return messages


if __name__ == "__main__":
    year_label = str(FILTER_YEAR) if FILTER_YEAR else "all-time"
    print(f"Extracting iMessage data ({year_label}) from {IMESSAGE_DB} ...")

    contacts = _load_contacts(CONTACTS_FILE)
    if contacts:
        print(f"Loaded {len(contacts):,} contact entries from {CONTACTS_FILE}")
    else:
        print(f"No contacts found — run ./dump_contacts first")

    msgs = read_messages(IMESSAGE_DB, contacts)
    print(f"Found {len(msgs):,} messages.")

    with open(OUTPUT_FILE, "w") as f:
        json.dump({"messages": msgs}, f)

    print(f"Saved to {OUTPUT_FILE}")
