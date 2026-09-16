#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
X Follower Tracker using SocialCrawl API
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

# Force UTF-8
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parent.parent
ACCOUNTS_FILE = ROOT / "accounts.json"
HISTORY_FILE = ROOT / "data" / "history.json"
LATEST_FILE = ROOT / "data" / "latest.json"

API_KEY = os.environ.get("SOCIALCRAWL_API_KEY")
API_URL = "https://www.socialcrawl.dev/v1/twitter/profile"


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


def fetch_follower_count(username: str):
    if not API_KEY:
        print(f"  [{username}] ERROR: SOCIALCRAWL_API_KEY not set")
        return None

    try:
        resp = requests.get(
            API_URL,
            params={"handle": username},
            headers={"x-api-key": API_KEY},
            timeout=20,
        )

        if resp.status_code != 200:
            print(f"  [{username}] HTTP {resp.status_code}")
            return None

        data = resp.json()

        if not data.get("success"):
            print(f"  [{username}] API returned success=false")
            return None

        author = data.get("data", {}).get("author", {})
        followers = author.get("followers")
        return followers

    except Exception as e:
        # Safe print without unicode issues
        print(f"  [{username}] Error: {type(e).__name__}")
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
        print(f"-> @{username}")
        count = fetch_follower_count(username)
        snapshot["accounts"][username] = count
        if count is not None:
            print(f"  OK {count} followers")
        else:
            print(f"  FAILED")
        time.sleep(0.7)

    history.append(snapshot)
    if len(history) > 200:
        history = history[-200:]

    save_json(HISTORY_FILE, history)
    save_json(LATEST_FILE, snapshot)

    print("\nDone.")
    print(json.dumps(snapshot, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
