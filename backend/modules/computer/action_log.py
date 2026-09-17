# backend/modules/computer/action_log.py
"""
action_log.py — Lightweight local JSON-lines action log.

Stores: timestamp, action, target, success, optional error.
Sensitive message/email content is never stored here.
"""
import json
import threading
from datetime import datetime
from pathlib import Path

LOG_PATH = Path(__file__).resolve().parents[3] / "logs" / "computer_actions.jsonl"
_lock = threading.Lock()


def log_action(action: str, target: str, success: bool, error: str = None, extra: dict = None):
    """Append one action record to the log file. Thread-safe."""
    try:
        record = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "action": action,
            "target": str(target) if target is not None else "",
            "success": bool(success),
        }
        if error:
            record["error"] = str(error)
        if extra:
            record["extra"] = extra

        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _lock:
            with open(LOG_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"[ActionLog] Failed to write log: {e}")
