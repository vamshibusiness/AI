from dotenv import load_dotenv
import os

load_dotenv()

USER_TITLE = os.getenv("USER_TITLE", "sir")

WAKE_RESPONSE = os.getenv(
    "WAKE_RESPONSE",
    f"Hello {USER_TITLE}, how can I help you?"
)

USER_CITY = os.getenv("USER_CITY", "Pittsburgh")
USER_STATE = os.getenv("USER_STATE", "PA")

KEEP_GMAIL_DAYS = int(
    os.getenv("KEEP_GMAIL_DAYS", "7")
)

GMAIL_PULL_MINS = int(
    os.getenv("GMAIL_PULL_MINS", "15")
)


BEAST_MODE = (
    os.getenv("BEAST_MODE", "False").lower() == "true"
)

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat")
CHAT_MODEL = os.getenv("CHAT_MODEL", "gemma4:e4b")
RESEARCH_MODE = os.getenv("RESEARCH_MODE", "qwen3.6:27b")


MAX_MEMORY_ITEMS = int(
    os.getenv("MAX_MEMORY_LIST", "20")
)




