from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from pathlib import Path
import sys
import asyncio
import shutil
import tempfile
from datetime import datetime, timedelta, timezone

# Absolute pathing for reliable imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

from backend.modules.agents.gmail_agent import start_gmail_agent, stop_gmail_agent
from backend.modules.agents.research_agent import ResearchAgent
from backend.modules.research.research_tool import set_research_agent
from backend.modules.google.gmail_storage import get_inbox
from backend.modules.google.calendar_tool import get_calendar_summary
from backend.modules.rag.rag_store import index_document, list_indexed_documents, UPLOAD_DIR
from backend.modules.rag.rag_answer import answer_rag_query
from backend.modules.memory.memory_store import (
    remember, recall, forget, get_all_active_memories,
    get_memory_context_prompt, add_conversation_turn
)
from backend.modules.voice.tts import stop_speaking, is_speaking
from backend.security import redact_secrets
from backend.router.intent_router import route_command


# Background task references
gmail_task = None
startup_task = None

# Agent instances
research_agent = None

calendar_summary_cache = {
    "data": None,
    "updated_at": None,
}

CALENDAR_CACHE_MINUTES = 15

def get_gmail_summary():
    inbox = get_inbox()

    if not isinstance(inbox, list):
        inbox = []

    return {
        "unread_count": len(inbox),
    }

def get_cached_calendar_summary(force_refresh: bool = False):
    now = datetime.now(timezone.utc)

    cached_data = calendar_summary_cache.get("data")
    updated_at = calendar_summary_cache.get("updated_at")

    cache_is_valid = (
        cached_data is not None
        and updated_at is not None
        and now - updated_at < timedelta(minutes=CALENDAR_CACHE_MINUTES)
    )

    if cache_is_valid and not force_refresh:
        return cached_data

    fresh_summary = get_calendar_summary()

    calendar_summary_cache["data"] = fresh_summary
    calendar_summary_cache["updated_at"] = now

    return fresh_summary

async def delayed_agent_startup():
    global gmail_task
    global research_agent

    try:
        # Create the research agent when Jarvis starts.
        # If active_research.json contains unfinished work, ResearchAgent will resume it automatically.
        research_agent = ResearchAgent()
        set_research_agent(research_agent)

        # Delay Gmail startup so the backend/UI can finish loading first.
        await asyncio.sleep(5)
        gmail_task = await start_gmail_agent()

    except asyncio.CancelledError:
        print("Startup: Delayed agent startup cancelled.")
        raise


async def cancel_task(task):
    if task is None or task.done():
        return

    task.cancel()

    try:
        await task
    except asyncio.CancelledError:
        pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    global startup_task

    startup_task = asyncio.create_task(delayed_agent_startup())

    try:
        yield

    finally:
        # Handles Ctrl+C during the initial startup delay.
        await cancel_task(startup_task)

        # Handles Ctrl+C after the Gmail polling loop has started.
        if gmail_task:
            await stop_gmail_agent(gmail_task)


app = FastAPI(lifespan=lifespan)

async def broadcast_message(message: dict):
    disconnected = []

    for client in connected_clients:
        try:
            await client.send_json(message)
        except Exception:
            disconnected.append(client)

    for client in disconnected:
        connected_clients.discard(client)


# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# UI state
connected_clients = set()
current_status = "idle"


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    global current_status

    await websocket.accept()
    connected_clients.add(websocket)

    await websocket.send_json({"status": current_status})

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        connected_clients.discard(websocket)
    except Exception:
        connected_clients.discard(websocket)


async def broadcast_status(status: str):
    global current_status

    current_status = status
    disconnected = []

    for client in connected_clients:
        try:
            await client.send_json({"status": status})
        except Exception:
            disconnected.append(client)

    for client in disconnected:
        connected_clients.discard(client)


@app.get("/status")
async def get_status():
    return {"status": current_status}


@app.get("/trigger-listening")
async def trigger_listening():
    await broadcast_status("listening")
    return {"ok": True, "status": current_status}


