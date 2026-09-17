# backend/modules/computer/mouse.py
"""
mouse.py — Mouse click helpers.
"""

_pyautogui = None


def _get_pyautogui():
    """Lazy-load pyautogui."""
    global _pyautogui
    if _pyautogui is None:
        import pyautogui
        pyautogui.FAILSAFE = True
        _pyautogui = pyautogui
    return _pyautogui


def click(x: int = None, y: int = None) -> dict:
    """Left-click. If x/y omitted, clicks current cursor position."""
    try:
        pg = _get_pyautogui()
        if x is not None and y is not None:
            pg.click(x, y)
            msg = f"Clicked at ({x}, {y})."
        else:
            pg.click()
            msg = "Clicked at current cursor position."
        return {"success": True, "action": "click", "target": f"({x},{y})", "message": msg}
    except Exception as e:
        return {"success": False, "action": "click", "target": f"({x},{y})", "error": str(e)}


def double_click(x: int = None, y: int = None) -> dict:
    """Double-click at the given position."""
    try:
        pg = _get_pyautogui()
        if x is not None and y is not None:
            pg.doubleClick(x, y)
        else:
            pg.doubleClick()
        return {"success": True, "action": "double_click", "target": f"({x},{y})", "message": "Double-clicked."}
    except Exception as e:
        return {"success": False, "action": "double_click", "target": f"({x},{y})", "error": str(e)}


def right_click(x: int = None, y: int = None) -> dict:
    """Right-click at the given position."""
    try:
        pg = _get_pyautogui()
        if x is not None and y is not None:
            pg.rightClick(x, y)
        else:
            pg.rightClick()
        return {"success": True, "action": "right_click", "target": f"({x},{y})", "message": "Right-clicked."}
    except Exception as e:
        return {"success": False, "action": "right_click", "target": f"({x},{y})", "error": str(e)}
