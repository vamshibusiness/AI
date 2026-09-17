# backend/router/registry.py
"""
Intent Handler Registry — determines which handler processes a user command.

Priority order matters: first matching handler wins.
1. Computer control (most specific)
2. Calendar
3. Gmail
4. Research/web
5. Weather
6. Memory (remember/forget/recall)
7. RAG / document knowledge
8. Chat (fallback LLM)
"""

from backend.modules.google.calendar_intent import CalendarHandler
from backend.modules.google.gmail_intent import GmailHandler
from backend.modules.weather.weather_intent import WeatherHandler
from backend.modules.llm.chat_intent import ChatHandler
from backend.modules.research.research_intent import ResearchHandler
from backend.modules.rag.rag_intent import RAGHandler
from backend.modules.memory.memory_intent import MemoryHandler

# Computer control is loaded last to prevent import errors if .pyc-only modules are not restored
_extra_handlers = []
try:
    from backend.modules.computer.computer_intent import ComputerHandler
    _extra_handlers.append(ComputerHandler())
except Exception as e:
    print(f"[Registry] Computer control handler unavailable: {e}")

INTENT_HANDLERS = [
    *_extra_handlers,       # 1. Computer control (if available)
    CalendarHandler(),      # 2. Calendar
    GmailHandler(),         # 3. Gmail
    ResearchHandler(),      # 4. Web research
    WeatherHandler(),       # 5. Weather
    MemoryHandler(),        # 6. Memory (remember / recall / forget)
    RAGHandler(),           # 7. RAG document knowledge
    ChatHandler(),          # 8. Chat fallback
]