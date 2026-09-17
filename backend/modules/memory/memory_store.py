# backend/modules/memory/memory_store.py
"""
Persistent SQLite & Semantic Memory Store for JARVIS.

Handles:
- Short-term conversation history per session
- Long-term curated facts & preferences in SQLite
- Semantic memory vector search via sentence-transformers (all-MiniLM-L6-v2)
- Automatic secret redaction before writing to disk
- Seamless synchronization with legacy user_profile.json
"""

import sqlite3
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
import numpy as np

from backend.security import redact_secrets
from backend.config.jarvis_config import MAX_MEMORY_ITEMS

PROJECT_ROOT = Path(__file__).resolve().parents[3]
MEMORY_DIR = PROJECT_ROOT / "backend" / "assets" / "memory"
DB_PATH = MEMORY_DIR / "jarvis_memory.db"
LEGACY_PROFILE_FILE = PROJECT_ROOT / "backend" / "assets" / "user_profile.json"

_embedder = None

def _get_embedder():
    global _embedder
    if _embedder is None:
        from backend.modules.rag.rag_store import get_embedding_model
        _embedder = get_embedding_model()
    return _embedder

def _get_connection() -> sqlite3.Connection:
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

_initialized = False
_migrating = False

def init_memory_db():
    global _initialized
    if _initialized:
        return
    _initialized = True

    conn = _get_connection()
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS long_term_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT DEFAULT 'fact',
                content TEXT NOT NULL UNIQUE,
                embedding BLOB,
                created_at REAL,
                updated_at REAL,
                is_active INTEGER DEFAULT 1
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at REAL
            )
        """)
    conn.close()
    _migrate_legacy_profile()

def _migrate_legacy_profile():
    """Migrates existing user_profile.json facts into SQLite if not already present."""
    global _migrating
    if _migrating or not LEGACY_PROFILE_FILE.exists():
        return
    _migrating = True
    try:
        with open(LEGACY_PROFILE_FILE, "r", encoding="utf-8") as f:
            facts = json.load(f)
        if isinstance(facts, list):
            for fact in facts:
                if isinstance(fact, str) and fact.strip():
                    remember(fact.strip(), category="legacy")
    except Exception as e:
        print(f"[Memory] Legacy profile migration note: {e}")
    finally:
        _migrating = False

def _sync_to_legacy_file():
    """Keeps user_profile.json up to date for any legacy modules."""
    if _migrating:
        return
    try:
        memories = get_all_active_memories()
        facts = [m["content"] for m in memories[:MAX_MEMORY_ITEMS]]
        LEGACY_PROFILE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LEGACY_PROFILE_FILE, "w", encoding="utf-8") as f:
            json.dump(facts, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"[Memory] Could not sync legacy profile: {e}")

def remember(content: str, category: str = "fact") -> Dict[str, Any]:
    """Stores a fact or preference, redacting any sensitive data first."""
    cleaned = redact_secrets(content).strip()
    if not cleaned:
        return {"ok": False, "error": "Empty memory content"}

    now = time.time()
    init_memory_db()

    # Compute embedding
    embedder = _get_embedder()
    emb = embedder.encode([cleaned], convert_to_numpy=True, normalize_embeddings=True)[0]
    emb_blob = emb.astype(np.float32).tobytes()

    conn = _get_connection()
    with conn:
        conn.execute("""
            INSERT INTO long_term_memory (category, content, embedding, created_at, updated_at, is_active)
            VALUES (?, ?, ?, ?, ?, 1)
            ON CONFLICT(content) DO UPDATE SET
                updated_at = excluded.updated_at,
                is_active = 1
        """, (category, cleaned, emb_blob, now, now))
    conn.close()

    _sync_to_legacy_file()
    return {"ok": True, "content": cleaned, "category": category}

def get_all_active_memories() -> List[Dict[str, Any]]:
    init_memory_db()
    conn = _get_connection()
    rows = conn.execute("""
        SELECT id, category, content, created_at, updated_at
        FROM long_term_memory
        WHERE is_active = 1
        ORDER BY updated_at DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def recall(query: str, top_k: int = 5, min_score: float = 0.25) -> List[Dict[str, Any]]:
    """Semantically searches active long-term memories."""
    init_memory_db()
    conn = _get_connection()
    rows = conn.execute("""
        SELECT id, category, content, embedding, updated_at
        FROM long_term_memory
        WHERE is_active = 1
    """).fetchall()
    conn.close()

    if not rows:
        return []

    embedder = _get_embedder()
    query_emb = embedder.encode([query], convert_to_numpy=True, normalize_embeddings=True)[0]

    scored = []
    for r in rows:
        emb_bytes = r["embedding"]
        if not emb_bytes:
            continue
        mem_emb = np.frombuffer(emb_bytes, dtype=np.float32)
        score = float(np.dot(query_emb, mem_emb))
        if score >= min_score:
            scored.append({
                "id": r["id"],
                "category": r["category"],
                "content": r["content"],
                "score": score,
                "updated_at": r["updated_at"],
            })

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]

def forget(content_or_query: str) -> Dict[str, Any]:
    """Deactivates a memory matching content or semantic query."""
    init_memory_db()
    matches = recall(content_or_query, top_k=1, min_score=0.6)
    conn = _get_connection()
    if matches:
        mem_id = matches[0]["id"]
        matched_content = matches[0]["content"]
        with conn:
            conn.execute("UPDATE long_term_memory SET is_active = 0 WHERE id = ?", (mem_id,))
        conn.close()
        _sync_to_legacy_file()
        return {"ok": True, "forgot": matched_content}

    # Direct substring match fallback
    with conn:
        cursor = conn.execute("""
            UPDATE long_term_memory
            SET is_active = 0
            WHERE is_active = 1 AND content LIKE ?
        """, (f"%{content_or_query}%",))
        count = cursor.rowcount
    conn.close()
    _sync_to_legacy_file()
    return {"ok": count > 0, "count": count}

# =====================================================================
# CONVERSATION HISTORY (SESSION PERSISTENCE)
# =====================================================================
def add_conversation_turn(session_id: str, role: str, content: str):
    init_memory_db()
    cleaned = redact_secrets(content)
    conn = _get_connection()
    with conn:
        conn.execute("""
            INSERT INTO conversation_history (session_id, role, content, created_at)
            VALUES (?, ?, ?, ?)
        """, (session_id, role, cleaned, time.time()))
    conn.close()

def get_conversation_history(session_id: str, limit: int = 20) -> List[Dict[str, str]]:
    init_memory_db()
    conn = _get_connection()
    rows = conn.execute("""
        SELECT role, content FROM conversation_history
        WHERE session_id = ?
        ORDER BY id DESC LIMIT ?
    """, (session_id, limit)).fetchall()
    conn.close()
    history = [dict(r) for r in reversed(rows)]
    return history

def get_memory_context_prompt(query: str = "") -> str:
    """Returns a formatted prompt block containing relevant memories."""
    if query:
        relevant = recall(query, top_k=4, min_score=0.3)
    else:
        relevant = get_all_active_memories()[:5]

    if not relevant:
        return ""
    facts = "\n".join(f"- {item['content']}" for item in relevant)
    return f"\nRelevant information about the user:\n{facts}\n"

# Initialize upon import
init_memory_db()
