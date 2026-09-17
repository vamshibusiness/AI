# backend/modules/computer/files.py
"""
files.py — Safe filesystem operations.

All paths are validated by safety.py before any action is taken.
Destructive operations (delete) require explicit confirmation via the
/computer/confirm-delete endpoint and never happen automatically.
"""
import os
import shutil
import subprocess
from pathlib import Path

from backend.modules.computer.safety import (
    validate_path_for_read,
    validate_path_for_write,
    validate_path_for_delete,
)
from backend.modules.computer.verifier import verify_file_exists, verify_dir_exists
from backend.modules.computer.action_log import log_action

_HOME = Path.home()

LOCATION_MAP = {
    "desktop": _HOME / "Desktop",
    "documents": _HOME / "Documents",
    "downloads": _HOME / "Downloads",
    "pictures": _HOME / "Pictures",
    "videos": _HOME / "Videos",
    "music": _HOME / "Music",
    "home": _HOME,
}


def _resolve_location(location: str) -> Path:
    loc_key = (location or "desktop").lower().strip()
    if loc_key in LOCATION_MAP:
        return LOCATION_MAP[loc_key]
    candidate = Path(location).resolve()
    return candidate


def _human_size(size_bytes: int) -> str:
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def create_folder(name: str, location: str = "desktop") -> dict:
    base = _resolve_location(location)
    target = base / name
    is_safe, reason = validate_path_for_write(target)
    if not is_safe:
        return {"success": False, "action": "create_folder", "target": str(target), "error": reason}

    try:
        target.mkdir(parents=True, exist_ok=True)
        ok, _ = verify_dir_exists(str(target))
        log_action("create_folder", str(target), ok)
        return {
            "success": ok,
            "action": "create_folder",
            "target": str(target),
            "message": f"Folder '{name}' created at {target.parent}.",
        }
    except Exception as e:
        log_action("create_folder", str(target), False, str(e))
        return {"success": False, "action": "create_folder", "target": str(target), "error": str(e)}


def create_file(name: str, location: str = "desktop", content: str = "") -> dict:
    base = _resolve_location(location)
    target = base / name
    is_safe, reason = validate_path_for_write(target)
    if not is_safe:
        return {"success": False, "action": "create_file", "target": str(target), "error": reason}

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            f.write(content)
        ok, _ = verify_file_exists(str(target))
        log_action("create_file", str(target), ok)
        return {
            "success": ok,
            "action": "create_file",
            "target": str(target),
            "message": f"File '{name}' created at {target.parent}.",
        }
    except Exception as e:
        log_action("create_file", str(target), False, str(e))
        return {"success": False, "action": "create_file", "target": str(target), "error": str(e)}


def open_folder(location: str = "desktop") -> dict:
    """Open a folder in File Explorer."""
    target = _resolve_location(location)
    if not target.exists() or not target.is_dir():
        return {
            "success": False,
            "action": "open_folder",
            "target": str(target),
            "error": f"Folder '{target}' does not exist.",
        }

    is_safe, reason = validate_path_for_read(target)
    if not is_safe:
        return {"success": False, "action": "open_folder", "target": str(target), "error": reason}

    try:
        subprocess.Popen(f'explorer "{target}"', shell=True)
        log_action("open_folder", str(target), True)
        return {
            "success": True,
            "action": "open_folder",
            "target": str(target),
            "message": f"Opened {target} in File Explorer.",
        }
    except Exception as e:
        log_action("open_folder", str(target), False, str(e))
        return {"success": False, "action": "open_folder", "target": str(target), "error": str(e)}


def list_files(location: str = "desktop") -> dict:
    """List files/folders in a safe directory."""
    target = _resolve_location(location)
    if not target.exists() or not target.is_dir():
        return {
            "success": False,
            "action": "list_files",
            "target": str(target),
            "error": f"'{target}' does not exist.",
        }

    is_safe, reason = validate_path_for_read(target)
    if not is_safe:
        return {"success": False, "action": "list_files", "target": str(target), "error": reason}

    try:
        entries = []
        for item in target.iterdir():
            try:
                entries.append({
                    "name": item.name,
                    "type": "folder" if item.is_dir() else "file",
                    "size": _human_size(item.stat().st_size) if item.is_file() else None,
                })
            except Exception:
                pass

        entries.sort(key=lambda x: (x["type"] != "folder", x["name"].lower()))
        log_action("list_files", str(target), True)
        return {
            "success": True,
            "action": "list_files",
            "target": str(target),
            "entries": entries[:50],
            "message": f"Found {len(entries)} items in {target}.",
        }
    except Exception as e:
        log_action("list_files", str(target), False, str(e))
        return {"success": False, "action": "list_files", "target": str(target), "error": str(e)}


