import json
import os
import re
import requests
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

URLS = {
    "23 Sep": "https://in.bookmyshow.com/movies/hyderabad/the-paradise/buytickets/ET00518274/20260923?etCodes=*&language=telugu&refEventCode=ET00518274",
    "24 Sep": "https://in.bookmyshow.com/movies/hyderabad/the-paradise/buytickets/ET00518274/20260924?etCodes=*&language=telugu&refEventCode=ET00518274",
}

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT = os.environ["TELEGRAM_CHAT_ID"]
BROWSERLESS_TOKEN = os.environ["BROWSERLESS_TOKEN"]

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

def extract_times(text, date_label):
    # Keep only clock-looking values. The selected BookMyShow date page
    # is used as the source, and duplicate times are removed.
    found = []
    seen = set()

    for raw_time, meridiem in re.findall(
        r"\b([0-9]{1,2}:[0-9]{2})\s*(AM|PM)\b", text, re.I
    ):
        hour, minute = map(int, raw_time.split(":"))
        meridiem = meridiem.upper()

        if not (1 <= hour <= 12 and 0 <= minute <= 59):
            continue

        if date_label == "24 Sep":
            if meridiem != "AM" or hour >= 8:
                continue

        normalized = f"{hour:02d}:{minute:02d} {meridiem}"
        if normalized not in seen:
            seen.add(normalized)
            found.append(normalized)

    return found

def get_page_text(browser, url):
    page = browser.new_page(viewport={"width": 1440, "height": 1200})
    try:
        print("Opening:", url)
        page.goto(url, wait_until="domcontentloaded", timeout=60000)

        # Allow the client-rendered show listings to settle.
        page.wait_for_timeout(6000)

        title = page.title()
        print("Page title:", title)

        text = page.locator("body").inner_text(timeout=30000)
        print("Page text length:", len(text))

        if len(text.strip()) < 200:
            raise RuntimeError("BookMyShow page returned unexpectedly little visible content.")

        return text
    finally:
        page.close()

matches = []

with sync_playwright() as p:
    ws_endpoint = (
        "wss://production-sfo.browserless.io/chromium/playwright"
        f"?token={BROWSERLESS_TOKEN}"
    )

    browser = p.chromium.connect(ws_endpoint)
    try:
        for date_label, url in URLS.items():
            try:
                text = get_page_text(browser, url)
                times = extract_times(text, date_label)
                print(f"{date_label} matching times:", times)

                for time in times:
                    matches.append((date_label, time))
            except PlaywrightTimeoutError as exc:
                print(f"Timeout while checking {date_label}: {exc}")
            except Exception as exc:
                print(f"Error while checking {date_label}: {exc}")
    finally:
        browser.close()

print("All matching shows detected:", matches)

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

    msg += "\nBookMyShow:\n" + URLS["24 Sep"]
    send(msg)
    print("Sent alert for:", new)
else:
    print("No new matching show. No Telegram alert sent.")

save(state)
