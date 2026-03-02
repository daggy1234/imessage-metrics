"""
Dump full conversation with a contact by phone number.
Reads chat.db directly (no year filter).

Usage: python3 dump_conversation.py +17044307408
"""

import datetime
import json
import os
import re
import sqlite3
import sys

IMESSAGE_DB = os.path.expanduser("~/Library/Messages/chat.db")
CONTACTS_FILE = os.path.join(os.path.dirname(__file__), "contacts.json")

_APPLE_EPOCH = datetime.datetime(2001, 1, 1)
_APPLE_EPOCH_UNIX = int(_APPLE_EPOCH.timestamp())
_NS_PER_SEC = 1_000_000_000


def _apple_ns_to_str(ns):
    if ns is None:
        return ""
    try:
        return datetime.datetime.fromtimestamp((ns / _NS_PER_SEC) + _APPLE_EPOCH_UNIX).strftime("%Y-%m-%d %H:%M:%S")
    except (OSError, ValueError):
        return ""


def _extract_body(attributed_body):
    if not attributed_body:
        return ""
    decoded = attributed_body.decode("utf-8", errors="replace")
    if "NSNumber" in decoded:
        decoded = decoded.split("NSNumber")[0]
        if "NSString" in decoded:
            decoded = decoded.split("NSString")[1]
            if "NSDictionary" in decoded:
                return decoded.split("NSDictionary")[0][6:-12]
    return ""


def _load_contact_name(phone):
    if not os.path.exists(CONTACTS_FILE):
        return None
    try:
        with open(CONTACTS_FILE) as f:
            entries = json.load(f)
    except (json.JSONDecodeError, ValueError):
        return None
    digits = re.sub(r"[^\d]", "", phone)
    if len(digits) == 10:
        digits = "1" + digits
    norm = "+" + digits
    for entry in entries:
        if "phone" not in entry:
            continue
        d = re.sub(r"[^\d]", "", entry["phone"])
        if len(d) == 10:
            d = "1" + d
        if "+" + d == norm:
            return entry.get("name")
    return None


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 dump_conversation.py <phone_number>")
        sys.exit(1)

    target = sys.argv[1]
    output = os.path.join(os.path.dirname(__file__), f"conversation_{target.replace('+', '')}.json")

    conn = sqlite3.connect(IMESSAGE_DB)
    cur = conn.cursor()
    rows = cur.execute("""
        SELECT message.date, message.text, message.attributedBody, message.is_from_me
        FROM message
        LEFT JOIN handle ON message.handle_id = handle.ROWID
        WHERE handle.id = ? AND message.cache_roomnames IS NULL
        ORDER BY message.date
    """, (target,)).fetchall()
    conn.close()

    if not rows:
        print(f"No messages found for {target}")
        sys.exit(1)

    contact_name = _load_contact_name(target) or target
    msgs = []
    sent = 0
    for date, text, ab, is_from_me in rows:
        body = text if text else _extract_body(ab)
        if is_from_me:
            sent += 1
        msgs.append({
            "date": _apple_ns_to_str(date),
            "body": body,
            "is_from_me": bool(is_from_me),
        })

    recv = len(msgs) - sent
    result = {
        "contact": contact_name,
        "phone_number": target,
        "total_messages": len(msgs),
        "sent": sent,
        "received": recv,
        "messages": msgs,
    }

    with open(output, "w") as f:
        json.dump(result, f, indent=2)

    print(f"💬  {contact_name} ({target})")
    print(f"    {len(msgs):,} messages  (sent {sent:,} / received {recv:,})")
    print(f"    Saved → {output}")


if __name__ == "__main__":
    main()
