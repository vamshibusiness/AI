import json
import time
from datetime import datetime
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]
GPU_PRIORITY_PATH = BACKEND_DIR / "assets" / "gpu_priority.json"


def _now() -> float:
    return time.time()


def _read_state() -> dict:
    if not GPU_PRIORITY_PATH.exists():
        return {}

    try:
        content = GPU_PRIORITY_PATH.read_text(encoding="utf-8").strip()
        return json.loads(content) if content else {}
    except Exception:
        return {}


def _write_state(data: dict) -> None:
    GPU_PRIORITY_PATH.parent.mkdir(parents=True, exist_ok=True)

    temp_path = GPU_PRIORITY_PATH.with_suffix(".json.tmp")
    temp_path.write_text(json.dumps(data, indent=4), encoding="utf-8")
    temp_path.replace(GPU_PRIORITY_PATH)


def mark_interactive_gpu_active(reason: str = "interactive", ttl_seconds: int = 180) -> None:
    """
    Cross-process signal:
    Voice/STT/TTS/normal Jarvis interaction needs priority access to GPU.
    """
    expires_at = _now() + ttl_seconds

    _write_state(
        {
            "interactive_active": True,
            "reason": reason,
            "expires_at": expires_at,
            "updated_at": datetime.now().isoformat(),
        }
    )


def clear_interactive_gpu_active() -> None:
    """
    Clears the interactive GPU priority signal.
    """
    _write_state(
        {
            "interactive_active": False,
            "reason": None,
            "expires_at": 0,
            "updated_at": datetime.now().isoformat(),
        }
    )


def is_interactive_gpu_active() -> bool:
    state = _read_state()

    if not state.get("interactive_active"):
        return False

    expires_at = float(state.get("expires_at") or 0)

    if expires_at <= _now():
        return False

    return True


def wait_until_background_gpu_allowed(check_interval_seconds: float = 1.0) -> None:
    """
    Used by background agents before GPU-heavy work.
    Research waits here while Jarvis voice interaction is active.
    """
    last_log = 0.0

    while is_interactive_gpu_active():
        current = _now()

        if current - last_log > 10:
            print("[GPU Priority] Voice interaction is active. Research is yielding GPU.")
            last_log = current

        time.sleep(check_interval_seconds)