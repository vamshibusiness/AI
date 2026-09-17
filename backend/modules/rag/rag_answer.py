# backend/modules/rag/rag_answer.py
"""
Answer generator for JARVIS RAG with source attribution and citations.
"""

from typing import Dict, Any, List, Tuple
from backend.modules.llm.local_llm import ask_local_llm
from backend.modules.rag.retriever import retrieve_docs

def answer_rag_query(question: str, top_k: int = 4, min_score: float = 0.35) -> Dict[str, Any]:
    """
    Retrieves matching document chunks and prompts the local LLM.
    Returns structured answer with source and page citations.
    """
    chunks = retrieve_docs(question, top_k=top_k, min_score=min_score)

    if not chunks:
        return {
            "answer": "I could not find anything relevant to your question in the loaded documents.",
            "citations": [],
            "chunks_used": 0,
        }

    context_parts = []
    citations = []

    for c in chunks:
        src = c.get("source", "Document")
        pg = c.get("page", 1)
        score = c.get("score", 0.0)
        heading = c.get("heading", "")

        context_parts.append(
            f"[Source: {src} | Page: {pg} | Section: {heading}]\n{c['text']}"
        )
        citations.append({
            "source": src,
            "page": pg,
            "heading": heading,
            "score": round(score, 3),
            "snippet": c["text"][:150] + "...",
        })

    context = "\n\n---\n\n".join(context_parts)

    messages = [
        {
            "role": "system",
            "content": (
                "You are JARVIS, an intelligent agent. Answer the user's question accurately using ONLY "
                "the provided document excerpts. When stating facts, explicitly reference the source document "
                "and page number if applicable (e.g. '[Source: myfile.pdf, Page 2]'). "
                "Be direct, clear, and informative. If the context does not contain the answer, state that clearly."
            ),
        },
        {
            "role": "user",
            "content": f"Document context:\n\n{context}\n\nUser Question:\n{question}",
        },
    ]

    answer = ask_local_llm(messages).strip()

    return {
        "answer": answer,
        "citations": citations,
        "chunks_used": len(chunks),
    }

def ask_jarvis_docs(question: str) -> str:
    """Voice/Router compatible string response."""
    result = answer_rag_query(question)
    return result["answer"]
