# test_integration_suite.py
"""
Comprehensive Automated Test Suite for JARVIS Modular Integration.
Tests all integrated capabilities without side effects.
"""
import sys
from pathlib import Path

try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

def test_security():
    print("[TEST 1/6] Testing Security Module...")
    from backend.security import (
        is_allowed_app,
        validate_path_for_read,
        validate_path_for_write,
        validate_path_for_delete,
        redact_secrets,
        sanitize_text_for_typing,
    )
    # Allow-list
    assert is_allowed_app("notepad") is True
    assert is_allowed_app("chrome") is True
    assert is_allowed_app("calc") is True
    assert is_allowed_app("powershell_malicious") is False

    # Blocked paths in computer safety
    from backend.modules.computer.safety import (
        validate_path_for_read as safe_read,
        validate_path_for_write as safe_write,
    )
    ok_read, reason = safe_read("C:/Windows/System32/config/SAM")
    assert ok_read is False, f"Should block SAM read: {reason}"

    ok_write, reason = safe_write("C:/Windows/System32/cmd.exe")
    assert ok_write is False, f"Should block write to Windows: {reason}"

    # Secret redaction
    redacted = redact_secrets("My API key is sk-1234567890abcdef1234567890abcdef and password is secret123")
    assert "sk-1234567890abcdef" not in redacted
    assert "[REDACTED_API_KEY]" in redacted

    # Text sanitization
    sanitized = sanitize_text_for_typing("Hello world; rm -rf / ; cat /etc/passwd")
    assert len(sanitized) > 0
    print("  ✓ Security module tests passed!")


def test_memory():
    print("[TEST 2/6] Testing Memory Store (SQLite + FAISS)...")
    from backend.modules.memory.memory_store import (
        remember,
        recall,
        forget,
        get_all_active_memories,
        add_conversation_turn,
    )

    res = remember("The user prefers dark mode and lives in Hyderabad", category="test")
    assert res.get("ok") is True

    # Recall
    recalled = recall("Where does the user live?", top_k=2)
    assert len(recalled) > 0
    assert any("Hyderabad" in r["content"] for r in recalled)

    # Conversation turn
    add_conversation_turn("test_session", "user", "Hello Jarvis")
    add_conversation_turn("test_session", "assistant", "Greetings, sir.")

    # Clean up test item
    forget("The user prefers dark mode and lives in Hyderabad")
    print("  ✓ Memory store tests passed!")


def test_computer_controller():
    print("[TEST 3/6] Testing Computer Controller...")
    from backend.modules.computer.controller import dispatch, get_allowed_tools

    tools = get_allowed_tools()
    assert len(tools) >= 15
    assert "open_application" in tools
    assert "open_website" in tools
    assert "type_text" in tools
    assert "delete_file" in tools

    # Unknown tool rejected safely
    res = dispatch("arbitrary_bash_command", {"cmd": "rm -rf"})
    assert res["success"] is False
    assert "Unknown tool" in res["error"]

    # Disallowed app rejected safely
    res = dispatch("open_application", {"application": "dangerous_root_exploit"})
    assert res["success"] is False
    assert "not in the allowed application list" in res["error"]
    print("  ✓ Computer controller tests passed!")


def test_rag_store():
    print("[TEST 4/6] Testing RAG Knowledge Store...")
    from backend.modules.rag.rag_store import list_indexed_documents
    docs = list_indexed_documents()
    print(f"  Indexed documents in FAISS: {len(docs)}")
    assert isinstance(docs, list)
    assert len(docs) > 0, "Expected at least 1 indexed document in docs/"
    print(f"  Sample doc: {docs[0]['filename']} ({docs[0]['chunk_count']} chunks)")
    print("  ✓ RAG store tests passed!")


def test_intent_handlers():
    print("[TEST 5/6] Testing Intent Handler Registry...")
    from backend.router.registry import INTENT_HANDLERS
    handler_names = [h.__class__.__name__ for h in INTENT_HANDLERS]
    print(f"  Active handlers ({len(handler_names)}): {handler_names}")
    assert "ComputerHandler" in handler_names
    assert "MemoryHandler" in handler_names
    assert "RAGHandler" in handler_names
    assert "ChatHandler" in handler_names
    assert "CalendarHandler" in handler_names
    assert "GmailHandler" in handler_names
    assert "ResearchHandler" in handler_names
    assert "WeatherHandler" in handler_names
    print("  ✓ Intent handler registry tests passed!")


def test_voice_and_vision():
    print("[TEST 6/6] Testing Voice & Vision Modules...")
    from backend.modules.voice.tts import stop_speaking, is_speaking
    stop_speaking()
    assert is_speaking() is False

    from backend.modules.vision.screen_vision import VISION_MODEL, OLLAMA_URL
    assert VISION_MODEL is not None
    assert OLLAMA_URL is not None
    print("  ✓ Voice barge-in & vision module tests passed!")


if __name__ == "__main__":
    print("=" * 60)
    print("RUNNING JARVIS MASTER INTEGRATION TEST SUITE")
    print("=" * 60)
    test_security()
    test_memory()
    test_computer_controller()
    test_rag_store()
    test_intent_handlers()
    test_voice_and_vision()
    print("=" * 60)
    print("ALL 6 TEST SUITES PASSED SUCCESSFULLY! (100% GREEN)")
    print("=" * 60)
