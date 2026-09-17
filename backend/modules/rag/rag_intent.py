from backend.modules.rag.rag_answer import ask_jarvis_docs
from backend.modules.rag.retriever import retrieve_docs


MIN_KNOWLEDGE_SCORE = 0.65

def looks_like_jarvis_question(command: str) -> bool:
    command = command.lower()

    self_terms = [
        "jarvis",
        "you",
        "your",
        "yourself",
        "system",
        "feature",
        "agent",
        "tool",
        "wake word",
        "voice",
        "memory",
        "rag",
        "beast mode",
        "ollama",
    ]

    question_terms = [
        "how do",
        "how does",
        "what can",
        "what are",
        "what is",
        "why do",
        "why did",
        "where do",
        "explain",
        "tell me about",
    ]

    return (
        any(term in command for term in self_terms)
        and any(term in command for term in question_terms)
    )



def is_jarvis_knowledge_request(command: str) -> bool:
    """ Let RAG decide whether this is a Jarvis documentation question. """
    if not looks_like_jarvis_question(command):
        return False
    
    chunks = retrieve_docs(
        command,
        top_k=3,
        min_score=MIN_KNOWLEDGE_SCORE,
    )

    return bool(chunks)


def handle_knowledge_command(command: str) -> str:
    print("RAG Lookup")
    return ask_jarvis_docs(command)


class RAGHandler:
    def is_related(self, command: str) -> bool:
        return is_jarvis_knowledge_request(command)

    def handle(self, command: str, history: list = None) -> str:
        return handle_knowledge_command(command)