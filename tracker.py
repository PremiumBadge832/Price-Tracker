#!/usr/bin/env python3
"""
Price Tracker
-------------
Reads a list of product URLs from urls.txt, scrapes the current price
from each page, compares it against the last known price stored in
data/price_history.json, and sends a Discord notification whenever:
  - This is the first time we've seen the product (baseline), OR
  - The price has changed since the last check, OR
  - The page shows any "sale" / "clearance" indicator.

Designed to run unattended via GitHub Actions on a schedule.
"""

import os
import re
import json
import sys
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

URLS_FILE = "urls.txt"
HISTORY_FILE = "data/price_history.json"
DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

PRICE_REGEX = re.compile(r"[\$£€]\s?([\d,]+\.\d{2})")


def load_urls():
    if not os.path.exists(URLS_FILE):
        print(f"No {URLS_FILE} found. Create it with one product URL per line.")
        return []
    with open(URLS_FILE, "r") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]


def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    return {}


def save_history(history):
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)


def fetch_page(url):
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    return resp.text


def extract_price_and_title(html, url):
    soup = BeautifulSoup(html, "html.parser")

    title_tag = soup.find("title")
    h1_tag = soup.find("h1")
    title = (title_tag.get_text(strip=True) if title_tag else None) or \
            (h1_tag.get_text(strip=True) if h1_tag else url)

    candidates = soup.select(
        '[class*="price" i], [id*="price" i], [data-testid*="price" i]'
    )
    for tag in candidates:
        text = tag.get_text(" ", strip=True)
        match = PRICE_REGEX.search(text)
        if match:
            return title, float(match.group(1).replace(",", ""))

    match = PRICE_REGEX.search(soup.get_text(" ", strip=True))
    if match:
        return title, float(match.group(1).replace(",", ""))

    return title, None


def detect_sale(html):
    lowered = html.lower()
    return any(word in lowered for word in ["on sale", "clearance", "instant savings", "special buy"])


def send_discord_alert(message):
    if not DISCORD_WEBHOOK:
        print("DISCORD_WEBHOOK not set — skipping notification. Message was:")
        print(message)
        return
    try:
        resp = requests.post(DISCORD_WEBHOOK, json={"content": message}, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"Failed to send Discord alert: {e}")


def check_url(url, history):
    print(f"Checking: {url}")
    try:
        html = fetch_page(url)
    except requests.RequestException as e:
        print(f"  Error fetching page: {e}")
        return

    title, price = extract_price_and_title(html, url)
    on_sale = detect_sale(html)
    now = datetime.now(timezone.utc).isoformat()

    if price is None:
        print("  Could not find a price on the page. Site markup may have changed.")
        return

    entry = history.get(url, {})
    last_price = entry.get("last_price")
    log = entry.get("log", [])
    log.append({"timestamp": now, "price": price, "on_sale": on_sale})
    log = log[-500:]

    is_first_check = last_price is None
    price_changed = (not is_first_check) and (price != last_price)

    if is_first_check:
        msg = f"📦 **Now tracking**: {title}\n💲 Starting price: **${price:.2f}**\n{url}"
        send_discord_alert(msg)
    elif price_changed:
        direction = "🔻 dropped" if price < last_price else "🔺 increased"
        msg = (
            f"{'🔥' if price < last_price else '⚠️'} **Price {direction}**: {title}\n"
            f"Was **${last_price:.2f}** → now **${price:.2f}**\n"
            f"{url}"
        )
        send_discord_alert(msg)
    elif on_sale:
        msg = f"🏷️ **On sale**: {title}\nCurrent price: **${price:.2f}**\n{url}"
        send_discord_alert(msg)
    else:
        print(f"  No change. Price: ${price:.2f}")

    history[url] = {
        "title": title,
        "last_price": price,
        "last_checked": now,
        "log": log,
    }


def main():
    urls = load_urls()
    if not urls:
        sys.exit(0)

    history = load_history()
    for url in urls:
        check_url(url, history)

    save_history(history)


if __name__ == "__main__":
    main()