@app.get("/trigger-thinking")
async def trigger_thinking():
    await broadcast_status("thinking")
    return {"ok": True, "status": current_status}


@app.get("/trigger-speaking")
async def trigger_speaking():
    await broadcast_status("speaking")
    return {"ok": True, "status": current_status}


@app.get("/trigger-idle")
async def trigger_idle():
    await broadcast_status("idle")
    return {"ok": True, "status": current_status}


@app.get("/trigger-email-check")
async def trigger_email_check():
    await broadcast_status("checking-email")
    return {"ok": True, "status": current_status}


@app.get("/trigger-finish-tasks")
async def trigger_finish_tasks():
    global research_agent

    await broadcast_status("thinking")

    # Safety fallback in case the startup task has not created it yet.
    # Creating ResearchAgent will automatically resume unfinished research if active_research.json has a running status.
    if research_agent is None:
        research_agent = ResearchAgent()

    message = research_agent.get_status()

    await broadcast_status("idle")

    return {
        "ok": True,
        "message": message,
        "status": current_status,
    }


@app.get("/research/status")
async def research_status():
    global research_agent

    if research_agent is None:
        research_agent = ResearchAgent()

    return {
        "ok": True,
        "message": research_agent.get_status(),
    }

@app.get("/research/show-completed")
async def show_completed_research():
    global research_agent

    if research_agent is None:
        research_agent = ResearchAgent()
        set_research_agent(research_agent)

    history = research_agent.list_completed_research()

    items = []

    for item in history:
        report = item.get("report", "")
        items.append({
            "topic": item.get("topic", "Untitled research"),
            "summary": item.get("summary") or item.get("report", "")[:350],
            "report": item.get("report", ""),
            "facts": item.get("facts", []),
            "sources": item.get("sources", []),
            "created_at": item.get("created_at", "unknown date"),
        })

    await broadcast_message({
        "type": "show_completed_research",
        "items": items,
    })

    await broadcast_message({
        "type": "research_summary",
        **research_agent.get_research_summary(),
    })
    return {
        "ok": True,
        "count": len(items),
    }

@app.get("/research/close")
async def close_research():

    await broadcast_message({
        "type": "home"
    })

    return {"ok": True}    

@app.get("/research/summary")
async def research_summary():
    global research_agent

    if research_agent is None:
        research_agent = ResearchAgent()
        set_research_agent(research_agent)

    return {
        "ok": True,
        **research_agent.get_research_summary(),
    }

@app.get("/gmail/summary")
async def gmail_summary():
    return {
        "ok": True,
        **get_gmail_summary(),
    }


@app.get("/gmail/refresh-summary")
async def refresh_gmail_summary():
    summary = get_gmail_summary()

    await broadcast_message({
        "type": "gmail_summary",
        **summary,
    })

    return {
        "ok": True,
        **summary,
    }

@app.get("/calendar/summary")
async def calendar_summary():
    return {
        "ok": True,
        **get_cached_calendar_summary(force_refresh=False),
    }


@app.get("/calendar/refresh-summary")
async def refresh_calendar_summary():
    summary = get_cached_calendar_summary(force_refresh=True)

    await broadcast_message({
        "type": "calendar_summary",
        **summary,
    })

    return {
        "ok": True,
        **summary,
    }


# ==============================================================
# RAG / DOCUMENT ENDPOINTS
# ==============================================================

@app.post("/rag/upload")
async def rag_upload(file: UploadFile = File(...)):
    """Upload and index a document (PDF, TXT, MD, CSV) into the RAG knowledge base."""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    allowed_extensions = {".pdf", ".txt", ".md", ".markdown", ".csv"}
    suffix = Path(file.filename).suffix.lower()

    if suffix not in allowed_extensions:
        return JSONResponse(status_code=400, content={
            "ok": False,
            "error": f"File type '{suffix}' is not supported. Supported: PDF, TXT, MD, CSV",
        })

    save_path = UPLOAD_DIR / file.filename
    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    result = index_document(save_path)

    await broadcast_message({
        "type": "rag_document_indexed",
        **result,
    })

    return {"ok": True, **result}


