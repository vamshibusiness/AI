# backend/modules/computer/verifier.py
"""
verifier.py — Post-action verification helpers.

Each verifier returns (True, detail_str) or (False, reason_str).
"""
import time
from pathlib import Path


def verify_process_running(exe_name: str, timeout: float = 4.0) -> tuple[bool, str]:
    """
    Poll psutil for up to `timeout` seconds to confirm the process is running.
    Returns (True, pid_str) or (False, reason).
    """
    try:
        import psutil
    except ImportError:
        return (True, "psutil unavailable — skipping process verification")

    exe_clean = exe_name.lower().replace(".exe", "")
    start_time = time.time()
    while time.time() - start_time < timeout:
        for proc in psutil.process_iter(['name', 'pid']):
            try:
                name = (proc.info['name'] or '').lower()
                if exe_clean in name:
                    return (True, f"pid={proc.info['pid']}")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        time.sleep(0.3)
    return (False, f"Process '{exe_name}' not found after {timeout}s")


def verify_process_gone(exe_name: str, timeout: float = 4.0) -> tuple[bool, str]:
    """Confirm the process is no longer running."""
    try:
        import psutil
    except ImportError:
        return (True, "psutil unavailable — skipping")

    exe_clean = exe_name.lower().replace(".exe", "")
    start_time = time.time()
    while time.time() - start_time < timeout:
        found = False
        for proc in psutil.process_iter(['name']):
            try:
                name = (proc.info['name'] or '').lower()
                if exe_clean in name:
                    found = True
                    break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        if not found:
            return (True, "process terminated")
        time.sleep(0.3)
    return (False, f"Process '{exe_name}' still running after {timeout}s")


def verify_file_exists(path: str, timeout: float = 2.0) -> tuple[bool, str]:
    """Poll until the file appears or timeout."""
    p = Path(path)
    start_time = time.time()
    while time.time() - start_time < timeout:
        if p.exists() and p.is_file():
            return (True, f"{p.stat().st_size} bytes")
        time.sleep(0.2)
    return (False, f"File '{path}' not found after {timeout}s")


def verify_dir_exists(path: str) -> tuple[bool, str]:
    """Check if directory exists."""
    p = Path(path)
    if p.exists() and p.is_dir():
        return (True, "directory exists")
    return (False, f"Directory '{path}' was not created")
