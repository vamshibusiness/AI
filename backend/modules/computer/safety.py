# backend/modules/computer/safety.py
"""
safety.py — Path validation and application allow-list enforcement.

Adapts central security rules from backend/security.py for the computer module.
Returns (is_safe, reason) tuples for safe, un-raised error handling.
"""
from pathlib import Path
from backend.security import (
    SAFE_WRITE_ROOTS,
    SAFE_READ_ROOTS,
    BLOCKED_PATHS,
    APP_REGISTRY,
    normalize_app_name,
    resolve_app,
    is_allowed_app,
    is_safe_path,
    validate_path_for_read as _val_read,
    validate_path_for_write as _val_write,
    validate_path_for_delete as _val_delete,
    sanitize_text_for_typing as safe_text_for_typing,
)


def validate_path_for_read(path: str | Path) -> tuple[bool, str]:
    try:
        _val_read(str(path))
        return True, ""
    except Exception as e:
        return False, str(e)


def validate_path_for_write(path: str | Path) -> tuple[bool, str]:
    try:
        _val_write(str(path))
        return True, ""
    except Exception as e:
        return False, str(e)


def validate_path_for_delete(path: str | Path) -> tuple[bool, str]:
    try:
        _val_delete(str(path))
        return True, ""
    except Exception as e:
        return False, str(e)


__all__ = [
    "SAFE_WRITE_ROOTS",
    "SAFE_READ_ROOTS",
    "BLOCKED_PATHS",
    "APP_REGISTRY",
    "normalize_app_name",
    "resolve_app",
    "is_allowed_app",
    "is_safe_path",
    "validate_path_for_read",
    "validate_path_for_write",
    "validate_path_for_delete",
    "safe_text_for_typing",
]
