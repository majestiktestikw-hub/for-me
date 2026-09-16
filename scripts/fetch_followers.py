#!/usr/bin/env python3
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parent.parent
ACCOUNTS_FILE = ROOT / "accounts.json"
HISTORY_FILE = ROOT / "data" / "history.json"
LATEST_FILE = ROOT / "data" / "latest.json"

API_KEY = os.environ.get("SOCIALCRAWL_API_KEY", "")
API_URL = "https://www.socialcrawl.dev/v1/twitter/profile"


def load_accounts():
    with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def load_history():
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def fetch_follower_count(username):
    if not API_KEY:
        print("NO_API_KEY")
        return None

    try:
        r = requests.get(
            API_URL,
            params={"handle": username},
            headers={"x-api-key": API_KEY},
            timeout=25
        )
        print("STATUS " + str(r.status_code))
        if r.status_code != 200:
            return None

        data = r.json()
        if not data.get("success"):
            print("API_FAIL")
            return None

        followers = data.get("data", {}).get("author", {}).get("followers")
        return followers
    except Exception as e:
        # Печатаем только безопасную информацию
        print("EXCEPTION_TYPE " + type(e).__name__)
        return None


def main():
    accounts = load_accounts()
    history = load_history()
    timestamp = datetime.now(timezone.utc).isoformat()

    print("START " + timestamp)
    print("KEY_LEN " + str(len(API_KEY)))

    snapshot = {"timestamp": timestamp, "accounts": {}}

    for username in accounts:
        print("USER " + username)
        count = fetch_follower_count(username)
        snapshot["accounts"][username] = count
        if count is not None:
            print("OK " + str(count))
        else:
            print("FAIL")
        time.sleep(0.8)

    history.append(snapshot)
    if len(history) > 200:
        history = history[-200:]

    save_json(HISTORY_FILE, history)
    save_json(LATEST_FILE, snapshot)

    print("DONE")


if __name__ == "__main__":
    main()