def rename_file(old_path: str, new_name: str) -> dict:
    """Rename a file or folder within the same directory."""
    target = Path(old_path).resolve()
    if not target.exists():
        return {
            "success": False,
            "action": "rename_file",
            "target": str(target),
            "error": f"'{target}' does not exist.",
        }

    dest = target.parent / new_name
    is_safe, reason = validate_path_for_write(dest)
    if not is_safe:
        return {"success": False, "action": "rename_file", "target": str(target), "error": reason}

    try:
        target.rename(dest)
        log_action("rename_file", str(target), True, extra={"new_name": new_name})
        return {
            "success": True,
            "action": "rename_file",
            "target": str(target),
            "message": f"Renamed to '{new_name}'.",
        }
    except Exception as e:
        log_action("rename_file", str(target), False, str(e))
        return {"success": False, "action": "rename_file", "target": str(target), "error": str(e)}


def move_file(source: str, destination: str) -> dict:
    """Move a file or folder to a new safe location."""
    src = Path(source).resolve()
    dest = Path(destination).resolve()

    if not src.exists():
        return {
            "success": False,
            "action": "move_file",
            "target": str(src),
            "error": f"'{src}' does not exist.",
        }

    is_safe, reason = validate_path_for_write(dest)
    if not is_safe:
        return {"success": False, "action": "move_file", "target": str(dest), "error": reason}

    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dest))
        log_action("move_file", str(src), True)
        return {
            "success": True,
            "action": "move_file",
            "target": str(src),
            "message": f"Moved '{src.name}' to {dest}.",
        }
    except Exception as e:
        log_action("move_file", str(src), False, str(e))
        return {"success": False, "action": "move_file", "target": str(src), "error": str(e)}


def prepare_delete(path: str) -> dict:
    """
    Validate the path and return metadata for the confirmation UI.
    Does NOT delete anything.
    """
    target = Path(path).resolve()
    if not target.exists():
        return {
            "success": False,
            "action": "prepare_delete",
            "target": str(target),
            "error": f"'{target}' does not exist.",
        }

    is_safe, reason = validate_path_for_delete(target)
    if not is_safe:
        return {"success": False, "action": "prepare_delete", "target": str(target), "error": reason}

    is_dir = target.is_dir()
    size_str = f"{len(list(target.glob('*')))} items" if is_dir else _human_size(target.stat().st_size)

    return {
        "success": True,
        "action": "prepare_delete",
        "target": str(target),
        "name": target.name,
        "size": size_str,
        "is_dir": is_dir,
        "requires_confirmation": True,
    }


def execute_delete(path: str) -> dict:
    """
    Actually delete a file/folder after explicit user confirmation.
    Called only by /computer/confirm-delete endpoint.
    """
    target = Path(path).resolve()
    if not target.exists():
        return {
            "success": False,
            "action": "delete",
            "target": str(target),
            "error": f"'{target}' does not exist.",
        }

    is_safe, reason = validate_path_for_delete(target)
    if not is_safe:
        return {"success": False, "action": "delete", "target": str(target), "error": reason}

    try:
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()

        if not target.exists():
            log_action("delete", str(target), True)
            return {
                "success": True,
                "action": "delete",
                "target": str(target),
                "message": f"'{target.name}' deleted successfully.",
            }
        else:
            log_action("delete", str(target), False, "Still exists after delete attempt")
            return {
                "success": False,
                "action": "delete",
                "target": str(target),
                "error": "Deletion failed — item still exists.",
            }
    except Exception as e:
        log_action("delete", str(target), False, str(e))
        return {"success": False, "action": "delete", "target": str(target), "error": str(e)}
