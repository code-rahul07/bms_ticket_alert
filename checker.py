import json
import os
import re
import requests
from bs4 import BeautifulSoup

URL = "https://in.bookmyshow.com/movies/hyderabad/the-paradise/buytickets/ET00518274/20260924?etCodes=*&language=telugu&refEventCode=ET00518274"

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT = os.environ["TELEGRAM_CHAT_ID"]

def send(msg):
    response = requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        json={"chat_id": CHAT, "text": msg},
        timeout=20,
    )
    print("Telegram response:", response.text)
    response.raise_for_status()
    data = response.json()
    if not data.get("ok"):
        raise RuntimeError(f"Telegram API error: {data}")

def load():
    with open("last_seen.json", encoding="utf-8") as f:
        return json.load(f)

def save(data):
    with open("last_seen.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

response = requests.get(URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
response.raise_for_status()
print("BookMyShow HTTP status:", response.status_code)

soup = BeautifulSoup(response.text, "html.parser")
page_text = soup.get_text(" ", strip=True)

# The page URL supplied by the user is for 24 Sep.
# Detect only early-morning shows strictly before 08:00 AM.
matches = []
for t in re.findall(r"\b([0-9]{1,2}:[0-9]{2})\s*(AM|PM)\b", page_text, re.I):
    hour, minute = map(int, t[0].split(":"))
    meridiem = t[1].upper()
    if meridiem == "AM" and (hour < 8):
        matches.append(("24 Sep", f"{hour:02d}:{minute:02d} AM"))

print("Matching shows detected:", matches)

state = load()
seen = set(state.get("shows", []))
new = []

for date, time in matches:
    key = f"{date}-{time}"
    if key not in seen:
        seen.add(key)
        new.append((date, time))

state["shows"] = sorted(seen)

if new:
    msg = "🎟 The Paradise Ticket Alert\n\n"
    for date, time in new:
        msg += f"{date} • {time}\n"
    msg += "\nOpen BookMyShow:\n" + URL
    send(msg)
    print("Sent alert for:", new)
else:
    print("No new matching show. No Telegram alert sent.")

save(state)
