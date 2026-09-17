# backend/modules/computer/keyboard.py
"""
keyboard.py — Keyboard input helpers (type_text, press_key, hotkey).

All calls go through pyautogui. Input text is sanitized by security.py
before reaching this module.
"""
import time

_pyautogui = None


def _get_pyautogui():
    """Lazy-load pyautogui (avoids slow startup when not needed)."""
    global _pyautogui
    if _pyautogui is None:
        import pyautogui
        pyautogui.FAILSAFE = False
        _pyautogui = pyautogui
    return _pyautogui


def type_text(text: str, app: str = "", interval: float = 0.04) -> dict:
    """
    Type text at the current cursor position.
    If `app` is given, focus that application first.

    Args:
        text: Text to type
        app: (optional) application name to focus first
        interval: Seconds between keystrokes (default 0.04)
    """
    try:
        from backend.security import sanitize_text_for_typing
        safe = sanitize_text_for_typing(text)

        pg = _get_pyautogui()

        if app:
            from backend.modules.computer.applications import focus_application
            focus_application(app)
            time.sleep(0.3)

        pg.typewrite(safe, interval=interval)
        return {
            "success": True,
            "action": "type_text",
            "target": f"'{safe[:40]}{'...' if len(safe) > 40 else ''}'",
            "message": f"Typed {len(safe)} characters.",
        }
    except Exception as e:
        return {"success": False, "action": "type_text", "target": text, "error": str(e)}


def press_key(key: str) -> dict:
    """
    Press a single key (e.g. 'enter', 'escape', 'tab', 'ctrl', etc.).

    Args:
        key: Key name understood by pyautogui
    """
    try:
        pg = _get_pyautogui()
        pg.press(key.lower())
        return {
            "success": True,
            "action": "press_key",
            "target": key,
            "message": f"Pressed '{key}'.",
        }
    except Exception as e:
        return {"success": False, "action": "press_key", "target": key, "error": str(e)}


def hotkey(keys: list) -> dict:
    """
    Press a key combination (e.g. ['ctrl', 'c'], ['ctrl', 'shift', 'esc']).

    Args:
        keys: List of key names
    """
    try:
        pg = _get_pyautogui()
        pg.hotkey(*[k.lower() for k in keys])
        combo = "+".join(keys)
        return {
            "success": True,
            "action": "hotkey",
            "target": combo,
            "message": f"Pressed hotkey '{combo}'.",
        }
    except Exception as e:
        return {"success": False, "action": "hotkey", "target": str(keys), "error": str(e)}
