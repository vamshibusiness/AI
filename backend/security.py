# backend/security.py
"""
Central Security Module for JARVIS.

Enforces:
- Allowed and blocked filesystem roots
- Application allow-list enforcement
- Secret redaction before storage or logging
- Confirmation tokens for destructive or sensitive actions
- Typing and tool argument sanitization
"""

import os
import re
import uuid
import time
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

_HOME = Path.home()

# =====================================================================
# FILESYSTEM ACCESS ROOTS
# =====================================================================
SAFE_WRITE_ROOTS = [
    _HOME / "Desktop",
    _HOME / "Documents",
    _HOME / "Downloads",
    _HOME / "Pictures",
    _HOME / "Videos",
    _HOME / "Music",
]

SAFE_READ_ROOTS = [
    _HOME,
    _HOME / "Desktop",
    _HOME / "Documents",
    _HOME / "Downloads",
    _HOME / "Pictures",
    _HOME / "Videos",
    _HOME / "Music",
    Path("C:/Jarvis/docs"),
    Path("C:/Jarvis/backend/assets"),
]

BLOCKED_PATHS = [
    Path("C:/Windows"),
    Path("C:/Windows/System32"),
    Path("C:/Windows/SysWOW64"),
    Path("C:/Program Files"),
    Path("C:/Program Files (x86)"),
    Path("C:/ProgramData"),
    Path("C:/Boot"),
    _HOME / "AppData",
]

PROTECTED_FILENAMES = {
    ".env",
    "google_credentials.json",
    "token.json",
    "id_rsa",
    "id_ed25519",
    "credentials.json",
    "client_secret.json",
    "token.pickle",
}

# =====================================================================
# ALLOWED APPLICATION REGISTRY
# =====================================================================
APP_REGISTRY: Dict[str, str] = {
    "chrome": "chrome.exe",
    "google chrome": "chrome.exe",
    "firefox": "firefox.exe",
    "edge": "msedge.exe",
    "microsoft edge": "msedge.exe",
    "notepad": "notepad.exe",
    "notepad++": "notepad++.exe",
    "calculator": "calc.exe",
    "calc": "calc.exe",
    "explorer": "explorer.exe",
    "file explorer": "explorer.exe",
    "vscode": "Code.exe",
    "vs code": "Code.exe",
    "visual studio code": "Code.exe",
    "word": "WINWORD.EXE",
    "excel": "EXCEL.EXE",
    "powerpoint": "POWERPNT.EXE",
    "paint": "mspaint.exe",
    "vlc": "vlc.exe",
    "spotify": "Spotify.exe",
    "discord": "Discord.exe",
    "slack": "slack.exe",
    "zoom": "Zoom.exe",
    "teams": "Teams.exe",
    "task manager": "Taskmgr.exe",
    "snipping tool": "SnippingTool.exe",
    "settings": "ms-settings:",
}