@app.get("/rag/documents")
async def rag_documents():
    """List all indexed documents with chunk and page counts."""
    docs = list_indexed_documents()
    return {"ok": True, "documents": docs, "count": len(docs)}


@app.post("/rag/query")
async def rag_query(body: dict):
    """
    Query the RAG knowledge base.
    Body: { "question": "..." }
    Returns answer with source citations.
    """
    question = (body.get("question") or "").strip()
    if not question:
        return JSONResponse(status_code=400, content={"ok": False, "error": "Question is required."})

    result = answer_rag_query(question)
    return {"ok": True, **result}


@app.get("/rag/index-docs")
async def rag_index_docs():
    """Re-index all documents in the docs/ folder (incremental, skips unchanged)."""
    from backend.modules.rag.build_index import build_index
    docs = build_index()
    return {"ok": True, "indexed_count": len(docs), "documents": docs}


# ==============================================================
# MEMORY ENDPOINTS
# ==============================================================

@app.post("/memory/remember")
async def memory_remember(body: dict):
    """Store a fact in long-term memory."""
    content = (body.get("content") or "").strip()
    category = body.get("category", "api")
    if not content:
        return JSONResponse(status_code=400, content={"ok": False, "error": "Content is required."})
    result = remember(content, category=category)
    return result


@app.post("/memory/recall")
async def memory_recall(body: dict):
    """Semantic search over long-term memories."""
    query = (body.get("query") or "").strip()
    if not query:
        return JSONResponse(status_code=400, content={"ok": False, "error": "Query is required."})
    results = recall(query, top_k=5)
    return {"ok": True, "results": results, "count": len(results)}


@app.post("/memory/forget")
async def memory_forget(body: dict):
    """Forget a memory matching content or query."""
    query = (body.get("content") or body.get("query") or "").strip()
    if not query:
        return JSONResponse(status_code=400, content={"ok": False, "error": "Content or query is required."})
    result = forget(query)
    return result


@app.get("/memory/all")
async def memory_all():
    """List all active long-term memories."""
    memories = get_all_active_memories()
    return {"ok": True, "memories": memories, "count": len(memories)}


# ==============================================================
# SYSTEM STATS ENDPOINT
# ==============================================================

