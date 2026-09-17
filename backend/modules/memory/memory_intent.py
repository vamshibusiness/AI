# backend/modules/memory/memory_intent.py
"""
MemoryHandler for the JARVIS Intent Router.

Detects commands like:
- "Remember that my project is Staylo"
- "Remember my car is a Honda"
- "What do you remember about me?"
- "What do you know about my project?"
- "Forget that I ..."
"""

import re
from backend.modules.memory.memory_store import remember, recall, forget, get_all_active_memories
from backend.modules.llm.local_llm import ask_local_llm

_REMEMBER_PREFIXES = [
    r"remember\s+that\s+(.*)",
    r"remember\s+my\s+(.*)",
    r"remember\s+(.*)",
    r"make\s+a\s+note\s+that\s+(.*)",
    r"note\s+that\s+(.*)",
]

_FORGET_PREFIXES = [
    r"forget\s+that\s+(.*)",
    r"forget\s+about\s+(.*)",
    r"delete\s+memory\s+about\s+(.*)",
    r"forget\s+(.*)",
]

_QUERY_MEMORY_PATTERNS = [
    r"what\s+do\s+you\s+(remember|know)\s+about\s+(.*)",
    r"what\s+is\s+my\s+(.*)",
    r"what\s+are\s+my\s+(.*)",
    r"tell\s+me\s+what\s+you\s+know\s+about\s+me",
    r"show\s+my\s+memories",
    r"list\s+my\s+memories",
]

class MemoryHandler:
    def is_related(self, command: str) -> bool:
        cmd = command.strip().lower()

        # Check remember commands
        for p in _REMEMBER_PREFIXES:
            if re.match(p, cmd):
                return True

        # Check forget commands
        for p in _FORGET_PREFIXES:
            if re.match(p, cmd):
                return True

        # Check explicit memory recall questions
        for p in _QUERY_MEMORY_PATTERNS:
            if re.match(p, cmd):
                return True

        return False

    def handle(self, command: str, history: list = None) -> str:
        cmd = command.strip()
        lower = cmd.lower()

        # 1. Handle Forget
        for p in _FORGET_PREFIXES:
            m = re.match(p, lower)
            if m:
                target = m.group(1).strip()
                result = forget(target)
                if result.get("ok"):
                    return f"I have forgotten that information."
                return f"I couldn't find any memory matching '{target}' to forget."

        # 2. Handle Remember
        for p in _REMEMBER_PREFIXES:
            m = re.match(p, cmd, flags=re.IGNORECASE)
            if m:
                fact_to_remember = m.group(1).strip()
                if fact_to_remember:
                    res = remember(fact_to_remember, category="user_stated")
                    return f"I will remember that: {res['content']}"

        # 3. Handle List all memories
        if any(term in lower for term in ["list my memories", "show my memories", "what do you know about me"]):
            memories = get_all_active_memories()
            if not memories:
                return "I don't have any saved memories about you yet."
            items = "\n".join(f"• {m['content']}" for m in memories[:10])
            return f"Here is what I remember about you:\n{items}"

        # 4. Handle Specific memory queries (e.g. "What is my project name?", "What do you know about Staylo?")
        results = recall(cmd, top_k=3, min_score=0.3)
        if not results:
            return "I don't recall any specific memory about that."

        context = "\n".join(f"- {r['content']}" for r in results)
        messages = [
            {
                "role": "system",
                "content": (
                    "You are JARVIS. Answer the user's question directly using ONLY the recalled memories provided. "
                    "Be brief, direct, and polite. Do not speculate."
                ),
            },
            {
                "role": "user",
                "content": f"Recalled memories:\n{context}\n\nQuestion: {cmd}",
            },
        ]
        return ask_local_llm(messages).strip()
