import json
import requests
import datetime
from pathlib import Path
import re

from backend.config.jarvis_config import MAX_MEMORY_ITEMS, CHAT_MODEL, OLLAMA_URL

PROFILE_FILE = Path(__file__).resolve().parents[3] / "backend" / "assets" / "user_profile.json"
MODEL_NAME = CHAT_MODEL

def load_user_profile():
    """Loads the array of stored facts about the user."""
    if not PROFILE_FILE.exists():
        return []
    try:
        with open(PROFILE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []

def update_user_profile(session_messages: list):
    """
    Runs in the background post-session.
    Uses the LLM to curate the full memory file, then overwrites user_profile.json
    with only the most useful long-term memories.
    """
    if not session_messages:
        return

    current_facts = load_user_profile()

    try:
        print("Jarvis background engine: Curating long-term memory...")

        curated_facts = curate_memories_with_llm(
            current_facts=current_facts,
            session_messages=session_messages,
        )

        # Safety: never wipe existing memory just because the LLM returned nothing.
        if not curated_facts and current_facts:
            print("[Memory] LLM returned no curated memories. Falling back to Python compaction.")
            curated_facts = compact_memories(current_facts)

        PROFILE_FILE.parent.mkdir(parents=True, exist_ok=True)

        with open(PROFILE_FILE, "w", encoding="utf-8") as f:
            json.dump(curated_facts, f, indent=4, ensure_ascii=False)

        print(f"Profile synchronized. Current memory bank:\n{json.dumps(curated_facts, indent=2)}")

    except Exception as e:
        print(f"Memory curation failed: {e}")

        try:
            fallback_facts = compact_memories(current_facts)

            PROFILE_FILE.parent.mkdir(parents=True, exist_ok=True)

            with open(PROFILE_FILE, "w", encoding="utf-8") as f:
                json.dump(fallback_facts, f, indent=4, ensure_ascii=False)

            print(f"[Memory] Fallback compaction saved {len(fallback_facts)} memories.")

        except Exception as fallback_error:
            print(f"[Memory] Fallback compaction also failed: {fallback_error}")


def normalize_memory_text(text: str) -> str:
    text = (text or "").strip()
    text = re.sub(r"\s+", " ", text)
    return text.strip(" .") + "." if text and not text.endswith(".") else text


def should_keep_memory(memory: str) -> bool:
    lower = memory.lower().strip()

    if not lower:
        return False

    # Junk/tool/action logs — do not keep long term.
    blocked_phrases = [
        "user attempted to send an email",
        "email recipient:",
        "subject line:",
        "message body:",
        "research started",
        "research initiated",
        "currently compiling",
        "final report regarding",
        "schedule is empty",
        "no new facts",
        "no scheduled events",
        "scheduled event:",
        "scheduled '",
        "canceled event:",
        "cancelled event:",
        "reminder:",
    ]

    if any(phrase in lower for phrase in blocked_phrases):
        return False

    # One-time dated facts usually should not live in long-term memory.
    has_specific_date_or_time = bool(
        re.search(
            r"\b(january|february|march|april|may|june|july|august|september|october|november|december)\b"
            r"|\b\d{1,2}:\d{2}\b"
            r"|\b\d{4}\b",
            lower,
        )
    )

    long_term_signals = [
        "prefers",
        "preferred",
        "likes",
        "dislikes",
        "wants",
        "goal",
        "plans to",
        "intends to",
        "is building",
        "is working on",
        "does not want",
        "from now on",
        "going forward",
        "priority",
    ]

    if has_specific_date_or_time and not any(signal in lower for signal in long_term_signals):
        return False

    return any(signal in lower for signal in long_term_signals)


def memory_score(memory: str) -> int:
    lower = memory.lower()
    score = 0

    high_value_terms = [
        "prefers",
        "preferred",
        "does not want",
        "goal",
        "intends to",
        "plans to",
        "is building",
        "is working on",
        "from now on",
        "going forward",
        "priority",
        "jarvis",
    ]

    for term in high_value_terms:
        if term in lower:
            score += 3

    # Penalize stale task-like memories.
    low_value_terms = [
        "scheduled",
        "canceled",
        "research",
        "email",
        "today",
        "tomorrow",
    ]

    for term in low_value_terms:
        if term in lower:
            score -= 2

    return score


def compact_memories(memories: list[str]) -> list[str]:
    cleaned = []

    for memory in memories:
        memory = normalize_memory_text(memory)

        if not should_keep_memory(memory):
            continue

        cleaned.append(memory)

    # Dedupe by simplified lowercase text.
    deduped = {}

    for memory in cleaned:
        key = re.sub(r"[^a-z0-9]+", "", memory.lower())

        if key not in deduped:
            deduped[key] = memory

    sorted_memories = sorted(
        deduped.values(),
        key=memory_score,
        reverse=True,
    )

    return sorted_memories[:MAX_MEMORY_ITEMS]      


def clean_json_array_output(raw_output: str) -> list:
    raw_output = (raw_output or "").strip()

    if "```json" in raw_output:
        raw_output = raw_output.split("```json")[-1].split("```")[0].strip()
    elif "```" in raw_output:
        raw_output = raw_output.split("```")[-1].split("```")[0].strip()

    try:
        parsed = json.loads(raw_output)

        if isinstance(parsed, list):
            return parsed
    except Exception:
        pass

    match = re.search(r"\[.*\]", raw_output, flags=re.DOTALL)

    if match:
        try:
            parsed = json.loads(match.group(0))

            if isinstance(parsed, list):
                return parsed
        except Exception:
            pass

    return []


def curate_memories_with_llm(current_facts: list, session_messages: list) -> list[str]:
    today = datetime.date.today()
    current_date_str = today.strftime("%A, %B %d, %Y")

    cleaned_history = [
        {"role": m["role"], "content": m["content"]}
        for m in session_messages
        if isinstance(m, dict) and "role" in m and "content" in m
    ]

    curator_prompt = (
        "You are Jarvis's long-term memory curator. "
        "Your job is to rewrite the user's memory file so it contains only the most useful long-term memories.\n\n"

        f"Today's date is {current_date_str}.\n"
        f"Maximum memories allowed: {MAX_MEMORY_ITEMS}.\n\n"

        "Return the FINAL complete memory list to save. "
        "Do not return only new memories.\n\n"

        "KEEP ONLY memories useful weeks or months from now:\n"
        "- Stable user preferences.\n"
        "- Long-term goals.\n"
        "- Ongoing projects.\n"
        "- Repeated habits.\n"
        "- Important constraints.\n"
        "- Things the user explicitly asked Jarvis to remember.\n\n"

        "DO NOT KEEP:\n"
        "- One-time calendar events.\n"
        "- Scheduled appointments.\n"
        "- Canceled appointments.\n"
        "- Empty schedules.\n"
        "- Email recipients, subjects, or message bodies.\n"
        "- Research started, research completed, or research status.\n"
        "- Temporary task progress.\n"
        "- Generic tool actions.\n"
        "- Anything only useful today.\n\n"

        "RULES:\n"
        "1. Return ONLY a valid JSON array of strings.\n"
        f"2. Return at most {MAX_MEMORY_ITEMS} strings.\n"
        "3. Merge duplicates and overlapping memories.\n"
        "4. Rewrite memories to be short, clean, and durable.\n"
        "5. Do not include markdown, explanations, labels, or comments."
    )

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": curator_prompt},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "existing_memory": current_facts,
                        "latest_conversation": cleaned_history,
                    },
                    ensure_ascii=False,
                ),
            },
        ],
        "stream": False,
        "think": False,
    }

    response = requests.post(OLLAMA_URL, json=payload, timeout=60)
    response.raise_for_status()

    raw_output = response.json().get("message", {}).get("content", "").strip()
    curated = clean_json_array_output(raw_output)

    safe_curated = []

    blocked_phrases = [
        "user attempted to send an email",
        "email recipient:",
        "subject line:",
        "message body:",
        "research started",
        "research initiated",
        "currently compiling",
        "final report regarding",
        "schedule is empty",
        "no new facts",
        "no scheduled events",
        "scheduled event:",
        "scheduled '",
        "canceled event:",
        "cancelled event:",
        "reminder:",
        "appointment",
    ]

    for memory in curated:
        if not isinstance(memory, str):
            continue

        memory = normalize_memory_text(memory)

        if not memory:
            continue

        lower = memory.lower()

        if any(phrase in lower for phrase in blocked_phrases):
            continue

        if memory not in safe_curated:
            safe_curated.append(memory)

    return safe_curated[:MAX_MEMORY_ITEMS]