@app.get("/system/stats")
async def system_stats():
    """Return safe system resource metrics."""
    try:
        import psutil
        cpu_pct = psutil.cpu_percent(interval=0.5)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        battery = psutil.sensors_battery()

        gpu_info = None
        try:
            import subprocess
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.used,memory.total,utilization.gpu",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                parts = [p.strip() for p in result.stdout.strip().split(",")]
                if len(parts) >= 4:
                    gpu_info = {
                        "name": parts[0],
                        "vram_used_mb": int(parts[1]),
                        "vram_total_mb": int(parts[2]),
                        "utilization_pct": int(parts[3]),
                    }
        except Exception:
            pass

        return {
            "ok": True,
            "cpu_percent": cpu_pct,
            "ram_used_gb": round(ram.used / 1e9, 2),
            "ram_total_gb": round(ram.total / 1e9, 2),
            "ram_percent": ram.percent,
            "disk_used_gb": round(disk.used / 1e9, 2),
            "disk_total_gb": round(disk.total / 1e9, 2),
            "disk_percent": disk.percent,
            "battery_percent": battery.percent if battery else None,
            "battery_plugged": battery.power_plugged if battery else None,
            "gpu": gpu_info,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ==============================================================
# VOICE CONTROL (BARGE-IN) ENDPOINTS
# ==============================================================

@app.post("/voice/stop")
async def voice_stop():
    """Immediately interrupt and silence any active TTS speech."""
    stop_speaking()
    return {"ok": True, "message": "Speech playback stopped."}


@app.get("/voice/status")
async def voice_status():
    """Check if speech is currently playing."""
    return {"ok": True, "speaking": is_speaking()}


# ==============================================================
# COMPUTER CONTROL ENDPOINTS
# ==============================================================

@app.post("/computer/confirm-delete")
async def computer_confirm_delete(body: dict):
    """
    Execute deletion of a file/folder after explicit user confirmation in UI.
    Body: { "path": "...", "confirm": true }
    """
    path = body.get("path", "")
    confirmed = body.get("confirm", False)
    if not confirmed:
        return JSONResponse(status_code=400, content={"ok": False, "error": "Action cancelled by user."})

    from backend.modules.computer.files import execute_delete
    result = execute_delete(path)
    return result


@app.get("/computer/tools")
async def computer_tools():
    """List available computer control tools."""
    from backend.modules.computer.controller import get_allowed_tools
    tools = get_allowed_tools()
    return {"ok": True, "tools": tools}


# ==============================================================
# VISION & OCR ENDPOINTS
# ==============================================================

@app.post("/vision/analyze")
async def vision_analyze(body: dict = None):
    """
    Take screenshot and analyze with on-demand local vision model (keep_alive: 0).
    Body: { "prompt": "..." }
    """
    from backend.modules.vision.screen_vision import analyze_screen
    prompt = (body or {}).get("prompt", "Describe what is on the screen succinctly.")
    res = analyze_screen(prompt)
    return res


@app.get("/vision/ocr")
async def vision_ocr():
    """Extract text from screen using lightweight OCR."""
    from backend.modules.vision.screen_vision import extract_screen_text
    res = extract_screen_text()
    return res


# ==============================================================
# VOICE TRIGGER ENDPOINT — Trigger wake/listening from UI mic
# ==============================================================

@app.post("/voice/trigger")
async def voice_trigger():
    """Trigger JARVIS voice listening pipeline from UI microphone button."""
    try:
        from backend.modules.wakeword.listener import wake_queue
        wake_queue.put("trigger")
        return {"ok": True, "message": "Voice listening triggered"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"ok": False, "error": str(e)})


# ==============================================================
# CHAT ENDPOINT — Text-based conversation (UI chat panel)
# ==============================================================

from backend.modules.memory_manager import load_user_profile

# In-process conversation sessions keyed by session_id
_chat_sessions: dict = {}


def _get_chat_history(session_id: str, current_message: str) -> list:
    """
    Construct full conversation history with system prompt, user profile,
    and long-term memory context, appending the current message so
    local LLM receives the complete prompt.
    """
    global _chat_sessions

    if session_id not in _chat_sessions:
        user_facts = load_user_profile()
        memory_ctx = get_memory_context_prompt()
        profile_context = ""
        if user_facts:
            profile_context += "\nCore details you know about the user:\n" + "\n".join([f"- {fact}" for fact in user_facts])
        if memory_ctx:
            profile_context += "\n" + memory_ctx

        system_prompt = (
            "You are Jarvis, a highly intelligent, sharp, and articulate AI assistant created for Vamshi Krishna. "
            "Your tone is polished, calm, and effortlessly capable, with a hint of dry wit. "
            "Answer directly and helpfully. Use clean Markdown with code blocks where appropriate."
            f"{profile_context}"
        )
        _chat_sessions[session_id] = [{"role": "system", "content": system_prompt}]

    # Append current message to session history
    _chat_sessions[session_id].append({"role": "user", "content": current_message})

    # Rolling window: keep system prompt + last 14 message turns
    if len(_chat_sessions[session_id]) > 15:
        _chat_sessions[session_id] = [_chat_sessions[session_id][0]] + _chat_sessions[session_id][-14:]

    return _chat_sessions[session_id]


@app.post("/ws/broadcast")
async def ws_broadcast_endpoint(body: dict):
    """Broadcast an arbitrary event to all connected WebSocket clients."""
    await broadcast_message(body)
    return {"ok": True}


