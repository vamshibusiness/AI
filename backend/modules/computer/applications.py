# backend/modules/computer/applications.py
"""
applications.py — Safe application launch and close.

Uses allow-list (safety.APP_REGISTRY), shutil.which, known Windows paths,
and the Windows `start` command as fallback. Never runs arbitrary paths.
"""
import os
import shutil
import subprocess
import time
from pathlib import Path

from backend.modules.computer.safety import APP_REGISTRY, resolve_app
from backend.modules.computer.verifier import verify_process_running, verify_process_gone
from backend.modules.computer.action_log import log_action

_PROGRAM_DIRS = [
    Path("C:/Program Files"),
    Path("C:/Program Files (x86)"),
    Path.home() / "AppData" / "Local" / "Programs",
]


def _find_exe(exe_name: str) -> str | None:
    """Look up exe in PATH, then common Windows program dirs."""
    found = shutil.which(exe_name)
    if found:
        return found
    for pdir in _PROGRAM_DIRS:
        if pdir.exists():
            candidates = list(pdir.rglob(exe_name))
            if candidates:
                return str(candidates[0])
    return None


def open_application(app_name: str) -> dict:
    """Launch a known, allow-listed application and verify it started."""
    app_info = resolve_app(app_name)
    if not app_info:
        log_action("open_application", app_name, False, "Not in allowed app list")
        return {
            "success": False,
            "action": "open_application",
            "target": app_name,
            "error": f"'{app_name}' is not in the allowed application list.",
        }

    # Special protocol handlers (e.g. ms-settings:)
    if isinstance(app_info, dict) and app_info.get("protocol"):
        try:
            os.system(f"start {app_info['protocol']}")
            time.sleep(1.0)
            log_action("open_application", app_name, True)
            return {
                "success": True,
                "action": "open_application",
                "target": app_name,
                "message": "Windows Settings opened.",
            }
        except Exception as e:
            return {"success": False, "action": "open_application", "target": app_name, "error": str(e)}

    exe = app_info if isinstance(app_info, str) else app_info.get("exe", "")
    resolved_path = _find_exe(exe) if exe else None

    try:
        if resolved_path:
            subprocess.Popen([resolved_path], shell=False)
        elif exe:
            # Fallback to start command for registered Windows executables
            subprocess.Popen(f'start "" "{exe}"', shell=True)
        else:
            return {
                "success": False,
                "action": "open_application",
                "target": app_name,
                "error": f"Could not locate any executable for '{app_name}'.",
            }

        ok, detail = verify_process_running(exe, timeout=5.0) if exe else (True, "launched")
        if ok:
            log_action("open_application", app_name, True, extra={"exe": exe, "detail": detail})
            return {
                "success": True,
                "action": "open_application",
                "target": app_name,
                "message": f"{app_name.capitalize()} opened successfully.",
            }
        else:
            return {
                "success": True,
                "action": "open_application",
                "target": app_name,
                "message": f"Launched '{app_name}' but could not confirm it is running. {detail}",
            }
    except Exception as e:
        log_action("open_application", app_name, False, str(e))
        return {"success": False, "action": "open_application", "target": app_name, "error": str(e)}


def close_application(app_name: str) -> dict:
    """Terminate a running application by name using psutil."""
    try:
        import psutil
    except ImportError:
        return {
            "success": False,
            "action": "close_application",
            "target": app_name,
            "error": "psutil not available.",
        }

    app_info = resolve_app(app_name)
    if not app_info:
        return {
            "success": False,
            "action": "close_application",
            "target": app_name,
            "error": f"'{app_name}' is not in the allowed application list.",
        }

    exe = (app_info if isinstance(app_info, str) else app_info.get("exe") or "").lower().replace(".exe", "")
    closed_pids = []

    for proc in psutil.process_iter(['name', 'pid']):
        try:
            name = (proc.info['name'] or '').lower()
            if exe and exe in name:
                proc.terminate()
                closed_pids.append(proc.info['pid'])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    if not closed_pids:
        return {
            "success": False,
            "action": "close_application",
            "target": app_name,
            "error": f"No running process found for '{app_name}'.",
        }

    time.sleep(1.0)
    ok, _ = verify_process_gone(exe, timeout=4.0)
    log_action("close_application", app_name, ok, extra={"pids": closed_pids})

    if ok:
        return {
            "success": True,
            "action": "close_application",
            "target": app_name,
            "message": f"{app_name.capitalize()} closed successfully.",
        }
    else:
        return {
            "success": True,
            "action": "close_application",
            "target": app_name,
            "message": f"Sent close signal to {app_name} (pids: {closed_pids}).",
        }


def focus_application(app_name: str) -> bool:
    """
    Attempt to bring an application window to the foreground.
    Returns True if focus was likely achieved.
    Uses pygetwindow (installed with pyautogui).
    """
    try:
        import pygetwindow as gw
        windows = gw.getWindowsWithTitle(app_name)
        if windows:
            win = windows[0]
            if win.isMinimized:
                win.restore()
            win.activate()
            time.sleep(0.5)
            return True
    except Exception as e:
        print(f"[focus_application] Warning: {e}")
    return False
