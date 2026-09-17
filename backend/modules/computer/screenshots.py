# backend/modules/computer/screenshots.py
"""
screenshots.py — Take screenshots and save to a secure temp location.
"""
import tempfile
import time
from pathlib import Path


def take_screenshot() -> dict:
    """
    Take a screenshot and save to a temp file.
    Returns: { success, action, target, message, path }
    """
    try:
        import pyautogui  # lazy import
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        tmp_dir = Path(tempfile.gettempdir()) / "jarvis_screenshots"
        tmp_dir.mkdir(exist_ok=True)
        out_path = str(tmp_dir / f"screenshot_{timestamp}.png")
        img = pyautogui.screenshot()
        img.save(out_path)
        return {
            "success": True,
            "action": "take_screenshot",
            "target": out_path,
            "message": f"Screenshot saved to {out_path}",
            "path": out_path,
        }
    except Exception as e:
        return {
            "success": False,
            "action": "take_screenshot",
            "target": None,
            "error": str(e),
        }
