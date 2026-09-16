#!/usr/bin/env python3
"""
X (Twitter) Follower Tracker
Fetches public follower counts for a list of accounts and appends to history.
Designed to run in GitHub Actions every 12 hours.
"""

import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

# Paths
ROOT = Path(__file__).resolve().parent.parent
ACCOUNTS_FILE = ROOT / "accounts.json"
HISTORY_FILE = ROOT / "data" / "history.json"
LATEST_FILE = ROOT / "data" / "latest.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
}


def load_accounts():
    with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def load_history():
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def parse_count(text: str) -> int | None:
    """Convert '5.3K', '12.4M', '1,234' etc. to int."""
    if not text:
        return None
    text = text.strip().replace(",", "").replace(" ", "").upper()
    multipliers = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}
    for suffix, mult in multipliers.items():
        if text.endswith(suffix):
            try:
                return int(float(text[:-1]) * mult)
            except ValueError:
                return None
    try:
        return int(float(text))
    except ValueError:
        return None


def fetch_via_page(username: str) -> int | None:
    """
    Try to extract follower count from the public profile page.
    X embeds data in meta tags and JSON. Success rate varies.
    """
    url = f"https://x.com/{username}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        if resp.status_code != 200:
            print(f"  [{username}] HTTP {resp.status_code}")
            return None

        html = resp.text

        # Method 1: og:description often contains "12345 followers · ..."
        m = re.search(r'og:description" content="([^"]+)"', html)
        if m:
            desc = m.group(1)
            m2 = re.search(r"([\d,]+)\s*followers", desc, re.I)
            if m2:
                return int(m2.group(1).replace(",", ""))

        # Method 2: "followers_count":12345 in embedded JSON
        match = re.search(r'"followers_count"\s*:\s*(\d+)', html)
        if match:
            return int(match.group(1))

        # Method 3: alternative field
        match = re.search(r'"followersCount"\s*:\s*(\d+)', html)
        if match:
            return int(match.group(1))

        # Method 4: visible text patterns
        match = re.search(
            r'([\d,\.]+[KkMmBb]?)\s*(?:Followers|followers)',
            html,
            re.IGNORECASE,
        )
        if match:
            return parse_count(match.group(1))

        print(f"  [{username}] Could not find followers_count in page")
        return None

    except Exception as e:
        print(f"  [{username}] Error: {e}")
        return None


def fetch_follower_count(username: str) -> int | None:
    """Main fetch function. Can be extended with more providers later."""
    count = fetch_via_page(username)
    if count is not None:
        return count
    return None


def main():
    accounts = load_accounts()
    history = load_history()
    now = datetime.now(timezone.utc)
    timestamp = now.isoformat()

    print(f"Fetching at {timestamp} for {len(accounts)} accounts...")

    snapshot = {
        "timestamp": timestamp,
        "accounts": {},
    }

    for username in accounts:
        print(f"→ @{username}")
        count = fetch_follower_count(username)
        snapshot["accounts"][username] = count
        if count is not None:
            print(f"  ✓ {count:,} followers")
        else:
            print(f"  ✗ failed")
        time.sleep(1.5)

    # Append to history
    history.append(snapshot)

    # Keep last ~90 days of data
    if len(history) > 200:
        history = history[-200:]

    save_json(HISTORY_FILE, history)
    save_json(LATEST_FILE, snapshot)

    print("\nDone. Latest snapshot saved.")
    print(json.dumps(snapshot, indent=2))


if __name__ == "__main__":
    main()
