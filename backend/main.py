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

