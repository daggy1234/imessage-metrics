"""
iMessage analysis — reads messages.json and prints stats + time-of-day plot.
"""

import json
import os
import re
from collections import Counter, defaultdict
from datetime import datetime

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DATA_FILE = os.path.join(os.path.dirname(__file__), "messages.json")
OUTPUT_CSV = os.path.join(os.path.dirname(__file__), "out.csv")
OUTPUT_PNG = os.path.join(os.path.dirname(__file__), "text_time.png")
TOP_N = 20

with open(DATA_FILE) as f:
    data = json.load(f)

messages = data["messages"]
print(f"Loaded {len(messages):,} messages from {DATA_FILE}\n")

sent_bodies: list[str] = []
sent_words: list[str] = []
sent_times: list = []
people_i_text: list[str] = []
people_text_me: list[str] = []
group_chats: list[str] = []
sent_count = 0
recv_count = 0

person_sent: dict[str, int] = defaultdict(int)
person_recv: dict[str, int] = defaultdict(int)

all_dates: list[str] = []
sent_lengths: list[int] = []
emoji_counter: Counter = Counter()
double_text_count = 0
late_night_count = 0

EMOJI_RE = re.compile(
    "["
    "\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF"
    "\U0001F1E0-\U0001F1FF"
    "\U00002702-\U000027B0"
    "\U0000FE00-\U0000FE0F"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FA6F"
    "\U0001FA70-\U0001FAFF"
    "\U00002600-\U000026FF"
    "\U0000200D"
    "\U00002764"
    "]+",
    flags=re.UNICODE,
)

prev_from_me = False

for msg in messages:
    is_gc = bool(msg.get("group_chat_name"))
    identifier = msg.get("contact_name") or msg["phone_number"]
    body = (msg.get("body") or "").strip()
    date_str = msg.get("date", "")

    if date_str:
        all_dates.append(date_str)

    if msg["is_from_me"]:
        sent_count += 1

        if body:
            sent_bodies.append(body)
            sent_words.extend(body.lower().split())
            sent_lengths.append(len(body))
            for e in EMOJI_RE.findall(body):
                emoji_counter.update(list(e))

        if prev_from_me:
            double_text_count += 1
        prev_from_me = True

        try:
            ts = pd.Timestamp(date_str)
            sent_times.append(ts.floor("min").time())
            if ts.hour < 5:
                late_night_count += 1
        except Exception:
            pass

        if is_gc:
            group_chats.append(msg["group_chat_name"])
        else:
            people_i_text.append(identifier)
            person_sent[identifier] += 1
    else:
        recv_count += 1
        prev_from_me = False
        if is_gc:
            group_chats.append(msg["group_chat_name"])
        else:
            people_text_me.append(identifier)
            person_recv[identifier] += 1


def print_ranking(title: str, items: list[str], n: int = TOP_N) -> None:
    print(f"\n{'─' * 55}")
    print(f"  {title}")
    print(f"{'─' * 55}")
    for i, (item, count) in enumerate(Counter(items).most_common(n), 1):
        label = item if item else "(unknown)"
        print(f"  {i:>3}. {label:<35s} {count:>6,}")
    print()


def section(title: str) -> None:
    print(f"\n{'─' * 55}")
    print(f"  {title}")
    print(f"{'─' * 55}")


print(f"📊  Total messages: {len(messages):,}")
print(f"    Sent:     {sent_count:>8,}")
print(f"    Received: {recv_count:>8,}")
print(f"    Ratio:    You send 1 for every {recv_count / max(sent_count, 1):.1f} received")

print_ranking("🔤  Top Message Bodies (sent)", sent_bodies)
print_ranking("🔠  Top Words Used (sent)", sent_words)
print_ranking("📤  Top People I Text", people_i_text)
print_ranking("📥  Top People Who Text Me", people_text_me)
print_ranking("👥  Top Group Chats", group_chats)

section("🎯  Fun Stats")

avg_len = sum(sent_lengths) / max(len(sent_lengths), 1)
print(f"  📏  Avg message length:         {avg_len:.0f} chars")
print(f"  🌙  Late night texts (12–5am):  {late_night_count:,}")
print(f"  ✌️   Double texts sent:          {double_text_count:,}")
print(f"  📱  Total unique contacts:      {len(set(person_sent) | set(person_recv)):,}")

if all_dates:
    days = []
    for d in all_dates:
        try:
            days.append(pd.Timestamp(d).day_name())
        except Exception:
            pass
    if days:
        print(f"\n  📅  Busiest days of the week:")
        for day, count in Counter(days).most_common():
            bar = "█" * (count // (len(days) // 50 or 1))
            print(f"      {day:<12s} {count:>6,}  {bar}")

if emoji_counter:
    print(f"\n  😀  Top emojis sent:")
    for i, (emoji, count) in enumerate(emoji_counter.most_common(10), 1):
        print(f"      {i:>2}. {emoji}  × {count:,}")

if all_dates:
    day_dates = []
    for d in all_dates:
        try:
            day_dates.append(pd.Timestamp(d).strftime("%Y-%m-%d"))
        except Exception:
            pass
    if day_dates:
        print(f"\n  🔥  Busiest single days:")
        for i, (day, count) in enumerate(Counter(day_dates).most_common(10), 1):
            print(f"      {i:>2}. {day}   {count:>5,} messages")

print()

if sent_times:
    counts = Counter(sent_times)
    df = pd.DataFrame(list(counts.items()), columns=["Time", "Count"])
    today = datetime.now().date()
    df["Time"] = [datetime.combine(today, t) for t in df["Time"]]
    df = df.groupby(pd.Grouper(key="Time", freq="15min")).sum()
    df.to_csv(OUTPUT_CSV)

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.fill_between(df.index, df["Count"], alpha=0.4)
    ax.plot(df.index, df["Count"], linewidth=1.5)
    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%H:%M"))
    ax.xaxis.set_major_locator(matplotlib.dates.HourLocator(interval=2))
    ax.set_xlabel("Time of Day")
    ax.set_ylabel("Messages Sent")
    ax.set_title("Texting Activity by Time of Day")
    fig.tight_layout()
    fig.savefig(OUTPUT_PNG, dpi=150)
    print(f"📈  Saved time-of-day plot → {OUTPUT_PNG}")
    print(f"📄  Saved CSV data         → {OUTPUT_CSV}")
else:
    print("No sent messages with valid timestamps — skipping plot.")