# =====================================================================
# SECRET REDACTION PATTERNS
# =====================================================================
_SECRET_PATTERNS = [
    # API Keys / Tokens (OpenAI, HuggingFace, Slack, GitHub, generic)
    (re.compile(r"(sk-[a-zA-Z0-9]{20,})", re.IGNORECASE), "[REDACTED_API_KEY]"),
    (re.compile(r"(ghp_[a-zA-Z0-9]{36,})", re.IGNORECASE), "[REDACTED_GITHUB_TOKEN]"),
    (re.compile(r"(xox[baprs]-[a-zA-Z0-9]{10,})", re.IGNORECASE), "[REDACTED_SLACK_TOKEN]"),
    (re.compile(r"(AIza[0-9A-Za-z\\-_]{35})", re.IGNORECASE), "[REDACTED_GOOGLE_API_KEY]"),
    (re.compile(r"(ya29\.[0-9A-Za-z\\-_]+)", re.IGNORECASE), "[REDACTED_OAUTH_TOKEN]"),
    (re.compile(r"(Bearer\s+[a-zA-Z0-9\-_\.]{20,})", re.IGNORECASE), "Bearer [REDACTED_TOKEN]"),
    # Passwords in URL or assignment strings
    (re.compile(r"(password\s*[:=]\s*['\"][^'\"]+['\"])", re.IGNORECASE), "password='[REDACTED_PASSWORD]'"),
    (re.compile(r"(client_secret\s*[:=]\s*['\"][^'\"]+['\"])", re.IGNORECASE), "client_secret='[REDACTED_SECRET]'"),
    # Private Key blocks
    (re.compile(r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----[^-]+-----END (?:RSA |EC )?PRIVATE KEY-----", re.DOTALL), "[REDACTED_PRIVATE_KEY]"),
]

def redact_secrets(text: str) -> str:
    """Replaces sensitive tokens, passwords, and private keys with redaction placeholders."""
    if not text:
        return text
    redacted = text
    for pattern, replacement in _SECRET_PATTERNS:
        redacted = pattern.sub(replacement, redacted)
    return redacted

# =====================================================================
# PATH VALIDATION
# =====================================================================
def _resolve(raw_path: str) -> Path:
    p = Path(raw_path).expanduser()
    try:
        return p.resolve()
    except Exception:
        return p

def _is_blocked(p: Path) -> bool:
    if p.name.lower() in PROTECTED_FILENAMES:
        return True
    # Also block files ending with sensitive extensions
    if p.suffix.lower() in {".pem", ".key", ".pfx", ".p12"}:
        return True
    for blocked in BLOCKED_PATHS:
        try:
            if p == blocked or blocked in p.parents:
                return True
        except Exception:
            pass
    return False

def is_safe_path(path: str, mode: str = "read") -> bool:
    """Determines whether a given path is safe for reading or writing."""
    try:
        resolved = _resolve(path)
        if _is_blocked(resolved):
            return False
        roots = SAFE_WRITE_ROOTS if mode == "write" else SAFE_READ_ROOTS
        for root in roots:
            try:
                resolved_root = root.resolve()
                if resolved == resolved_root or resolved_root in resolved.parents:
                    return True
            except Exception:
                continue
        return False
    except Exception:
        return False

def validate_path_for_read(path: str) -> Path:
    if not is_safe_path(path, mode="read"):
        raise PermissionError(f"Access denied: Path '{path}' is not within safe read roots or is protected.")
    resolved = _resolve(path)
    if not resolved.exists():
        raise FileNotFoundError(f"File not found: '{path}'")
    return resolved

def validate_path_for_write(path: str) -> Path:
    if not is_safe_path(path, mode="write"):
        raise PermissionError(f"Access denied: Path '{path}' is outside safe write directories or is protected.")
    return _resolve(path)

def validate_path_for_delete(path: str) -> Path:
    resolved = _resolve(path)
    if _is_blocked(resolved):
        raise PermissionError(f"Access denied: Deletion of '{path}' is strictly blocked.")
    if not is_safe_path(path, mode="write"):
        raise PermissionError(f"Access denied: '{path}' is not within safe writable roots.")
    return resolved

# =====================================================================
# APPLICATION ALLOW-LIST
# =====================================================================
def normalize_app_name(name: str) -> str:
    return name.lower().strip()

def resolve_app(name: str) -> Optional[str]:
    return APP_REGISTRY.get(normalize_app_name(name))

def is_allowed_app(name: str) -> bool:
    return normalize_app_name(name) in APP_REGISTRY

# =====================================================================
# SAFE TYPING SANITIZATION
# =====================================================================
_DANGEROUS_INJECTIONS = [
    re.compile(r"powershell(\.exe)?", re.IGNORECASE),
    re.compile(r"cmd(\.exe)?", re.IGNORECASE),
    re.compile(r"rmdir\s+/s", re.IGNORECASE),
    re.compile(r"del\s+/[sfq]", re.IGNORECASE),
    re.compile(r"format\s+[a-z]:", re.IGNORECASE),
    re.compile(r"reg\s+(add|delete)", re.IGNORECASE),
    re.compile(r"Invoke-Expression", re.IGNORECASE),
    re.compile(r"iex\s+", re.IGNORECASE),
]

def sanitize_text_for_typing(text: str) -> str:
    for pattern in _DANGEROUS_INJECTIONS:
        if pattern.search(text):
            raise ValueError(f"Security Alert: Blocked dangerous system command injection in typing payload.")
    return text

# =====================================================================
# CONFIRMATION TOKEN SYSTEM FOR SENSITIVE ACTIONS
# =====================================================================
_CONFIRMATION_TOKENS: Dict[str, Dict[str, Any]] = {}
TOKEN_EXPIRY_SECONDS = 300  # 5 minutes

def create_confirmation_token(action_type: str, details: Dict[str, Any]) -> str:
    """Generates a secure single-use confirmation token for destructive actions."""
    token = str(uuid.uuid4())
    _CONFIRMATION_TOKENS[token] = {
        "action_type": action_type,
        "details": details,
        "created_at": time.time(),
    }
    return token

def get_pending_confirmation(token: str) -> Optional[Dict[str, Any]]:
    record = _CONFIRMATION_TOKENS.get(token)
    if not record:
        return None
    if time.time() - record["created_at"] > TOKEN_EXPIRY_SECONDS:
        _CONFIRMATION_TOKENS.pop(token, None)
        return None
    return record

def consume_confirmation_token(token: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Validates and invalidates a confirmation token."""
    record = get_pending_confirmation(token)
    if not record:
        return False, None
    _CONFIRMATION_TOKENS.pop(token, None)
    return True, record
