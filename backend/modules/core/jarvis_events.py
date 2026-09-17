import queue
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class JarvisEvent:
    event_type: str
    payload: Dict[str, Any]


_event_queue = queue.Queue()


def publish_event(event_type: str, payload: Optional[Dict[str, Any]] = None) -> None:
    _event_queue.put(
        JarvisEvent(
            event_type=event_type,
            payload=payload or {},
        )
    )


def get_next_event_nowait() -> Optional[JarvisEvent]:
    try:
        return _event_queue.get_nowait()
    except queue.Empty:
        return None