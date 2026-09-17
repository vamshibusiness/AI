import json
import threading
import time
import datetime
import zoneinfo
from pathlib import Path
from typing import Any, Dict
import requests

from backend.modules.core.jarvis_events import publish_event


BACKEND_DIR = Path(__file__).resolve().parents[2]
ACTIVE_STATE_PATH = BACKEND_DIR / "assets" / "active_calendar_reminders.json"




class CalendarReminderAgent:
    RUNNING_STATUSES = {"monitoring"}

    REMINDER_MINUTES = 15
    POLL_SECONDS = 30

    # Allows slight timing drift so we don't miss the window.
    WINDOW_SECONDS = 45

    def __init__(self):
        self._file_lock = threading.RLock()
        self._thread = None
        self.state = self.load_state()

    def default_state(self) -> Dict[str, Any]:
        return {
            "status": "idle",
            "announced_keys": [],
            "last_checked_at": None,
            "error": None,
            "started_at": None,
            "updated_at": None,
        }

    def _now(self) -> str:
        return datetime.datetime.now(datetime.timezone.utc).isoformat()

    def _read_json_file(self, path: Path, fallback: Any) -> Any:
        if not path.exists():
            return fallback

        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                return json.loads(content) if content else fallback
        except Exception as e:
            print(f"[Calendar Reminder Agent] Failed reading {path.name}: {e}")
            return fallback

    def _atomic_write_json(self, path: Path, data: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)

        temp_path = path.with_suffix(path.suffix + ".tmp")

        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

        temp_path.replace(path)

    def _normalize_state(self, state: Any) -> Dict[str, Any]:
        if not isinstance(state, dict):
            return self.default_state()

        normalized = self.default_state()
        normalized.update(state)

        valid_statuses = self.RUNNING_STATUSES | {"idle", "error"}
        if normalized.get("status") not in valid_statuses:
            normalized["status"] = "idle"

        if not isinstance(normalized.get("announced_keys"), list):
            normalized["announced_keys"] = []

        return normalized

    def load_state(self) -> Dict[str, Any]:
        with self._file_lock:
            state = self._read_json_file(ACTIVE_STATE_PATH, self.default_state())
            return self._normalize_state(state)

    def save_state(self) -> None:
        with self._file_lock:
            self.state["updated_at"] = self._now()
            self._atomic_write_json(ACTIVE_STATE_PATH, self.state)

    def start(self) -> str:
        with self._file_lock:
            if self._thread and self._thread.is_alive():
                return "Calendar reminder agent is already running."

            self.state = self.load_state()
            self.state["status"] = "monitoring"
            self.state["started_at"] = self.state.get("started_at") or self._now()
            self.save_state()

            self._thread = threading.Thread(
                target=self._reminder_loop,
                daemon=True,
            )
            self._thread.start()

        return "Calendar reminder agent started."

    def _get_cached_calendar_summary(self) -> dict:
        summary_path = Path("assets/calendar_summary.json")
        if not summary_path.exists():
            summary_path = Path("backend/assets/calendar_summary.json")
        if summary_path.exists():
            return self._read_json_file(summary_path, {"events": []})
        return {"events": []}

    def _parse_event_start(self, start_raw: str):
        if not start_raw or "T" not in start_raw:
            return None

        dt = datetime.datetime.fromisoformat(start_raw.replace("Z", "+00:00"))

        # If Google/local cache ever gives us a naive datetime, treat it as local system time.
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=get_local_tz())

        # Convert to this computer's local timezone.
        return dt.astimezone()

    def _format_time_for_speech(self, dt: datetime.datetime) -> str:
        hour = dt.strftime("%I").lstrip("0")
        minute = dt.strftime("%M")
        am_pm = dt.strftime("%p")

        if minute == "00":
            return f"{hour} {am_pm}"

        return f"{hour}:{minute} {am_pm}"

    def _event_key(self, event: dict) -> str:
        title = event.get("title", "Untitled event")
        start = event.get("start", "")
        return f"{title}:{start}"

    def _prune_announced_keys(self):
        announced_keys = self.state.get("announced_keys", [])

        if len(announced_keys) > 300:
            self.state["announced_keys"] = announced_keys[-200:]

    def _reminder_loop(self) -> None:
        print("[Calendar Reminder Agent] Started. Monitoring cached calendar summary.")

        while True:
            try:
                self._check_cached_events()

            except Exception as e:
                print(f"[Calendar Reminder Agent Error] {e}")

                with self._file_lock:
                    self.state["status"] = "error"
                    self.state["error"] = str(e)
                    self.save_state()

            time.sleep(self.POLL_SECONDS)

    def _check_cached_events(self) -> None:
        now = now_local()
        summary = self._get_cached_calendar_summary()
        events = summary.get("events", [])

        with self._file_lock:
            self.state = self.load_state()
            self.state["status"] = "monitoring"
            self.state["last_checked_at"] = self._now()
            self.state["error"] = None

            announced_keys = set(self.state.get("announced_keys", []))

            for event in events:
                title = event.get("title", "your meeting")
                start_raw = event.get("start")

                start_dt = self._parse_event_start(start_raw)

                # Skip all-day events or malformed starts.
                if not start_dt:
                    continue

                minutes_until = (start_dt - now).total_seconds() / 60

                is_in_reminder_window = (
                    self.REMINDER_MINUTES - (self.WINDOW_SECONDS / 60)
                    <= minutes_until
                    <= self.REMINDER_MINUTES + (self.WINDOW_SECONDS / 60)
                )

                if not is_in_reminder_window:
                    continue

                event_key = self._event_key(event)

                if event_key in announced_keys:
                    continue

                start_speech = self._format_time_for_speech(start_dt)

                self.state["announced_keys"].append(event_key)
                announced_keys.add(event_key)
                self._prune_announced_keys()
                self.save_state()

                publish_event(
                    "calendar_reminder",
                    {
                        "title": title,
                        "start": start_raw,
                        "start_speech": start_speech,
                        "minutes": self.REMINDER_MINUTES,
                    },
                )

                print(f"[Calendar Reminder Agent] Reminder published for: {title}")

            self.save_state()


_calendar_reminder_agent = None
_agent_lock = threading.RLock()


def get_calendar_reminder_agent() -> CalendarReminderAgent:
    global _calendar_reminder_agent

    with _agent_lock:
        if _calendar_reminder_agent is None:
            _calendar_reminder_agent = CalendarReminderAgent()

        return _calendar_reminder_agent


def start_calendar_reminder_agent() -> str:
    agent = get_calendar_reminder_agent()
    return agent.start()


def get_local_tz():
    return datetime.datetime.now().astimezone().tzinfo


def now_local():
    return datetime.datetime.now().astimezone()