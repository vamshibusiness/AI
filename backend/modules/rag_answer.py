from backend.modules.llm.local_llm import ask_local_llm
from backend.modules.rag.retriever import retrieve_docs


def ask_jarvis_docs(question: str) -> str:
    chunks = retrieve_docs(question, top_k=4, min_score=0.35)

    if not chunks:
        return "I could not find anything about that in my Jarvis documentation."

    context_parts = []

    for chunk in chunks:
        context_parts.append(
            f"Source: {chunk['source']}\n"
            f"Heading: {chunk['heading']}\n"
            f"Content:\n{chunk['text']}"
        )

    context = "\n\n---\n\n".join(context_parts)

    messages = [
        {
            "role": "system",
            "content": (
                "Keep answers concise, clear, and voice-friendly. "
                "Do not use markdown, bullet points, asterisks, or numbered lists. "
                "Answer in 1 to 3 short paragraphs."
                "Use only provided documentation to answer question"
            ),
        },
        {
            "role": "user",
            "content": (
                f"Documentation context:\n\n{context}\n\n"
                f"User question:\n{question}"
            ),
        },
    ]

    return ask_local_llm(messages).strip()