@app.post("/chat")
async def chat(body: dict):
    """
    Accept a text message from the UI chat panel, route it through the
    existing JARVIS intent router without TTS speech, and return the response.

    Body: { "message": "...", "session_id": "...", "msg_id": "..." }
    Returns: { "ok": true, "response": "...", "session_id": "...", "msg_id": "..." }
    """
    message = (body.get("message") or "").strip()
    session_id = body.get("session_id") or "default"
    msg_id = body.get("msg_id") or ""

    if not message:
        return JSONResponse(status_code=400, content={"ok": False, "error": "Message is required."})

    await broadcast_status("thinking")

    try:
        # Build full conversation history containing the system prompt and current user message
        history = _get_chat_history(session_id, message)

        # Route through intent system with speak_response=False (Chat Mode MUST NOT speak)
        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: route_command(message, history, speak_response=False),
        )

        reply_text = str(response) if response else "I processed your request, sir, but have no additional report."

        # Record assistant reply in rolling history
        history.append({"role": "assistant", "content": reply_text})

        # Persist conversation turn in memory store
        try:
            add_conversation_turn(session_id, "user", message)
            add_conversation_turn(session_id, "assistant", reply_text)
        except Exception:
            pass

        await broadcast_status("idle")

        return {
            "ok": True,
            "response": reply_text,
            "session_id": session_id,
            "msg_id": msg_id,
        }

    except Exception as e:
        await broadcast_status("idle")
        return JSONResponse(status_code=500, content={"ok": False, "error": str(e)})


@app.post("/chat/stream")
async def chat_stream(body: dict):
    """
    Streaming SSE endpoint for Chat Mode.
    Progressively streams tokens from local Ollama without TTS audio playback.
    """
    from fastapi.responses import StreamingResponse
    import json
    import threading

    message = (body.get("message") or "").strip()
    session_id = body.get("session_id") or "default"
    msg_id = body.get("msg_id") or ""

    if not message:
        return JSONResponse(status_code=400, content={"ok": False, "error": "Message is required."})

    await broadcast_status("thinking")

    async def event_generator():
        try:
            history = _get_chat_history(session_id, message)

            # Check if specialized tool handler matches (computer, calendar, research, etc.)
            from backend.router.registry import INTENT_HANDLERS
            from backend.modules.llm.chat_intent import ChatHandler

            special_handler = None
            for h in INTENT_HANDLERS:
                if not isinstance(h, ChatHandler) and h.is_related(message):
                    special_handler = h
                    break

            if special_handler:
                resp = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: special_handler.handle(message, history=history)
                )
                reply_text = str(resp) if resp else "Task completed, sir."
                history.append({"role": "assistant", "content": reply_text})
                try:
                    add_conversation_turn(session_id, "user", message)
                    add_conversation_turn(session_id, "assistant", reply_text)
                except Exception:
                    pass
                yield f"data: {json.dumps({'chunk': reply_text, 'done': True, 'msg_id': msg_id})}\n\n"
            else:
                from backend.modules.llm.local_llm import ask_local_llm_stream
                full_reply = []
                loop = asyncio.get_event_loop()
                token_queue = asyncio.Queue()

                def sync_stream_worker():
                    try:
                        for tok in ask_local_llm_stream(history):
                            if tok:
                                loop.call_soon_threadsafe(token_queue.put_nowait, tok)
                    except Exception as err:
                        print(f"[sync_stream_worker error] {err}")
                    finally:
                        loop.call_soon_threadsafe(token_queue.put_nowait, None)

                threading.Thread(target=sync_stream_worker, daemon=True).start()

                while True:
                    tok = await token_queue.get()
                    if tok is None:
                        break
                    full_reply.append(tok)
                    yield f"data: {json.dumps({'chunk': tok, 'done': False, 'msg_id': msg_id})}\n\n"

                final_text = "".join(full_reply)
                history.append({"role": "assistant", "content": final_text})
                try:
                    add_conversation_turn(session_id, "user", message)
                    add_conversation_turn(session_id, "assistant", final_text)
                except Exception:
                    pass
                yield f"data: {json.dumps({'chunk': '', 'done': True, 'msg_id': msg_id})}\n\n"

            await broadcast_status("idle")

        except Exception as e:
            await broadcast_status("idle")
            yield f"data: {json.dumps({'error': str(e), 'done': True, 'msg_id': msg_id})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


