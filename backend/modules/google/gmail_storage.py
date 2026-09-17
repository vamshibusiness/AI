import json
import os
from pathlib import Path

# Save to a dedicated data directory
DATA_FILE = Path(__file__).resolve().parents[2] / "assets" / "inbox.json"

def get_inbox():
    if not os.path.exists(DATA_FILE): return []
    with open(DATA_FILE, 'r') as f: return json.load(f)

def save_inbox(data):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, 'w') as f: json.dump(data, f, indent=4)

def consume_inbox() -> list[dict]:
    """
    Return locally stored email summaries and clear the local queue.

    This does not delete emails from Gmail. It only clears inbox.json
    after Jarvis reads the saved summaries aloud.
    """
    inbox = get_inbox()

    if inbox:
        save_inbox([])

    return inbox    

def peek_inbox():
    """
    Reads saved inbox emails without deleting or clearing them.
    Used by morning briefing.
    """
    if not DATA_FILE.exists():
        return []

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = f.read().strip()

            if not data:
                return []

            return json.loads(data)

    except Exception as e:
        print(f"[Gmail Storage] Failed to peek inbox: {e}")
        return []